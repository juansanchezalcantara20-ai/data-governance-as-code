"""Validate governance/maturity.yaml: the 11 DAMA-DMBOK2 areas, scores 1-5, evidence that exists."""

from __future__ import annotations

from ..paths import governance, root
from . import Finding

AREAS = {
    "data_governance", "data_architecture", "data_modeling", "data_storage_operations", "data_security",
    "data_integration", "document_content", "reference_master_data", "dw_bi", "metadata", "data_quality",
}


def check_assessment(doc: dict) -> list[Finding]:
    out: list[Finding] = []
    areas = {a.get("id"): a for a in doc.get("areas", [])}
    for missing in sorted(AREAS - areas.keys()):
        out.append(Finding("maturity", "error", missing, "DAMA-DMBOK2 area not assessed"))
    for extra in sorted(areas.keys() - AREAS):
        out.append(Finding("maturity", "error", extra, "not a DAMA-DMBOK2 knowledge area"))
    scale = {int(k) for k in doc.get("scale", {})}
    for aid, a in areas.items():
        score = a.get("score")
        if score not in scale or not 1 <= int(score) <= 5:
            out.append(Finding("maturity", "error", aid, f"score {score!r} is not on the 1-5 scale"))
            continue
        evidence = a.get("evidence") or []
        for path in evidence:
            if not (root() / path).exists():
                out.append(Finding("maturity", "error", aid, f"evidence '{path}' does not exist"))
        if score >= 3 and len(evidence) < 3:
            out.append(Finding("maturity", "error", aid, "a score of 3 or more needs at least three pieces of evidence"))
        for key in ("rationale", "next_level"):
            if not a.get(key):
                out.append(Finding("maturity", "error", aid, f"missing '{key}'"))
    for i, item in enumerate(doc.get("roadmap", [])):
        if item.get("area") not in AREAS:
            out.append(Finding("maturity", "error", f"roadmap[{i}]", f"unknown area '{item.get('area')}'"))
        if item.get("priority") not in (1, 2, 3) or item.get("effort") not in ("S", "M", "L"):
            out.append(Finding("maturity", "error", f"roadmap[{i}]", "priority must be 1-3 and effort S/M/L"))
    return out


def check() -> list[Finding]:
    return check_assessment(governance("maturity"))
