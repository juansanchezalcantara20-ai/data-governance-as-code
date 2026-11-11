"""Validate governance/glossary.yaml.

* Owner and Steward exist in users.yaml (and should govern the term's domain).
* Every metric has a formula and a source; every source table/column exists in a SQL model.
* No circular definitions: no term defined with its own name, no cycle in ``depends_on``.
* No orphans: every term is used by at least one data contract (``businessName``) or
  is the source column of a model.
* Linked quality rules exist in the contract of the source table.
"""

from __future__ import annotations

import re
from datetime import date

from .. import contracts as contracts_mod
from ..lineage import model_columns
from ..paths import governance
from . import Finding

TYPES = ("concept", "attribute", "metric")
STATUSES = ("draft", "approved")
REQUIRED = ("id", "name", "domain", "type", "definition", "owner", "steward", "status", "next_review")


def _cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    found, state = [], {}

    def visit(node, path):
        state[node] = 1
        for nxt in graph.get(node, []):
            if state.get(nxt) == 1:
                found.append(path[path.index(nxt):] + [nxt] if nxt in path else [node, nxt])
            elif nxt in graph and not state.get(nxt):
                visit(nxt, path + [nxt])
        state[node] = 2

    for n in graph:
        if not state.get(n):
            visit(n, [n])
    return found


def check_terms(terms: list[dict], users: dict, domains: dict, models: dict[str, list[str]],
                contracts: dict, today: date | None = None) -> list[Finding]:
    out: list[Finding] = []
    ids: dict[str, dict] = {}
    names = set()
    for t in terms:
        tid = t.get("id", "?")
        for key in REQUIRED:
            if not t.get(key):
                out.append(Finding("glossary", "error", tid, f"missing '{key}'"))
        if tid in ids:
            out.append(Finding("glossary", "error", tid, "duplicate id"))
        if t.get("name", "").lower() in names:
            out.append(Finding("glossary", "error", tid, f"duplicate name '{t.get('name')}'"))
        ids[tid] = t
        names.add(t.get("name", "").lower())

    used_names = {p.business_name for c in contracts.values() for p in c.properties if p.business_name}
    for tid, t in ids.items():
        if t.get("type") not in TYPES:
            out.append(Finding("glossary", "error", tid, f"type must be one of {TYPES}"))
        if t.get("status") not in STATUSES:
            out.append(Finding("glossary", "error", tid, f"status must be one of {STATUSES}"))
        for role, key in (("owner", "owner"), ("steward", "steward")):
            uid = t.get(key)
            if uid and uid not in users:
                out.append(Finding("glossary", "error", tid, f"{role} '{uid}' does not exist in users.yaml"))
        dom = domains.get(t.get("domain"))
        if dom is None:
            out.append(Finding("glossary", "error", tid, f"unknown domain '{t.get('domain')}'"))
        else:
            if t.get("owner") in users and t["owner"] != dom["owner"]:
                out.append(Finding("glossary", "warning", tid, f"owner is not the {t['domain']} domain owner"))
            if t.get("steward") in users and t["steward"] not in dom.get("stewards", []):
                out.append(Finding("glossary", "warning", tid, f"steward is not a {t['domain']} domain steward"))

        src = t.get("source") or {}
        if t.get("type") == "metric":
            if not t.get("formula"):
                out.append(Finding("glossary", "error", tid, "metric without a formula"))
            if not src:
                out.append(Finding("glossary", "error", tid, "metric without a source table/column"))
        source_ok = False
        if src:
            cols = models.get(src.get("table"))
            if cols is None:
                out.append(Finding("glossary", "error", tid, f"source table '{src.get('table')}' is not a model"))
            elif src.get("column") not in cols:
                out.append(Finding("glossary", "error", tid, f"source column '{src.get('column')}' not in {src['table']}"))
            else:
                source_ok = True
        if not source_ok and t.get("name") not in used_names:
            out.append(Finding("glossary", "error", tid, "orphan term: used by no contract and no model"))

        definition = str(t.get("definition", ""))
        if t.get("name") and re.search(rf"\b{re.escape(t['name'])}\b", definition, re.I):
            out.append(Finding("glossary", "error", tid, "circular definition: the definition uses the term itself"))
        for dep in t.get("depends_on") or []:
            if dep not in ids:
                out.append(Finding("glossary", "error", tid, f"depends on unknown term '{dep}'"))
        for rel in t.get("related") or []:
            if rel not in ids:
                out.append(Finding("glossary", "error", tid, f"related to unknown term '{rel}'"))

        contract = contracts.get(src.get("table")) if src else None
        rules = t.get("quality_rules") or []
        if contract:
            known = {r.name for r in contract.rules}
            for r in rules:
                if r not in known:
                    out.append(Finding("glossary", "error", tid, f"quality rule '{r}' not found in {contract.name}"))
        elif rules:
            out.append(Finding("glossary", "warning", tid, f"no contract yet for {src.get('table')}; rules unchecked"))

        overdue = today and t.get("next_review") and date.fromisoformat(str(t["next_review"])) < today
        if t.get("status") == "approved" and overdue:
            out.append(Finding("glossary", "warning", tid, f"review overdue since {t['next_review']}"))

    for cycle in _cycles({tid: list(t.get("depends_on") or []) for tid, t in ids.items()}):
        out.append(Finding("glossary", "error", cycle[0], "circular definition: " + " -> ".join(cycle)))
    return out


def check_translations(terms: list[dict], translations: dict) -> list[Finding]:
    """Every term has a Spanish name, definition and example and an English example; no circular Spanish definition."""
    out: list[Finding] = []
    ids = {t["id"] for t in terms}
    for tid in sorted(ids - translations.keys()):
        out.append(Finding("glossary", "error", tid, "missing translation in glossary_translations.yaml"))
    for tid in sorted(translations.keys() - ids):
        out.append(Finding("glossary", "error", tid, "translation for a term that does not exist"))
    for tid, tr in translations.items():
        es, en = tr.get("es") or {}, tr.get("en") or {}
        for key in ("name", "definition", "example"):
            if not es.get(key):
                out.append(Finding("glossary", "error", tid, f"missing Spanish '{key}'"))
        if not en.get("example"):
            out.append(Finding("glossary", "error", tid, "missing English example"))
        if es.get("name") and re.search(rf"\b{re.escape(es['name'])}\b", str(es.get("definition", "")), re.I):
            out.append(Finding("glossary", "error", tid, "circular Spanish definition: it uses the term itself"))
    return out


def check() -> list[Finding]:
    from ..paths import governance_dir

    translations_path = governance_dir() / "glossary_translations.yaml"
    translations = governance("glossary_translations").get("terms", {}) if translations_path.exists() else None
    findings = [] if translations is None else check_translations(governance("glossary")["terms"], translations)
    return findings + check_terms(
        terms=governance("glossary")["terms"],
        users={u["id"]: u for u in governance("users")["users"]},
        domains=governance("domains")["domains"],
        models=model_columns(),
        contracts=contracts_mod.by_name(),
        today=date.today(),
    )
