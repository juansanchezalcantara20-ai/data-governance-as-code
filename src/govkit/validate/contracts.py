"""Static validation of the ODCS v3 data contracts in contracts/.

* Required ODCS fields (apiVersion v3, kind, id, version as semver, status, domain, schema).
* Owner and Steward in ``team`` exist and govern the contract's domain.
* Classification is a known level; any personal-data column forces confidential or restricted.
* An SLA (latency or frequency) and a change policy (breaking / nonBreaking) are declared.
* Every property has a description and a known logical type; every ``businessName`` is a glossary term.
* Rules use known types, dimensions and severities; references point at governed datasets.
* Every SQL model has exactly one contract and every contract has a model.
"""

from __future__ import annotations

import re

from .. import contracts as contracts_mod
from ..lineage import model_columns
from ..paths import contracts_dir, governance, load_yaml
from ..privacy import PII_CATEGORIES
from . import Finding

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def check_contract(c: contracts_mod.Contract, users: dict, domains: dict, levels: dict, terms: set[str],
                   datasets: set[str]) -> list[Finding]:
    out: list[Finding] = []

    def err(msg, level="error"):
        out.append(Finding("contracts", level, c.name, msg))

    raw = c.raw
    if not str(raw.get("apiVersion", "")).startswith("v3"):
        err("apiVersion must be ODCS v3.x")
    if raw.get("kind") != "DataContract":
        err("kind must be DataContract")
    if not c.id:
        err("missing id")
    if not SEMVER.match(c.version):
        err(f"version '{c.version}' is not semver")
    if c.status not in ("draft", "active", "deprecated", "retired"):
        err(f"unknown status '{c.status}'")
    if c.path and c.path.name != f"{c.name}.odcs.yaml":
        err(f"file must be named {c.name}.odcs.yaml")
    dom = domains.get(c.domain)
    if dom is None:
        err(f"unknown domain '{c.domain}'")
    if not c.owner:
        err("team has no data_owner")
    elif c.owner not in users:
        err(f"owner '{c.owner}' is not in users.yaml")
    elif dom and c.owner != dom["owner"]:
        err(f"owner '{c.owner}' is not the owner of domain '{c.domain}'")
    if not c.steward:
        err("team has no data_steward")
    elif c.steward not in users:
        err(f"steward '{c.steward}' is not in users.yaml")
    elif dom and c.steward not in dom.get("stewards", []):
        err(f"steward '{c.steward}' is not a steward of domain '{c.domain}'")
    if c.classification not in levels:
        err(f"unknown classification '{c.classification}'")
    else:
        for col in c.pii_columns:
            eff = c.column_classification(col, levels)
            if levels[eff] < levels["confidential"]:
                err(f"has personal data ({col}) but it is classified '{eff}'; must be confidential or restricted")
    if not any(s.get("property") in ("latency", "frequency") for s in raw.get("slaProperties") or []):
        err("no freshness SLA (latency or frequency)")
    policy = c.change_policy
    if not policy.get("breaking") or not policy.get("nonBreaking"):
        err("changePolicy must list breaking and nonBreaking changes")
    if not c.primary_key:
        err("no primary key declared")
    if not c.purpose:
        err("description.purpose is empty")

    for p in c.properties:
        if not p.description:
            err(f"column '{p.name}' has no description")
        if p.logical_type not in contracts_mod.LOGICAL_TYPES:
            err(f"column '{p.name}' has unknown logicalType '{p.logical_type}'")
        if p.business_name and p.business_name not in terms:
            err(f"column '{p.name}' businessName '{p.business_name}' is not a glossary term")
        if p.classification and p.classification not in levels:
            err(f"column '{p.name}' has unknown classification '{p.classification}'")
        elif p.classification and c.classification in levels and levels[p.classification] < levels[c.classification]:
            err(f"column '{p.name}' is classified below its dataset ('{p.classification}' < '{c.classification}')")
        if p.pii and p.pii not in PII_CATEGORIES:
            err(f"column '{p.name}' has unknown personal-data category '{p.pii}'")
    for r in c.rules:
        if r.dimension not in contracts_mod.DIMENSIONS:
            err(f"rule '{r.name}' has unknown dimension '{r.dimension}'")
        if r.severity not in contracts_mod.SEVERITIES:
            err(f"rule '{r.name}' has unknown severity '{r.severity}'")
        for key in ("table", "referenceTable"):
            target = r.args.get(key)
            if target and target not in datasets:
                err(f"rule '{r.name}' references ungoverned dataset '{target}'")
    names = [r.name for r in c.rules]
    for dup in {n for n in names if names.count(n) > 1}:
        err(f"duplicate rule name '{dup}'")
    return out


def check() -> list[Finding]:
    out: list[Finding] = []
    contracts = []
    for path in sorted(contracts_dir().glob("*.odcs.yaml")):
        try:
            contracts.append(contracts_mod.parse(load_yaml(path), path))
        except (ValueError, KeyError, TypeError) as exc:
            out.append(Finding("contracts", "error", path.name, f"cannot be parsed: {exc}"))
    users = {u["id"]: u for u in governance("users")["users"]}
    domains = governance("domains")["domains"]
    levels = {k: v["rank"] for k, v in governance("classification")["levels"].items()}
    terms = {t["name"] for t in governance("glossary")["terms"]}
    models = model_columns()
    sources = {s["name"] for s in (load_yaml(contracts_dir().parent / "models" / "sources.yaml") or {}).get("sources", [])}
    datasets = set(models) | sources
    for c in contracts:
        out += check_contract(c, users, domains, levels, terms, datasets)
    named = {c.name for c in contracts}
    for model in sorted(set(models) - named):
        out.append(Finding("contracts", "error", model, "published model has no data contract"))
    for name in sorted(named - set(models)):
        out.append(Finding("contracts", "error", name, "contract has no SQL model"))
    return out
