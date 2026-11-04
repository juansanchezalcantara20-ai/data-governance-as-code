"""Does the real data honour its contract?

``conformance`` compares a built table with its ODCS contract: every declared column
must exist with a compatible type, and no undeclared column may appear. Combined with
the contract's quality rules (``required``, ``unique``, keys, SLA, library and SQL rules),
this is what ``govkit verify`` enforces in CI: a schema change in a SQL model that breaks
the contract makes the build fail.
"""

from __future__ import annotations

from .contracts import LOGICAL_TYPES, Contract


def _base(t: str) -> str:
    return t.upper().split("(")[0].strip()


def conformance(contract: Contract, actual: dict[str, str]) -> list[tuple[str, str]]:
    """Return (severity, detail) violations of the contract schema."""
    out: list[tuple[str, str]] = []
    for p in contract.properties:
        if p.name not in actual:
            out.append(("error", f"column '{p.name}' is declared in contract v{contract.version} but missing"))
            continue
        real = _base(actual[p.name])
        allowed = LOGICAL_TYPES.get(p.logical_type, set())
        if real not in allowed:
            out.append(("error", f"column '{p.name}' is {real}, contract says {p.logical_type} ({p.physical_type})"))
        elif _base(p.physical_type) != real:
            out.append(("warning", f"column '{p.name}' physical type {real} differs from declared {p.physical_type}"))
    for name in actual:
        if not name.startswith("_") and contract.column(name) is None:
            out.append(("error", f"column '{name}' exists in the data but is not declared in the contract"))
    return out
