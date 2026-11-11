"""The demo app can only show what the engine produced (honesty lock) and never raw personal data."""

import json
import re

import pytest

from govkit import access, export_app
from tests.conftest import ROOT

DATA = ROOT / "app" / "data"
SCREENS = ["meta", "roles", "access", "glossary", "catalog", "contracts", "quality", "quarantine", "lineage",
           "maturity", "alerts", "value", "kpi_catalog", "changes"]


@pytest.fixture(scope="module")
def built(project):
    return export_app.build(project["con"])


def _published(name):
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def test_published_json_matches_engine_output(built):
    for name in SCREENS:
        assert _published(name) == json.loads(export_app.serialise(built[name])), f"{name}.json is stale"


def test_every_screen_has_data(built):
    assert built["glossary"]["terms"] and built["catalog"]["datasets"] and built["contracts"]["contracts"]
    assert built["quality"]["rules"] and built["quarantine"]["tables"] and built["lineage"]["dataset_edges"]
    assert built["maturity"]["areas"] and built["alerts"]["alerts"] and built["roles"]["raci"]
    assert built["access"]["personas"] and built["changes"]["events"] and built["kpi_catalog"]["checks"]
    assert built["value"]["result"]["total_pen"] > 0
    assert built["meta"]["health"]["rules_total"] == len(built["quality"]["rules"])


def test_role_views_follow_the_access_policy(built):
    datasets = {d["name"]: d for d in access.datasets()}
    for persona in built["access"]["personas"]:
        for name, view in persona["datasets"].items():
            assert view["level"] == access.max_level(persona["user"], datasets[name])
            cols = datasets[name].get("columns", [])
            assert view["columns"] == (access.column_view(persona["user"], datasets[name], cols) if cols else {})
    tech = next(p for p in built["access"]["personas"] if p["role"] == "field_technician")
    assert tech["datasets"]["silver.service_orders"]["columns"]["price"] == "hidden"
    assert tech["datasets"]["gold.service_order_economics"]["level"] is None
    auditor = next(p for p in built["access"]["personas"] if p["role"] == "auditor")
    assert auditor["read_only"] and not auditor["can_act_on_quarantine"]


EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}")
PHONE = re.compile(r"\b9\d{8}\b")
NATIONAL_ID = re.compile(r"\b\d{8}\b")


def test_no_unmasked_personal_data_is_published():
    for path in DATA.glob("*.json"):
        text = path.read_text(encoding="utf-8")
        leaks = [m for m in EMAIL.findall(text) if "*" not in m]
        assert leaks == [], f"{path.name}: {leaks[:3]}"
        assert PHONE.findall(text) == [], path.name
        assert NATIONAL_ID.findall(text) == [], path.name
    catalog = _published("catalog")
    for d in catalog["datasets"]:
        sensitive = {c["name"] for c in d["columns"] if c["personal_data"] or c["undeclared_personal_data"]}
        for row in d["sample"]:
            for col in sensitive & row.keys():
                assert row[col] is None or "*" in str(row[col]) or "." in str(row[col]) or "[" in str(row[col])
