"""Validate domains.yaml, users.yaml, classification.yaml and access_policy.yaml.

Detects: a domain without an Owner, an Owner without a Steward, people in the wrong
role for what they are named as, access that no role justifies, exceptions that are
not time-bound, and segregation-of-duties violations (a requester approving their own
request, or an approver who does not govern the domain).
"""

from __future__ import annotations

from datetime import date

from ..paths import governance
from . import Finding


def check_model(roles: dict, levels: dict, policy: dict, domains: dict, users: list[dict]) -> list[Finding]:
    out: list[Finding] = []
    by_id: dict[str, dict] = {}
    for u in users:
        if u["id"] in by_id:
            out.append(Finding("users", "error", u["id"], "duplicate user id"))
        by_id[u["id"]] = u

    # classification + policy shape
    for role in roles:
        if role not in policy.get("baseline", {}):
            out.append(Finding("policy", "error", role, "role has no access baseline (default is deny, so say so)"))
    for role, b in policy.get("baseline", {}).items():
        if role not in roles:
            out.append(Finding("policy", "error", role, "baseline for unknown role"))
        if b.get("up_to") not in levels:
            out.append(Finding("policy", "error", role, f"unknown classification '{b.get('up_to')}'"))
        if b.get("domains") not in ("assigned", "all"):
            out.append(Finding("policy", "error", role, "domains must be 'assigned' or 'all'"))
    req = policy.get("requests", {})
    for cls, approvers in req.get("approvers", {}).items():
        if cls not in levels:
            out.append(Finding("policy", "error", f"approvers.{cls}", "unknown classification"))
        for r in approvers:
            if r not in roles:
                out.append(Finding("policy", "error", f"approvers.{cls}", f"unknown role '{r}'"))

    # domains: owner and stewards
    for did, d in domains.items():
        owner = d.get("owner")
        if not owner:
            out.append(Finding("domains", "error", did, "domain has no Data Owner"))
        elif owner not in by_id:
            out.append(Finding("domains", "error", did, f"owner '{owner}' is not in users.yaml"))
        elif by_id[owner]["role"] != "data_owner":
            out.append(Finding("domains", "error", did, f"owner '{owner}' has role '{by_id[owner]['role']}', not data_owner"))
        stewards = d.get("stewards") or []
        if owner and not stewards:
            out.append(Finding("domains", "error", did, f"owner '{owner}' has no Data Steward appointed"))
        for s in stewards:
            if s not in by_id:
                out.append(Finding("domains", "error", did, f"steward '{s}' is not in users.yaml"))
            elif by_id[s]["role"] != "data_steward":
                out.append(Finding("domains", "error", did, f"steward '{s}' has role '{by_id[s]['role']}', not data_steward"))

    named = {d.get("owner") for d in domains.values()} | {s for d in domains.values() for s in d.get("stewards") or []}
    rank = levels
    for u in users:
        uid, role = u["id"], u.get("role")
        if role not in roles:
            out.append(Finding("users", "error", uid, f"unknown role '{role}'"))
            continue
        for key in ("name", "email", "area"):
            if not u.get(key):
                out.append(Finding("users", "error", uid, f"missing '{key}'"))
        for d in u.get("domains", []):
            if d != "*" and d not in domains:
                out.append(Finding("users", "error", uid, f"unknown domain '{d}'"))
        base = policy["baseline"].get(role, {})
        if "*" in u.get("domains", []) and base.get("domains") == "assigned":
            out.append(Finding("users", "error", uid, f"role '{role}' is domain-scoped; '*' breaks least privilege"))
        if role in ("data_owner", "data_steward") and uid not in named:
            out.append(Finding("users", "warning", uid, f"is a {role} but owns or stewards no domain"))

        for i, a in enumerate(u.get("access", [])):
            subject = f"{uid}.access[{i}]"
            dom, layers, up_to = a.get("domain"), a.get("layers", []), a.get("up_to")
            if up_to not in rank:
                out.append(Finding("access", "error", subject, f"unknown classification '{up_to}'"))
                continue
            if a.get("basis") == "role":
                problems = []
                scope_ok = (dom == "*" and base.get("domains") == "all") or (
                    dom != "*" and (base.get("domains") == "all" or dom in u.get("domains", [])))
                if not scope_ok:
                    problems.append(f"domain '{dom}' is outside the role scope")
                extra = [x for x in layers if x not in base.get("layers", [])]
                if extra:
                    problems.append(f"layers {extra} are not in the {role} baseline")
                if rank[up_to] > rank.get(base.get("up_to"), -1):
                    problems.append(f"'{up_to}' exceeds the {role} baseline '{base.get('up_to')}'")
                for p in problems:
                    out.append(Finding("access", "error", subject, f"access not justified by any role: {p}"))
            elif a.get("basis") == "request":
                out += _check_request(subject, uid, a, by_id, domains, req, rank)
            else:
                out.append(Finding("access", "error", subject, "access not justified by any role (no basis)"))
    return out


def _check_request(subject, uid, a, by_id, domains, req, rank) -> list[Finding]:
    out = []
    for key in ("ticket", "reason", "requested_by", "approved_by", "approved_on", "expires_on"):
        if not a.get(key):
            out.append(Finding("access", "error", subject, f"request-based access missing '{key}'"))
    if out:
        return out
    requester, approver, dom, up_to = a["requested_by"], a["approved_by"], a["domain"], a["up_to"]
    if requester != uid:
        out.append(Finding("access", "warning", subject, f"requested on behalf of {uid} by {requester}"))
    if requester == approver:
        out.append(Finding("sod", "error", subject, f"segregation of duties: {approver} approved their own request"))
    if approver not in by_id:
        out.append(Finding("access", "error", subject, f"approver '{approver}' is not in users.yaml"))
        return out
    allowed_roles = req.get("approvers", {}).get(up_to, [])
    if by_id[approver]["role"] not in allowed_roles:
        out.append(Finding("sod", "error", subject,
                           f"{approver} ({by_id[approver]['role']}) cannot approve '{up_to}' access; needs {allowed_roles}"))
    d = domains.get(dom, {})
    if approver != d.get("owner") and approver not in d.get("stewards", []):
        out.append(Finding("sod", "error", subject, f"{approver} does not govern domain '{dom}'"))
    if rank[up_to] > rank[req.get("max_classification", "internal")]:
        out.append(Finding("access", "error", subject, f"'{up_to}' data can never be granted through a request"))
    days = (date.fromisoformat(str(a["expires_on"])) - date.fromisoformat(str(a["approved_on"]))).days
    if days <= 0 or days > req.get("max_days", 90):
        out.append(Finding("access", "error", subject, f"exception lasts {days} days; must be 1-{req.get('max_days', 90)}"))
    return out


def check() -> list[Finding]:
    return check_model(
        roles=governance("roles")["roles"],
        levels={k: v["rank"] for k, v in governance("classification")["levels"].items()},
        policy=governance("access_policy"),
        domains=governance("domains")["domains"],
        users=governance("users")["users"],
    )
