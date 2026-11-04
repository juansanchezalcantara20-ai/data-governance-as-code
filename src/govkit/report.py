"""Quality report per dataset and per DAMA dimension, produced on every pipeline run.

``govkit run`` writes ``reports/quality_report.md`` and ``reports/quality_report.json`` for the
run. ``govkit docs`` publishes the latest one to ``docs/generated/quality_report.md``. The
content depends only on the data and the as-of date (no timestamps), so it is reproducible.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from .contracts import DIMENSIONS
from .paths import governance, reports_dir

FINDINGS_NOTE = ("Data is synthetic with deliberately injected defects (see `data/sources/_manifest.json`). "
                 "Findings illustrate the method; they are not results about any real organisation.")


def _latest(con: duckdb.DuckDBPyConnection) -> tuple[str, str, str]:
    return con.execute("SELECT run_id, CAST(as_of AS VARCHAR), status FROM meta.runs ORDER BY started_at DESC LIMIT 1"
                       ).fetchone()


def data(con: duckdb.DuckDBPyConnection) -> dict:
    run_id, as_of, status = _latest(con)
    results = con.execute("SELECT dataset, rule, kind, column_name, dimension, severity, origin, evaluated, failed, "
                          "pass_rate, status, description FROM meta.quality_results WHERE run_id = ? "
                          "ORDER BY dataset, rule", [run_id]).fetchdf()
    datasets = con.execute("SELECT dataset, layer, domain, classification, row_count, quarantined_rows, quality_score "
                           "FROM meta.datasets WHERE contract_version IS NOT NULL ORDER BY dataset").fetchdf()
    findings = con.execute("SELECT dataset, kind, severity, detail FROM meta.findings WHERE run_id = ? "
                           "ORDER BY severity, dataset", [run_id]).fetchdf()
    quarantine = {}
    for (table,) in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'quarantine' "
                                "ORDER BY 1").fetchall():
        rows = con.execute(f"SELECT unnest(string_split(quarantine_reason, '; ')) AS r, count(*) "
                           f"FROM quarantine.{table} GROUP BY 1 ORDER BY 2 DESC, 1").fetchall()
        if rows:
            quarantine[f"silver.{table}"] = {r: int(n) for r, n in rows}
    matrix = {}
    for ds, group in results.groupby("dataset"):
        matrix[ds] = {}
        for dim in DIMENSIONS:
            g = group[group.dimension == dim]
            if len(g):
                matrix[ds][dim] = {"rules": int(len(g)), "pass_rate": round(float(g.pass_rate.mean()), 2),
                                   "failing": int((g.failed > 0).sum())}
    by_dim = {}
    for dim in DIMENSIONS:
        g = results[results.dimension == dim]
        by_dim[dim] = {"rules": int(len(g)), "pass_rate": round(float(g.pass_rate.mean()), 2) if len(g) else None,
                       "failed_rows": int(g[g.evaluated > 1].failed.sum()), "failing_rules": int((g.failed > 0).sum())}
    terms = governance("glossary")["terms"]
    rule_status = {(r.dataset, r.rule): r for r in results.itertuples()}
    glossary_cov = []
    for t in terms:
        src = (t.get("source") or {}).get("table")
        linked = [rule_status.get((src, r)) for r in t.get("quality_rules") or []]
        linked = [r for r in linked if r is not None]
        glossary_cov.append({"term": t["name"], "rules": len(linked),
                             "pass_rate": round(sum(r.pass_rate for r in linked) / len(linked), 2) if linked else None})
    return {"as_of": as_of, "status": status, "datasets": datasets.to_dict("records"), "by_dimension": by_dim,
            "matrix": matrix, "results": results.to_dict("records"), "findings": findings.to_dict("records"),
            "quarantine": quarantine, "glossary_coverage": glossary_cov}


def _cell(x: dict | None) -> str:
    if not x:
        return "—"
    mark = "✅" if x["failing"] == 0 else "⚠️"
    return f"{mark} {x['pass_rate']:.2f}% ({x['rules']})"


def markdown(d: dict) -> str:
    lines = ["# Data quality report", "", f"As of **{d['as_of']}** · run status **{d['status'].upper()}**", "",
             f"> {FINDINGS_NOTE}", "", "## By dimension", "",
             "| Dimension | Rules | Mean pass rate | Failing rules | Rows failing (row rules) |", "|---|:-:|:-:|:-:|:-:|"]
    for dim, x in d["by_dimension"].items():
        rate = "—" if x["pass_rate"] is None else f"{x['pass_rate']:.2f}%"
        lines.append(f"| {dim} | {x['rules']} | {rate} | {x['failing_rules']} | {x['failed_rows']} |")
    lines += ["", "## By dataset and dimension", "", "Cell = mean pass rate (number of rules). ⚠️ = at least one rule failing.",
              "", "| Dataset | Rows | Quarantined | Score | " + " | ".join(DIMENSIONS) + " |",
              "|---|--:|--:|--:|" + "|".join(":-:" for _ in DIMENSIONS) + "|"]
    for ds in d["datasets"]:
        m = d["matrix"].get(ds["dataset"], {})
        score = "—" if ds["quality_score"] is None else f"{ds['quality_score']:.2f}"
        lines.append(f"| `{ds['dataset']}` | {int(ds['row_count'])} | {int(ds['quarantined_rows'] or 0)} | {score} | "
                     + " | ".join(_cell(m.get(dim)) for dim in DIMENSIONS) + " |")
    lines += ["", "## Rules with failures", "", "| Dataset | Rule | Dimension | Severity | Failed / evaluated | Outcome |",
              "|---|---|---|---|--:|---|"]
    for r in d["results"]:
        if r["failed"]:
            outcome = "rows quarantined" if r["severity"] == "error" and r["dataset"].startswith("silver.") else r["status"]
            lines.append(f"| `{r['dataset']}` | `{r['rule']}` | {r['dimension']} | {r['severity']} | "
                         f"{r['failed']} / {r['evaluated']} | {outcome} |")
    lines += ["", "## Quarantine by reason", ""]
    for table, reasons in d["quarantine"].items():
        lines.append(f"- `{table}`: " + ", ".join(f"`{k}` {v}" for k, v in reasons.items()))
    lines += ["", "## Governance findings", ""]
    lines += [f"- **{f['severity']}** `{f['dataset']}` · {f['kind']}: {f['detail']}" for f in d["findings"]] or ["None."]
    lines += ["", "## Glossary terms and their rules", "", "| Term | Linked rules | Mean pass rate |", "|---|:-:|:-:|"]
    for g in d["glossary_coverage"]:
        rate = "—" if g["pass_rate"] is None else f"{g['pass_rate']:.2f}%"
        lines.append(f"| {g['term']} | {g['rules']} | {rate} |")
    return "\n".join(lines) + "\n"


def write(con: duckdb.DuckDBPyConnection, folder: Path | None = None) -> Path:
    folder = folder or reports_dir()
    folder.mkdir(parents=True, exist_ok=True)
    d = data(con)
    (folder / "quality_report.json").write_text(json.dumps(d, indent=2, default=str) + "\n", encoding="utf-8")
    path = folder / "quality_report.md"
    path.write_text(markdown(d), encoding="utf-8")
    return path
