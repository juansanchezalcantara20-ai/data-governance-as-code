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
    s = sub.add_parser("docs", help="generate documentation from governance YAML and run metadata")
    s.set_defaults(func=_docs)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
