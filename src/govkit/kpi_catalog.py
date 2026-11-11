"""Apply govkit's glossary, ownership and contract checks to an external KPI catalog (project 2).

The catalog (``examples/kpi_catalog/catalog.yaml``) uses its own format. The checks are the same standards this
repository enforces on itself, translated to that format:

* glossary: definition, formula and unit present; definition does not use the KPI's own name; related KPIs exist;
* ownership: an accountable owner is named; a steward is named (this repo's standard requires both);
* contract: the input table is declared for the KPI's case, input columns are listed, a reference SQL exists, and the
  traffic-light thresholds are consistent with the direction.

It is a report, not a CI gate: the catalog belongs to another repository.
"""

from __future__ import annotations

import re

from .paths import load_yaml, root

CHECKS = {
    "definition": ("glossary", "Has a definition, a formula and a unit"),
    "not_circular": ("glossary", "Definition does not use the KPI's own name"),
    "related_exist": ("glossary", "Every related KPI exists in the catalog"),
    "owner": ("ownership", "An accountable owner is named"),
    "steward": ("ownership", "A data steward is named"),
    "input_declared": ("contract", "Input table is declared for the case and columns are listed"),
    "reference_sql": ("contract", "A reference SQL query exists"),
    "thresholds": ("contract", "Traffic-light thresholds agree with the direction"),
}


def _thresholds_ok(k: dict) -> bool:
    t, d = k.get("thresholds") or {}, k.get("direction")
    g, a = t.get("green"), t.get("amber")
    if g is None or a is None:
        return False
    if d == "higher_is_better":
        return g >= a
    if d == "lower_is_better":
        return g <= a
    if d == "target_range":
        return isinstance(g, list) and isinstance(a, list) and a[0] <= g[0] <= g[1] <= a[1]
    return False


def evaluate(path=None) -> dict:
    doc = load_yaml(path or root() / "examples" / "kpi_catalog" / "catalog.yaml")
    kpis, cases = doc.get("kpis", []), doc.get("cases", {})
    ids = {k["id"] for k in kpis}
    per_kpi = []
    for k in kpis:
        name = re.sub(r"\s*\(.*\)$", "", k.get("name", ""))
        inp = k.get("input") or {}
        results = {
            "definition": all(k.get(f) for f in ("definition", "formula", "unit")),
            "not_circular": not re.search(rf"\b{re.escape(name)}\b", str(k.get("definition", "")), re.I),
            "related_exist": all(r in ids for r in k.get("related") or []),
            "owner": bool(k.get("owner")),
            "steward": bool(k.get("steward")),
            "input_declared": inp.get("table") in (cases.get(k.get("case"), {}).get("tables") or [])
            and bool(inp.get("columns")),
            "reference_sql": bool(k.get("sql")),
            "thresholds": _thresholds_ok(k),
        }
        per_kpi.append({"id": k["id"], "name": k.get("name"), "case": k.get("case"), "owner": k.get("owner"),
                        "results": results})
    summary = []
    for check, (family, text) in CHECKS.items():
        failed = [p["id"] for p in per_kpi if not p["results"][check]]
        summary.append({"check": check, "family": family, "description": text, "passed": len(per_kpi) - len(failed),
                        "failed": len(failed), "failed_kpis": failed})
    total = len(per_kpi) * len(CHECKS)
    passed = sum(s["passed"] for s in summary)
    return {"source": "examples/kpi_catalog/catalog.yaml", "origin_commit": "67e3e37", "kpis": len(per_kpi),
            "cases": sorted(cases), "checks": summary, "pass_rate": round(100 * passed / total, 1) if total else 0,
            "per_kpi": per_kpi}
