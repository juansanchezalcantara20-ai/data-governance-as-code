"""Access policy evaluation (least privilege by role, domain, layer and classification).

Used by the validator, the GRANT generator, the Unity Catalog generator and the UI,
so the same YAML decides who can read what everywhere.
"""

from __future__ import annotations

from datetime import date

from . import contracts as contracts_mod
from .paths import governance, load_yaml, models_dir


def levels() -> dict[str, int]:
    return {k: v["rank"] for k, v in governance("classification")["levels"].items()}


def policy() -> dict:
    return governance("access_policy")


def users() -> dict[str, dict]:
    return {u["id"]: u for u in governance("users")["users"]}


def domains() -> dict[str, dict]:
    return governance("domains")["domains"]


def datasets() -> list[dict]:
    """Every governed dataset with its layer, domain and classification (sources + contracts)."""
    out = []
    src = models_dir() / "sources.yaml"
    for s in (load_yaml(src).get("sources", []) if src.exists() else []):
        out.append({"name": s["name"], "layer": "bronze", "domain": s["domain"], "classification": s["classification"],
                    "pii": dict(s.get("pii") or {}), "description": s.get("description", "")})
    for c in contracts_mod.load_all():
        out.append({"name": c.name, "layer": c.layer, "domain": c.domain, "classification": c.classification,
                    "pii": c.pii_columns, "description": c.purpose})
    return out


def baseline(role: str) -> dict:
    return policy()["baseline"].get(role, {})


def _in_scope(user: dict, domain: str, entry_domain: str | None = None) -> bool:
    if entry_domain is not None:
        return entry_domain in ("*", domain)
    doms = user.get("domains", [])
    return "*" in doms or domain in doms


def role_allows(user: dict, domain: str, layer: str, classification: str) -> bool:
    b = baseline(user["role"])
    if not b:
        return False
    if b["domains"] == "assigned" and not _in_scope(user, domain):
        return False
    return layer in b["layers"] and levels()[classification] <= levels()[b["up_to"]]


def request_grants(user: dict, on: date | None = None) -> list[dict]:
    on = on or date.today()
    return [a for a in user.get("access", []) if a.get("basis") == "request"
            and date.fromisoformat(str(a["approved_on"])) <= on <= date.fromisoformat(str(a["expires_on"]))]


def can_read(user_id: str, dataset: dict, on: date | None = None) -> bool:
    user = users()[user_id]
    if role_allows(user, dataset["domain"], dataset["layer"], dataset["classification"]):
        return True
    return any(_in_scope(user, dataset["domain"], g["domain"]) and dataset["layer"] in g["layers"]
               and levels()[dataset["classification"]] <= levels()[g["up_to"]] for g in request_grants(user, on))


def sees_unmasked_pii(user_id: str, domain: str) -> bool:
    user = users()[user_id]
    b = baseline(user["role"])
    return bool(b.get("unmasked_pii")) and _in_scope(user, domain)


def governs(user_id: str, domain: str) -> bool:
    d = domains().get(domain, {})
    return user_id == d.get("owner") or user_id in d.get("stewards", [])
