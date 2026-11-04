"""Command line interface: ``govkit <command>``."""

from __future__ import annotations

import argparse
import sys


def _generate(args) -> int:
    from . import generator

    counts = generator.generate(seed=args.seed)
    print("Generated: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    return 0


def _run(_args) -> int:
    from . import pipeline

    print("Running Medallion pipeline...")
    report = pipeline.run()
    failures = [r for r in report.results if r.status == "fail"]
    warnings = [r for r in report.results if r.status == "warn"]
    print(f"\nRun {report.run_id} (as of {report.as_of}): {report.status.upper()}")
    print(f"  datasets built: {report.datasets} | quarantined rows: {report.quarantined}")
    print(f"  blocking rules with failures: {len(failures)} | warning rules with failures: {len(warnings)}")
    for dataset, kind, severity, detail in report.findings:
        print(f"  - [{severity}] {dataset} · {kind}: {detail}")
    for error in report.errors:
        print(f"  ERROR {error}")
    return 1 if report.status == "failed" else 0


def _validate(args) -> int:
    from .validate import run_all

    findings = run_all(args.only)
    errors = [f for f in findings if f.level == "error"]
    for f in findings:
        print(f)
    print(f"\n{len(errors)} errors, {len(findings) - len(errors)} warnings.")
    return 1 if errors else 0


def _lineage(args) -> int:
    from . import lineage
    from .db import connect

    parts = args.target.split(".")
    dataset, column = ".".join(parts[:2]), (parts[2] if len(parts) > 2 else None)
    con = connect(read_only=True)
    walk = lineage.downstream if args.impact else lineage.upstream
    print(f"{'Impact of' if args.impact else 'Upstream of'} {args.target}:")
    for n in walk(con, dataset, column):
        print(f"  {'  ' * (n['depth'] - 1)}└─ {n['dataset']}.{n['column']}")
    return 0


def _verify(_args) -> int:
    from .db import connect

    con = connect(read_only=True)
    run = con.execute("SELECT run_id, status FROM meta.runs ORDER BY started_at DESC LIMIT 1").fetchone()
    if not run:
        print("No pipeline run found. Run: govkit run")
        return 1
    rows = con.execute("""
        SELECT d.dataset, d.contract_version,
               (SELECT count(*) FROM meta.findings f WHERE f.run_id = ? AND f.dataset = d.dataset
                  AND f.kind = 'contract_violation' AND f.severity = 'error') AS schema_violations,
               (SELECT count(*) FROM meta.quality_results q WHERE q.run_id = ? AND q.dataset = d.dataset
                  AND q.status = 'fail') AS failed_rules
        FROM meta.datasets d WHERE d.contract_version IS NOT NULL ORDER BY d.dataset""", [run[0], run[0]]).fetchall()
    broken = 0
    print(f"Data vs contract (run {run[0]}):")
    for dataset, version, schema, failed in rows:
        gold_fail = dataset.startswith("gold.") and failed
        ok = not schema and not gold_fail
        broken += not ok
        note = "quarantined, see report" if failed and dataset.startswith("silver.") else ""
        print(f"  {'✓' if ok else '✗'} {dataset:<34} v{version:<7} schema violations={schema} failed rules={failed} {note}")
    for (detail,) in con.execute("SELECT dataset || ': ' || detail FROM meta.findings WHERE run_id = ? "
                                 "AND kind = 'contract_violation'", [run[0]]).fetchall():
        print(f"  - {detail}")
    from . import contracts as contracts_mod

    built = {r[0] for r in rows}
    for name in sorted(set(contracts_mod.by_name()) - built):
        broken += 1
        print(f"  ✗ {name:<34} not built in this run (see run errors: upstream contract break?)")
    print(f"{broken} dataset(s) break their contract.")
    return 1 if broken else 0


def _compat(args) -> int:
    from . import compat

    problems = compat.check_against(args.base)
    for p in problems:
        print(f"[ERROR] {p}")
    print(f"{len(problems)} change-policy violation(s) against {args.base}.")
    return 1 if problems else 0


def _deploy(_args) -> int:
    from . import unity

    for path in unity.build():
        print(f"wrote {path}  (NOT EXECUTED: apply manually, see deploy/unity_catalog/README.md)")
    return 0


def _export(_args) -> int:
    from . import contracts as contracts_mod
    from .db import connect
    from .paths import data_dir

    out = data_dir() / "export"
    out.mkdir(parents=True, exist_ok=True)
    con = connect(read_only=True)
    for c in contracts_mod.load_all():
        path = out / f"{c.name}.parquet"
        con.execute(f"COPY {c.name} TO '{path}' (FORMAT parquet)")
        print(f"wrote {path}")
    return 0


def _docs(_args) -> int:
    from . import docs

    for path in docs.build_all():
        print(f"wrote {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="govkit", description="Governance as code on a Medallion lakehouse")
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("generate", help="generate the seeded synthetic source files")
    s.add_argument("--seed", type=int, default=42)
    s.set_defaults(func=_generate)
    s = sub.add_parser("run", help="run the bronze → silver → gold pipeline")
    s.set_defaults(func=_run)
    s = sub.add_parser("validate", help="validate governance YAML (fails on errors)")
    s.add_argument("--only", nargs="*", help="run only these validators")
    s.set_defaults(func=_validate)
    s = sub.add_parser("lineage", help="upstream lineage or downstream impact of layer.table[.column]")
    s.add_argument("target")
    s.add_argument("--impact", action="store_true")
    s.set_defaults(func=_lineage)
    s = sub.add_parser("verify", help="check that the data of the last run honours every contract")
    s.set_defaults(func=_verify)
    s = sub.add_parser("compat", help="check contract changes against a git ref follow the change policy")
    s.add_argument("--base", default="origin/main")
    s.set_defaults(func=_compat)
    s = sub.add_parser("deploy", help="generate Unity Catalog SQL in deploy/unity_catalog (not executed)")
    s.set_defaults(func=_deploy)
    s = sub.add_parser("export", help="export governed silver and gold tables to Parquet for upload")
    s.set_defaults(func=_export)
    s = sub.add_parser("docs", help="generate documentation from governance YAML and run metadata")
    s.set_defaults(func=_docs)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
