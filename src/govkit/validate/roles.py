"""Validate roles.yaml and raci.yaml.

Rules:
* every role has a name, purpose, responsibilities, decisions and an ``escalates_to``
  that is another existing role (or null), and the escalation chain has no cycles;
* every RACI activity has exactly one Accountable and at least one Responsible;
* every role cited in the RACI exists, and only R/A/C/I letters are used.
"""

from __future__ import annotations

from ..paths import governance
from . import Finding

LETTERS = {"R", "A", "C", "I"}
REQUIRED = ("name", "purpose", "responsibilities", "decisions")


def check_roles(roles: dict) -> list[Finding]:
    out: list[Finding] = []
    for rid, role in roles.items():
        for key in REQUIRED:
            if not role.get(key):
                out.append(Finding("roles", "error", rid, f"missing '{key}'"))
        if "escalates_to" not in role:
            out.append(Finding("roles", "error", rid, "missing 'escalates_to' (use null for the top role)"))
        target = role.get("escalates_to")
        if target is not None and target not in roles:
            out.append(Finding("roles", "error", rid, f"escalates to unknown role '{target}'"))
    for rid in roles:
        seen, current = [rid], roles[rid].get("escalates_to")
        while current in roles:
            if current in seen:
                out.append(Finding("roles", "error", rid, "escalation cycle: " + " -> ".join(seen + [current])))
                break
            seen.append(current)
            current = roles[current].get("escalates_to")
    tops = [r for r, v in roles.items() if v.get("escalates_to") is None]
    if len(tops) != 1:
        out.append(Finding("roles", "error", "roles.yaml", f"expected exactly one top role, found {tops}"))
    return out


def check_raci(activities: list[dict], roles: dict) -> list[Finding]:
    out: list[Finding] = []
    ids = set()
    for act in activities:
        aid = act.get("id", "?")
        if aid in ids:
            out.append(Finding("raci", "error", aid, "duplicate activity id"))
        ids.add(aid)
        raci = act.get("raci") or {}
        for role, letter in raci.items():
            if role not in roles:
                out.append(Finding("raci", "error", aid, f"cites unknown role '{role}'"))
            if letter not in LETTERS:
                out.append(Finding("raci", "error", aid, f"invalid letter '{letter}' for {role}"))
        accountable = [r for r, v in raci.items() if v == "A"]
        if len(accountable) != 1:
            out.append(Finding("raci", "error", aid, f"must have exactly one Accountable, has {len(accountable)}"))
        if not any(v == "R" for v in raci.values()):
            out.append(Finding("raci", "error", aid, "must have at least one Responsible"))
    return out


def check() -> list[Finding]:
    roles = governance("roles").get("roles", {})
    activities = governance("raci").get("activities", [])
    return check_roles(roles) + check_raci(activities, roles)
