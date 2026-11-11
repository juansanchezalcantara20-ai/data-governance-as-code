"""Data contracts: static validation, data-vs-contract verification and the change policy."""

import copy

import pytest

from govkit import cli, compat, generator, pipeline
from govkit import contracts as contracts_mod
from govkit.db import connect
from govkit.validate import contracts as v
from tests.conftest import make_project


def test_every_model_has_a_valid_contract():
    assert [f for f in v.check() if f.level == "error"] == []


def test_every_contract_declares_the_required_parts():
    for c in contracts_mod.load_all():
        assert c.owner and c.steward and c.primary_key and c.change_policy["breaking"]
        assert c.classification in ("public", "internal", "confidential", "restricted")
        assert any(s["property"] in ("latency", "frequency") for s in c.raw["slaProperties"])


def test_real_data_honours_every_contract(project):
    report = project["report"]
    assert report.status in ("passed", "warning")
    assert not [f for f in report.findings if f[1] == "contract_violation" and f[2] == "error"]
    assert not [r for r in report.results if r.dataset.startswith("gold.") and r.status == "fail"]


def test_quarantine_holds_rows_that_break_silver_contracts(con):
    reasons = " ".join(con.execute("SELECT quarantine_reason FROM quarantine.material_issues").fetchdf().quarantine_reason)
    assert "issue_cost_matches_master" in reasons     # accuracy: decimal-shift costs
    assert "issue_order_exists" in reasons             # consistency: orphan lines
    bad = con.execute("SELECT count(*) FROM silver.material_issues WHERE unit_cost <= 0").fetchone()[0]
    assert bad == 0


@pytest.fixture
def broken_project(tmp_path, monkeypatch):
    """A copy of the project where a developer renames a gold column in SQL but not in the contract."""
    root = make_project(tmp_path)
    sql = root / "models" / "gold.service_order_economics.sql"
    sql.write_text(sql.read_text().replace("AS gross_margin,", "AS margin_amount,"))
    monkeypatch.setenv("GOVKIT_HOME", str(root))
    generator.generate()
    return root


def test_breaking_schema_change_fails_the_build(broken_project):
    con = connect()
    report = pipeline.run(con=con, log=lambda *_: None)
    con.close()
    details = [f[3] for f in report.findings if f[1] == "contract_violation"]
    assert report.status == "failed"
    assert any("'gross_margin' is declared in contract v2.0.0 but missing" in d for d in details)
    assert any("'margin_amount' exists in the data but is not declared" in d for d in details)
    assert cli.main(["verify"]) == 1


def _contract(name="gold.service_order_economics"):
    return contracts_mod.by_name()[name]


def test_removing_a_column_without_major_bump_violates_policy():
    old = _contract()
    new = copy.deepcopy(old)
    new.properties = [p for p in new.properties if p.name != "gross_margin"]
    new.version = "2.1.0"
    problems = compat.check_pair(old, new)
    assert problems and "column 'gross_margin' removed or renamed" in problems[0]


def test_breaking_change_with_major_bump_is_allowed():
    old = _contract()
    new = copy.deepcopy(old)
    new.properties = [p for p in new.properties if p.name != "gross_margin"]
    new.version = "3.0.0"
    assert compat.check_pair(old, new) == []


def test_adding_an_optional_column_is_not_breaking():
    old = _contract()
    new = copy.deepcopy(old)
    extra = copy.deepcopy(new.properties[-1])
    extra.name, extra.required = "notes", False
    new.properties.append(extra)
    assert compat.check_pair(old, new) == []
    assert not any(c.breaking for c in compat.diff(old, new))


def test_raising_classification_and_type_change_are_breaking():
    old = _contract("silver.materials")
    new = copy.deepcopy(old)
    new.classification = "confidential"
    new.column("stock_on_hand").logical_type = "number"
    details = " ".join(c.detail for c in compat.diff(old, new) if c.breaking)
    assert "classification raised" in details and "type integer -> number" in details


def test_static_validator_rejects_personal_data_in_internal_contract():
    c = copy.deepcopy(_contract("gold.customer_value"))
    c.classification = "internal"
    findings = v.check_contract(c, users={"taylor.dummond": {}, "alex.exampleton": {}},
                                domains={"customer": {"owner": "taylor.dummond", "stewards": ["alex.exampleton"]}},
                                levels={"public": 0, "internal": 1, "confidential": 2, "restricted": 3},
                                terms={p.business_name for p in c.properties if p.business_name},
                                datasets={"gold.service_order_economics"})
    assert any("has personal data" in f.message for f in findings)


def test_raising_a_column_classification_is_breaking():
    old = _contract("silver.service_orders")
    new = copy.deepcopy(old)
    new.column("status").classification = "confidential"
    assert any("column 'status' classification raised" in c.detail for c in compat.diff(old, new) if c.breaking)
