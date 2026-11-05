"""What governance avoided, in hours and soles per month, under ILLUSTRATIVE assumptions.

``facts`` reads only what the pipeline actually did (rows quarantined, blocking rules that fired, undeclared personal
data found, metrics with a single governed definition). ``compute`` combines those facts with the assumptions in
``governance/supuestos_valor.yaml``. The demo app re-implements ``compute`` in JavaScript so visitors can change the
assumptions; a test keeps both in step.
"""

from __future__ import annotations

import re
from datetime import date

import duckdb

from .paths import governance

DAYS_PER_MONTH = 30.4375


def assumptions() -> dict[str, float]:
    return {k: float(v["value"]) for k, v in governance("supuestos_valor")["assumptions"].items()}


def facts(con: duckdb.DuckDBPyConnection, as_of: date) -> dict:
    run_id = con.execute("SELECT run_id FROM meta.runs ORDER BY started_at DESC LIMIT 1").fetchone()[0]
    first = con.execute("SELECT min(d) FROM (SELECT opened_on AS d FROM silver.service_orders UNION ALL "
                        "SELECT opened_on FROM quarantine.service_orders)").fetchone()[0]
    months = round((as_of - first).days / DAYS_PER_MONTH, 2)
    by_table = dict(con.execute("SELECT dataset, quarantined_rows FROM meta.datasets WHERE quarantined_rows > 0 "
                                "ORDER BY dataset").fetchall())
    rules = con.execute("SELECT dataset, rule, dimension, failed FROM meta.quality_results WHERE run_id = ? "
                        "AND severity = 'error' AND failed > 0 ORDER BY failed DESC, dataset, rule", [run_id]).fetchall()
    pii: dict[str, set[str]] = {}
    for dataset, detail in con.execute("SELECT dataset, detail FROM meta.findings WHERE run_id = ? "
                                       "AND kind = 'undeclared_pii'", [run_id]).fetchall():
        m = re.search(r"column '([^']+)'", detail)
        if m:
            pii.setdefault(m.group(1), set()).add(dataset)
    pii_columns = sorted(pii)
    pii_rows = 0
    for col, datasets in pii.items():
        for table in sorted(d for d in datasets if d.startswith("silver.")):
            pii_rows += con.execute(f'SELECT count("{col}") FROM {table}').fetchone()[0]
    metrics = [t["id"] for t in governance("glossary")["terms"] if t["type"] == "metric" and t["status"] == "approved"]
    return {
        "months_observed": months,
        "quarantined_rows": int(sum(by_table.values())),
        "quarantined_by_dataset": {k: int(v) for k, v in by_table.items()},
        "blocking_rules_fired": [{"dataset": d, "rule": r, "dimension": m, "rows": int(f)} for d, r, m, f in rules],
        "undeclared_pii_columns": pii_columns,
        "undeclared_pii_rows": int(pii_rows),
        "governed_metrics": len(metrics),
    }


def compute(f: dict, a: dict[str, float]) -> dict:
    """Monthly hours and soles not lost. Keep in step with app/js/value.js (same formula)."""
    rows_pm = f["quarantined_rows"] / f["months_observed"]
    rework_h = rows_pm * a["rework_hours_per_bad_row"]
    decisions = rows_pm / a["bad_rows_per_wrong_decision"]
    dispute_h = f["governed_metrics"] * a["dispute_hours_per_metric"] * a["people_per_dispute"]
    pii_h = len(f["undeclared_pii_columns"]) * a["incident_hours"] * a["exposure_probability_per_year"] / 12
    parts = {
        "rework": {"hours": rework_h, "pen": rework_h * a["analyst_hour_cost"]},
        "wrong_decisions": {"hours": 0.0, "pen": decisions * a["wrong_decision_cost"], "count": decisions},
        "definition_disputes": {"hours": dispute_h, "pen": dispute_h * a["analyst_hour_cost"]},
        "personal_data_risk": {"hours": pii_h, "pen": pii_h * a["analyst_hour_cost"]},
    }
    for p in parts.values():
        for k in list(p):
            p[k] = round(p[k], 2)
    return {
        "bad_rows_per_month": round(rows_pm, 2),
        "parts": parts,
        "total_hours": round(sum(p["hours"] for p in parts.values()), 1),
        "total_pen": round(sum(p["pen"] for p in parts.values())),
    }
