"""Medallion pipeline driven by governance metadata.

1. **Bronze**: raw CSV ingestion (all text) plus ``_source_file`` / ``_ingested_at``.
2. **Silver**: standardisation SQL, contract rules, and **quarantine** of failing rows.
3. **Gold**: business models and KPIs, with their own contract rules.

After each dataset is built: schema conformance against its contract, personal-data
discovery, column lineage and quality results are written to the ``meta`` schema.
Build order is derived from the SQL itself (no hand-maintained DAG).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime

import duckdb

from . import contracts as contracts_mod
from . import lineage, privacy, quality
from .db import audit, connect, table_columns
from .generator import as_of_date
from .paths import load_yaml, models_dir, sources_dir
from .verify import conformance


@dataclass
class Model:
    name: str
    sql: str | None = None
    source: dict | None = None
    contract: contracts_mod.Contract | None = None

    @property
    def layer(self) -> str:
        return self.name.split(".")[0]

    @property
    def deps(self) -> set[str]:
        deps = lineage.referenced_tables(self.sql) if self.sql else set()
        if self.contract:
            deps |= {r.args["table"] for r in self.contract.rules if r.kind == "references"}
            deps |= {r.args["referenceTable"] for r in self.contract.rules if r.kind == "tolerance"}
        deps.discard(self.name)
        return deps


@dataclass
class Report:
    run_id: str
    as_of: date
    status: str = "passed"
    datasets: int = 0
    quarantined: int = 0
    results: list[quality.Result] = field(default_factory=list)
    findings: list[tuple[str, str, str, str]] = field(default_factory=list)  # dataset, kind, severity, detail
    errors: list[str] = field(default_factory=list)


def sources() -> list[dict]:
    path = models_dir() / "sources.yaml"
    return load_yaml(path).get("sources", []) if path.exists() else []


def exposures() -> list[dict]:
    path = models_dir() / "exposures.yaml"
    return load_yaml(path).get("exposures", []) if path.exists() else []


def models() -> list[Model]:
    contracts = contracts_mod.by_name()
    out = [Model(s["name"], source=s) for s in sources()]
    for path in sorted(models_dir().glob("*.sql")):
        name = path.stem
        out.append(Model(name, sql=path.read_text(encoding="utf-8"), contract=contracts.get(name)))
    return out


def order(items: list[Model]) -> list[Model]:
    by = {m.name: m for m in items}
    deps = {m.name: {d for d in m.deps if d in by} for m in items}
    done: set[str] = set()
    result: list[Model] = []
    pending = sorted(by, key=lambda n: (("bronze", "silver", "gold").index(by[n].layer), n))
    while pending:
        ready = [n for n in pending if deps[n] <= done]
        if not ready:
            raise RuntimeError(f"Circular dependency between: {', '.join(pending)}")
        for n in ready:
            result.append(by[n])
            done.add(n)
        pending = [n for n in pending if n not in done]
    return result


def _ingest(con: duckdb.DuckDBPyConnection, m: Model) -> None:
    path = sources_dir() / m.source["file"]
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run: govkit generate")
    p = str(path).replace("'", "''")
    con.execute(f"CREATE OR REPLACE TABLE {m.name} AS SELECT *, '{m.source['file']}' AS _source_file, "
                f"TIMESTAMP '{datetime.now():%Y-%m-%d %H:%M:%S}' AS _ingested_at "
                f"FROM read_csv('{p}', all_varchar = true, header = true)")


def table_columns_any(con: duckdb.DuckDBPyConnection, name: str) -> dict[str, str]:
    """Columns of a persistent or temporary table."""
    return {r[0]: r[1] for r in con.execute(f"DESCRIBE {name}").fetchall()}


def run(con: duckdb.DuckDBPyConnection | None = None, actor: str = "pipeline", log=print) -> Report:
    own = con is None
    con = con or connect()
    report = Report(run_id=datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6], as_of=as_of_date())
    started = datetime.now()
    edges: list[tuple] = []
    catalog: list[list] = []
    column_rows: list[list] = []

    for m in order(models()):
        violations: list[tuple[str, str]] = []
        try:
            results, quarantined = [], 0
            if m.source:
                _ingest(con, m)
            else:
                staged = m.layer == "silver" and m.contract is not None
                target = "__stage" if staged else m.name
                con.execute(f"CREATE OR REPLACE {'TEMP ' if staged else ''}TABLE {target} AS {m.sql}")
                if m.contract:
                    # Schema first: rules are only meaningful on data that has the contracted shape.
                    violations = conformance(m.contract, table_columns_any(con, target))
                    if any(sev == "error" for sev, _ in violations):
                        if staged:
                            con.execute(f"CREATE OR REPLACE TABLE {m.name} AS SELECT * FROM __stage")
                    else:
                        results, quarantined = quality.evaluate(con, m.contract, target, report.as_of,
                                                                quarantine=staged)
                if staged:
                    con.execute("DROP TABLE IF EXISTS __stage")
        except Exception as exc:  # noqa: BLE001 - report and continue with independent models
            report.errors.append(f"{m.name}: {exc}")
            log(f"  ✗ {m.name}: {exc}")
            continue

        rows = con.execute(f"SELECT count(*) FROM {m.name}").fetchone()[0]
        actual = table_columns(con, m.name)
        detected = privacy.detect_table(con, m.name)
        declared_pii = dict(m.source.get("pii") or {}) if m.source else (m.contract.pii_columns if m.contract else {})
        for column, category in detected.items():
            if column not in declared_pii:
                report.findings.append((m.name, "undeclared_pii", "high",
                                        f"column '{column}' looks like '{category}' personal data but is not "
                                        "declared, so it is not masked"))
        for severity, detail in violations:
            report.findings.append((m.name, "contract_violation", severity, detail))
        if any(sev == "error" for sev, _ in violations):
            log(f"  ✗ {m.name}: breaks its contract ({len(violations)} schema violation(s)); quality rules skipped")
        if not m.contract and not m.source:
            report.findings.append((m.name, "no_contract", "medium", "published model without a data contract"))

        edges += (lineage.source_edges(con, m.name, m.source["file"]) if m.source
                  else lineage.model_edges(con, m.name, m.sql))
        report.results += results
        report.quarantined += quarantined
        report.datasets += 1
        c = m.contract
        meta = m.source or {}
        catalog.append([m.name, m.layer, c.domain if c else meta.get("domain"),
                        c.classification if c else meta.get("classification"), c.owner if c else None,
                        c.steward if c else None, c.version if c else None,
                        c.purpose if c else meta.get("description"), bool(declared_pii), rows, quarantined,
                        quality.score(results), datetime.now()])
        declared = {p.name: p for p in c.properties} if c else {}
        for pos, (name, typ) in enumerate(actual.items(), 1):
            p = declared.get(name)
            column_rows.append([m.name, name, pos, p.physical_type if p else None, typ, p.required if p else None,
                                p.unique if p else None, p.primary_key if p else None, p.description if p else None,
                                p.business_name if p else None, declared_pii.get(name), detected.get(name)])
        failing = sum(1 for r in results if r.failed)
        extra = f", {quarantined} quarantined" if quarantined else ""
        log(f"  ✓ {m.name:<34} {rows:>6} rows{extra}" + (f"  ({failing} rules with failures)" if failing else ""))

    edges += lineage.exposure_edges(exposures())
    finished = datetime.now()
    con.execute("DELETE FROM meta.lineage")
    con.execute("DELETE FROM meta.datasets")
    con.execute("DELETE FROM meta.columns")
    if edges:
        con.executemany("INSERT INTO meta.lineage VALUES (?, ?, ?, ?)", edges)
    if catalog:
        con.executemany("INSERT INTO meta.datasets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", catalog)
    if column_rows:
        con.executemany("INSERT INTO meta.columns VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", column_rows)
    if report.results:
        con.executemany("INSERT INTO meta.quality_results VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", [
            [report.run_id, r.dataset, r.rule.name, r.rule.kind, r.rule.column, r.rule.dimension, r.rule.severity,
             r.rule.origin, r.evaluated, r.failed, r.pass_rate, r.status, r.rule.description]
            for r in report.results])
    if report.findings:
        con.executemany("INSERT INTO meta.findings VALUES (?,?,?,?,?)", [[report.run_id, *f] for f in report.findings])

    gold_fail = any(r.status == "fail" and r.dataset.startswith("gold.") for r in report.results)
    if report.errors or any(f[1] == "contract_violation" and f[2] == "error" for f in report.findings):
        report.status = "failed"
    elif gold_fail or any(f[2] == "high" for f in report.findings):
        report.status = "warning"
    con.execute("INSERT INTO meta.runs VALUES (?,?,?,?,?,?,?,?)",
                [report.run_id, started, finished, report.as_of, report.status, report.datasets,
                 report.quarantined, "; ".join(report.errors)])
    audit(con, actor, "pipeline_run", "all",
          f"{report.run_id}: {report.datasets} datasets, {report.quarantined} quarantined, {report.status}")
    from . import report as report_mod

    report_mod.write(con)
    if own:
        con.close()
    return report
