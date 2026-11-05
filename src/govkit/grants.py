"""Compile the access policy into GRANT statements, so permissions come from the policy, never by hand.

Principals:
* one group per role and domain for domain-scoped roles (``gov_operations_data_steward``),
  one group per role for organisation-wide roles (``gov_data_custodian``);
* time-bound request grants go directly to the user, with ticket and expiry in a comment.

``render_postgres`` targets PostgreSQL-compatible engines (DuckDB has no GRANT support).
The Unity Catalog flavour lives in ``govkit.unity``.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import access


@dataclass(frozen=True)
class Grant:
    principal: str
    dataset: str
    kind: str        # group | user
    note: str = ""


def group_name(role: str, domain: str | None) -> str:
    return f"gov_{role}" if domain is None else f"gov_{domain}_{role}"


def groups() -> dict[str, list[str]]:
    """Group -> member user ids."""
    out: dict[str, list[str]] = {}
    pol = access.policy()["baseline"]
    for role, b in pol.items():
        if b["domains"] == "all":
            out[group_name(role, None)] = []
        else:
            for d in access.domains():
                out[group_name(role, d)] = []
    for uid, u in access.users().items():
        b = pol.get(u["role"], {})
        if b.get("domains") == "all":
            out[group_name(u["role"], None)].append(uid)
        else:
            for d in u.get("domains", []):
                out.setdefault(group_name(u["role"], d), []).append(uid)
    return out


def compile_grants() -> list[Grant]:
    lv = access.levels()
    grants: list[Grant] = []
    pol = access.policy()["baseline"]
    for ds in access.datasets():
        for role, b in pol.items():
            if ds["layer"] not in b["layers"] or lv[ds["classification"]] > lv[b["up_to"]]:
                continue
            masked = bool(ds["pii"]) and not b.get("unmasked_pii")
            note = "personal data masked" if masked else ""
            grants.append(Grant(group_name(role, None if b["domains"] == "all" else ds["domain"]), ds["name"], "group", note))
        for u in access.users().values():
            for g in u.get("access", []):
                if g.get("basis") != "request" or g["domain"] not in ("*", ds["domain"]) or ds["layer"] not in g["layers"]:
                    continue
                if lv[ds["classification"]] > lv[g["up_to"]]:
                    continue
                if access.role_allows(u, ds["domain"], ds["layer"], ds["classification"]):
                    continue
                grants.append(Grant(u["email"], ds["name"], "user", f"{g['ticket']}, expires {g['expires_on']}"))
    return sorted(set(grants), key=lambda g: (g.dataset, g.kind, g.principal))


def render_postgres() -> str:
    lines = ["-- Access grants compiled from governance/access_policy.yaml and users.yaml.",
             "-- PostgreSQL-compatible syntax. Regenerate with `govkit docs`; never edit by hand.", ""]
    members = groups()
    for g in sorted(members):
        lines.append(f"CREATE ROLE {g} NOLOGIN;")
    lines.append("")
    for g, users in sorted(members.items()):
        for uid in sorted(users):
            lines.append(f'GRANT {g} TO "{access.users()[uid]["email"]}";')
    lines.append("")
    for gr in compile_grants():
        target = gr.principal if gr.kind == "group" else f'"{gr.principal}"'
        note = f"  -- {gr.note}" if gr.note else ""
        lines.append(f"GRANT SELECT ON {gr.dataset} TO {target};{note}")
    return "\n".join(lines) + "\n"
