"""Validate governance/supuestos_valor.yaml: every assumption labelled in both languages and inside its range."""

from __future__ import annotations

from ..paths import governance, governance_dir
from . import Finding

REQUIRED = ("analyst_hour_cost", "rework_hours_per_bad_row", "bad_rows_per_wrong_decision", "wrong_decision_cost",
            "dispute_hours_per_metric", "people_per_dispute", "incident_hours", "exposure_probability_per_year")


def check_assumptions(doc: dict) -> list[Finding]:
    out: list[Finding] = []
    items = doc.get("assumptions", {})
    for key in REQUIRED:
        if key not in items:
            out.append(Finding("value", "error", key, "missing assumption"))
    for key, a in items.items():
        for field in ("value", "min", "max", "step", "unit", "es", "en"):
            if a.get(field) in (None, ""):
                out.append(Finding("value", "error", key, f"missing '{field}'"))
        if all(isinstance(a.get(f), (int, float)) for f in ("value", "min", "max")) and not a["min"] <= a["value"] <= a["max"]:
            out.append(Finding("value", "error", key, f"value {a['value']} outside [{a['min']}, {a['max']}]"))
    if items.get("bad_rows_per_wrong_decision", {}).get("min", 1) <= 0:
        out.append(Finding("value", "error", "bad_rows_per_wrong_decision", "min must be above zero (divisor)"))
    return out


def check() -> list[Finding]:
    if not (governance_dir() / "supuestos_valor.yaml").exists():
        return []
    return check_assumptions(governance("supuestos_valor"))
