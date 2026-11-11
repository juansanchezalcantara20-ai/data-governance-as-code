"""Export everything the demo app shows to ``app/data/*.json``.

The app has no backend: every number on screen comes from these files, and these files come only from the engine
(governance YAML, contracts, the pipeline run and its metadata). CI regenerates them and fails if the committed copy
differs (``python -m govkit export-app --check``), so the demo cannot show anything the engine did not produce.

Output is deterministic: no timestamps, no run ids, stable ordering. No personal data leaves unmasked.
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import re
from pathlib import Path

import duckdb

from . import access, compat, kpi_catalog, lineage, privacy, report, value
from . import contracts as contracts_mod
from .db import connect
from .generator import as_of_date
from .paths import contracts_dir, docs_dir, governance, load_yaml, models_dir, root
from .validate import access as access_validator

COMPANY = "Servicios Andinos de Campo S.A.C."
PERSONAS = [
    ("data_owner", "riley.placeholder"),
    ("data_custodian", "drew.stubbs"),
    ("data_consumer", "jamie.fakeley"),
    ("field_technician", "rowan.pretendez"),
    ("auditor", "ellis.checkwell"),
]


def out_dir() -> Path:
    return root() / "app" / "data"


def _clean(v):
    if isinstance(v, float):
        return round(v, 4)
    if isinstance(v, (dt.date, dt.datetime)):
        return v.isoformat()[:10]
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    return v


def _domain_role_users() -> dict:
    users = access.users()
    return {d: {"owner": users[x["owner"]]["name"], "stewards": [users[s]["name"] for s in x["stewards"]]}
            for d, x in access.domains().items()}


# ------------------------------------------------------------------ governance model
def roles_doc() -> dict:
    roles = governance("roles")["roles"]
    return {"roles": [{"id": k, **v} for k, v in roles.items()],
            "raci": governance("raci")["activities"],
            "domains": [{"id": k, "name": v["name"], "description": v["description"],
                         "owner_role": "data_owner", "steward_role": "data_steward"}
                        for k, v in access.domains().items()]}


def access_doc() -> dict:
    lv = access.levels()
    pol = access.policy()
    datasets = access.datasets()
    personas = []
    for role, uid in PERSONAS:
        u = access.users()[uid]
        views = {}
        for ds in datasets:
            top = access.max_level(uid, ds, as_of_date())
            views[ds["name"]] = {"level": top, "columns": access.column_view(uid, ds, ds["columns"], as_of_date())
                                 if ds.get("columns") else {}}
        personas.append({"role": role, "user": uid, "name": u["name"], "domains": u["domains"],
                         "can_act_on_quarantine": access.can_act_on_quarantine(uid),
                         "read_only": bool(access.baseline(role).get("read_only")), "datasets": views})
    matrix = []
    for role, b in pol["baseline"].items():
        row = {"role": role, "domains": b["domains"], "layers": b["layers"], "up_to": b["up_to"],
               "unmasked_personal_data": bool(b.get("unmasked_pii")), "read_only": bool(b.get("read_only")),
               "cells": {}}
        for d in access.domains():
            row["cells"][d] = {lvl: (lv[lvl] <= lv[b["up_to"]]) for lvl in lv}
        matrix.append(row)
    findings = access_validator.check()
    checks = [
        {"id": "domain_owner", "passed": not any("no Data Owner" in f.message for f in findings)},
        {"id": "owner_steward", "passed": not any("no Data Steward" in f.message for f in findings)},
        {"id": "justified_access", "passed": not any("not justified" in f.message for f in findings)},
        {"id": "segregation_of_duties", "passed": not any(f.check == "sod" for f in findings)},
        {"id": "exceptions_expire", "passed": not any("must be 1-" in f.message for f in findings)},
    ]
    exceptions = []
    for u in access.users().values():
        for a in u.get("access", []):
            if a.get("basis") == "request":
                exceptions.append({"user": u["name"], "role": u["role"], "domain": a["domain"], "up_to": a["up_to"],
                                   "ticket": a["ticket"], "requested_by_role": access.users()[a["requested_by"]]["role"],
                                   "approved_by_role": access.users()[a["approved_by"]]["role"],
                                   "same_person": a["requested_by"] == a["approved_by"],
                                   "approved_on": str(a["approved_on"]), "expires_on": str(a["expires_on"])})
    return {"levels": list(lv), "personas": personas, "matrix": matrix, "checks": checks,
            "sod_conflicts": [f.message for f in findings if f.check == "sod"], "exceptions": exceptions,
            "quarantine_actions": pol.get("quarantine_actions", [])}


def glossary_doc() -> dict:
    terms = governance("glossary")["terms"]
    tr = governance("glossary_translations")["terms"]
    used: dict[str, list[str]] = {}
    for c in contracts_mod.load_all():
        for p in c.properties:
            if p.business_name:
                used.setdefault(p.business_name, []).append(f"{c.name}.{p.name}")
    out = []
    for t in sorted(terms, key=lambda x: tr[x["id"]]["es"]["name"].lower()):
        out.append({"id": t["id"], "type": t["type"], "domain": t["domain"], "status": t["status"],
                    "next_review": str(t["next_review"]), "owner_role": "data_owner", "steward_role": "data_steward",
                    "name": {"en": t["name"], "es": tr[t["id"]]["es"]["name"]},
                    "definition": {"en": t["definition"], "es": tr[t["id"]]["es"]["definition"]},
                    "example": {"en": tr[t["id"]]["en"]["example"], "es": tr[t["id"]]["es"]["example"]},
                    "formula": t.get("formula"), "depends_on": t.get("depends_on") or [],
                    "source": t.get("source"), "quality_rules": t.get("quality_rules") or [],
                    "synonyms": t.get("synonyms") or [], "related": t.get("related") or [],
                    "used_in": sorted(used.get(t["name"], []))})
    return {"terms": out}


# ------------------------------------------------------------------ data
def _sample(con, name: str, pii: dict[str, str]) -> list[dict]:
    df = con.execute(f"SELECT * FROM {name} ORDER BY ALL LIMIT 5").fetchdf()
    df = df[[c for c in df.columns if not c.startswith("_")]]
    df = privacy.mask_frame(df, pii)
    rows = []
    for rec in df.to_dict("records"):
        rows.append({k: (None if v is None or (isinstance(v, float) and v != v) else _clean(v)) for k, v in rec.items()})
    return rows


def catalog_doc(con: duckdb.DuckDBPyConnection) -> dict:
    meta = {r[0]: r for r in con.execute("SELECT dataset, row_count, quarantined_rows, quality_score FROM meta.datasets"
                                         ).fetchall()}
    cols = con.execute("SELECT dataset, column_name, actual_type, pii_detected FROM meta.columns ORDER BY dataset, position"
                       ).fetchall()
    by_ds: dict[str, list] = {}
    for d, c, t, det in cols:
        by_ds.setdefault(d, []).append((c, t, det))
    contracts = contracts_mod.by_name()
    sources = {s["name"]: s for s in load_yaml(models_dir() / "sources.yaml")["sources"]}
    exposures = load_yaml(models_dir() / "exposures.yaml")["exposures"]
    lv = access.levels()
    out = []
    for name in sorted(meta, key=lambda n: (["bronze", "silver", "gold"].index(n.split(".")[0]), n)):
        c = contracts.get(name)
        s = sources.get(name, {})
        detected = {col: det for col, _, det in by_ds.get(name, []) if det}
        pii = dict(c.pii_columns if c else s.get("pii") or {})
        mask = {**detected, **pii}
        columns = []
        for col, typ, det in by_ds.get(name, []):
            if col.startswith("_"):
                continue
            p = c.column(col) if c else None
            cls = c.column_classification(col, lv) if c else s.get("classification")
            columns.append({"name": col, "type": typ, "description": p.description if p else None,
                            "classification": cls, "personal_data": pii.get(col),
                            "undeclared_personal_data": det if det and col not in pii else None,
                            "business_term": p.business_name if p else None,
                            "required": bool(p and p.required), "key": bool(p and p.primary_key)})
        rows, quarantined, score = meta[name][1:]
        ups = sorted({x["dataset"] for x in lineage.upstream(con, name) if x["depth"] == 1})
        downs = sorted({x["dataset"] for x in lineage.downstream(con, name) if x["depth"] == 1})
        out.append({
            "id": name, "layer": name.split(".")[0], "domain": c.domain if c else s.get("domain"),
            "classification": c.classification if c else s.get("classification"),
            "contract_version": c.version if c else None, "rows": int(rows), "quarantined": int(quarantined or 0),
            "quality_score": score, "description": c.purpose if c else s.get("description"),
            "usage": c.usage if c else None, "system": s.get("system"), "columns": columns,
            "consumers": sorted(e["name"] for e in exposures if name in e["depends_on"]),
            "upstream": ups, "downstream": downs, "sample": _sample(con, name, mask),
        })
    return {"datasets": out, "domain_people": _domain_role_users()}


def contracts_doc(con: duckdb.DuckDBPyConnection) -> dict:
    exposures = load_yaml(models_dir() / "exposures.yaml")["exposures"]
    out = []
    for c in contracts_mod.load_all():
        downs = sorted({x["dataset"] for x in lineage.downstream(con, c.name)
                        if not x["dataset"].startswith("file:")})
        sla = next(({"kind": s["property"], "value": s["value"], "unit": s.get("unit")}
                    for s in c.raw.get("slaProperties", [])), None)
        out.append({"id": c.name, "version": c.version, "status": c.status, "domain": c.domain,
                    "classification": c.classification, "purpose": c.purpose, "usage": c.usage,
                    "limitations": c.limitations, "sla": sla, "change_policy": c.change_policy,
                    "consumers": sorted({e["name"] for e in exposures if c.name in e["depends_on"]} |
                                        {d for d in downs if not d.startswith("exposure:")}),
                    "columns": [{"name": p.name, "logical_type": p.logical_type, "required": p.required,
                                 "key": p.primary_key, "business_term": p.business_name, "personal_data": p.pii,
                                 "classification": c.column_classification(p.name, access.levels())}
                                for p in c.properties],
                    "rules": len(c.rules),
                    "yaml": (contracts_dir() / f"{c.name}.odcs.yaml").read_text(encoding="utf-8")})
    # A real compatibility check run by the engine on a simulated breaking change (rename without a major bump).
    base = contracts_mod.by_name()["gold.service_order_economics"]
    changed = copy.deepcopy(base)
    changed.properties = [p for p in changed.properties if p.name != "gross_margin"]
    changed.version = base.version.split(".")[0] + ".1.0"
    history = {"contract": base.name, "from_version": base.version, "to_version": changed.version,
               "change": "gross_margin renamed to margin_amount in the SQL model",
               "engine_output": compat.check_pair(base, changed),
               "correct_version": str(int(base.version.split(".")[0]) + 1) + ".0.0",
               "correct_output": compat.check_pair(base, _bumped(changed, base))}
    return {"contracts": out, "history": history}


def _bumped(c, base):
    c = copy.deepcopy(c)
    c.version = str(int(base.version.split(".")[0]) + 1) + ".0.0"
    return c


def quality_doc(con: duckdb.DuckDBPyConnection) -> dict:
    d = report.data(con)
    domains = {c.name: c.domain for c in contracts_mod.load_all()}
    rules = []
    for r in d["results"]:
        c = contracts_mod.by_name().get(r["dataset"])
        rule = next((x for x in c.rules if x.name == r["rule"]), None) if c else None
        rules.append({"dataset": r["dataset"], "domain": domains.get(r["dataset"]), "rule": r["rule"],
                      "kind": r["kind"], "column": r["column_name"], "dimension": r["dimension"],
                      "severity": r["severity"], "origin": r["origin"], "evaluated": int(r["evaluated"]),
                      "failed": int(r["failed"]), "pass_rate": r["pass_rate"], "status": r["status"],
                      "args": _clean(rule.args) if rule else {}})
    by_domain = {}
    for r in rules:
        x = by_domain.setdefault(r["domain"], {"pass": 0, "fail": 0, "warn": 0})
        x[r["status"]] += 1
    return {"as_of": d["as_of"], "status": d["status"], "by_dimension": d["by_dimension"],
            "by_domain": by_domain, "rules": rules, "glossary_coverage": d["glossary_coverage"]}


def quarantine_doc(con: duckdb.DuckDBPyConnection) -> dict:
    out = []
    for (table,) in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'quarantine' "
                                "ORDER BY 1").fetchall():
        rows = con.execute(f"SELECT r, count(*) FROM (SELECT unnest(string_split(quarantine_reason, '; ')) AS r "
                           f"FROM quarantine.{table}) GROUP BY r ORDER BY 2 DESC, 1").fetchall()
        total = con.execute(f"SELECT count(*) FROM quarantine.{table}").fetchone()[0]
        if total:
            out.append({"dataset": f"silver.{table}", "rows": int(total),
                        "reasons": [{"rule": r, "rows": int(n)} for r, n in rows]})
    return {"tables": out, "total_rows": sum(t["rows"] for t in out),
            "note": "Aggregated counts only; quarantined rows are never published."}


def lineage_doc(con: duckdb.DuckDBPyConnection) -> dict:
    edges = con.execute("SELECT target_dataset, target_column, source_dataset, source_column FROM meta.lineage "
                        "ORDER BY 1, 2, 3, 4").fetchall()
    nodes = sorted({e[0] for e in edges} | {e[2] for e in edges})

    def kind(n):
        return n.split(":")[0] if ":" in n else n.split(".")[0]

    contracts = contracts_mod.by_name()
    return {"nodes": [{"id": n, "kind": kind(n), "domain": contracts[n].domain if n in contracts else None}
                      for n in nodes],
            "dataset_edges": sorted({(e[2], e[0]) for e in edges}),
            "column_edges": [list(e) for e in edges if not e[0].startswith("exposure:")]}


def maturity_doc() -> dict:
    doc = governance("maturity")
    return {"assessed_on": str(doc["assessed_on"]), "scale": {str(k): v for k, v in doc["scale"].items()},
            "areas": [{**a, "target": min(a["score"] + 1, 5)} for a in doc["areas"]], "roadmap": doc["roadmap"]}


def alerts_doc(con: duckdb.DuckDBPyConnection) -> dict:
    run_id = con.execute("SELECT run_id FROM meta.runs ORDER BY started_at DESC LIMIT 1").fetchone()[0]
    contracts = contracts_mod.by_name()
    alerts = []
    seen = set()
    for dataset, kind, detail in con.execute(
            "SELECT dataset, kind, detail FROM meta.findings WHERE run_id = ? ORDER BY dataset", [run_id]
    ).fetchall():
        col = re.search(r"column '([^']+)'", detail)
        col = col.group(1) if col else None
        if kind == "undeclared_pii":
            if (col, "pii") in seen:
                continue
            seen.add((col, "pii"))
            silver = dataset.replace("bronze.", "silver.")
            rows = con.execute(f'SELECT count("{col}") FROM {silver}').fetchone()[0]
            cat = re.search(r"looks like '([^']+)'", detail)
            alerts.append({"id": f"pii-{col}", "severity": "high", "kind": "undeclared_personal_data",
                           "dataset": silver, "column": col, "category": cat.group(1) if cat else None,
                           "rule": "personal_data_discovery", "rows": int(rows),
                           "domain": contracts[silver].domain, "decides": "data_owner",
                           "raci_activity": "classify_dataset", "also_in": sorted({dataset, silver})})
    for r in con.execute("SELECT dataset, rule, dimension, severity, failed, evaluated FROM meta.quality_results "
                         "WHERE run_id = ? AND failed > 0 ORDER BY failed DESC, dataset, rule", [run_id]).fetchall():
        d, rule, dim, sev, failed, evaluated = r
        alerts.append({"id": f"rule-{d}-{rule}", "severity": "medium" if sev == "error" else "low",
                       "kind": "rows_quarantined" if sev == "error" and d.startswith("silver.") else "rule_warning",
                       "dataset": d, "column": next((x.column for x in contracts[d].rules if x.name == rule), None),
                       "rule": rule, "dimension": dim, "rows": int(failed), "evaluated": int(evaluated),
                       "domain": contracts[d].domain, "decides": "data_steward",
                       "raci_activity": "resolve_quality_incident"})
    order = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda a: (order[a["severity"]], -a["rows"], a["id"]))
    return {"alerts": alerts}


def value_doc(con: duckdb.DuckDBPyConnection) -> dict:
    f = value.facts(con, as_of_date())
    doc = governance("supuestos_valor")
    return {"currency": doc["currency"], "facts": f, "assumptions": doc["assumptions"],
            "result": value.compute(f, value.assumptions()), "illustrative": True,
            "legal_context": "Law No. 29733 (Peru) on personal data protection; no fines are estimated."}


def changes_doc() -> dict:
    path = docs_dir() / "ci_history.yaml"
    return load_yaml(path) if path.exists() else {"events": []}


def meta_doc(con: duckdb.DuckDBPyConnection, q: dict, cat: dict, gl: dict, mat: dict, al: dict) -> dict:
    rules = q["rules"]
    passing = sum(1 for r in rules if r["status"] == "pass")
    terms = gl["terms"]
    contracts = [d for d in cat["datasets"] if d["contract_version"]]
    return {"company": COMPANY, "as_of": str(as_of_date()), "repository":
            "https://github.com/juansanchezalcantara20-ai/data-governance-as-code",
            "health": {"rules_total": len(rules), "rules_passing": passing,
                       "quarantined_rows": sum(d["quarantined"] for d in cat["datasets"]),
                       "contracts_active": len(contracts), "datasets": len(cat["datasets"]),
                       "terms_total": len(terms), "terms_with_owner": sum(1 for t in terms if t["owner_role"]),
                       "maturity_mean": round(sum(a["score"] for a in mat["areas"]) / len(mat["areas"]), 1),
                       "open_alerts": len(al["alerts"])}}


def build(con: duckdb.DuckDBPyConnection | None = None) -> dict[str, dict]:
    own = con is None
    con = con or connect(read_only=True)
    try:
        q, cat, gl, mat, al = quality_doc(con), catalog_doc(con), glossary_doc(), maturity_doc(), alerts_doc(con)
        docs = {
            "meta": meta_doc(con, q, cat, gl, mat, al), "roles": roles_doc(), "access": access_doc(),
            "glossary": gl, "catalog": cat, "contracts": contracts_doc(con), "quality": q,
            "quarantine": quarantine_doc(con), "lineage": lineage_doc(con), "maturity": mat, "alerts": al,
            "value": value_doc(con), "kpi_catalog": kpi_catalog.evaluate(), "changes": changes_doc(),
        }
    finally:
        if own:
            con.close()
    return {k: _clean(v) for k, v in docs.items()}


def serialise(doc: dict) -> str:
    return json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=False) + "\n"


def write(folder: Path | None = None) -> list[Path]:
    folder = folder or out_dir()
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, doc in build().items():
        path = folder / f"{name}.json"
        path.write_text(serialise(doc), encoding="utf-8")
        paths.append(path)
    return paths


def check(folder: Path | None = None) -> list[str]:
    """Names of published JSON files that differ from what the engine produces now."""
    folder = folder or out_dir()
    stale = []
    for name, doc in build().items():
        path = folder / f"{name}.json"
        if not path.exists() or path.read_text(encoding="utf-8") != serialise(doc):
            stale.append(name)
    return stale
