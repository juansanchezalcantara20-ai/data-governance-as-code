from govkit import value
from govkit.generator import as_of_date
from govkit.paths import governance
from govkit.validate import value as v


def test_assumptions_are_valid_and_marked():
    assert v.check() == []
    from tests.conftest import ROOT

    assert "ILLUSTRATIVE" in (ROOT / "governance" / "supuestos_valor.yaml").read_text(encoding="utf-8")


def test_out_of_range_assumption_is_rejected():
    doc = governance("supuestos_valor")
    doc["assumptions"]["analyst_hour_cost"]["value"] = 999
    assert any("outside" in f.message for f in v.check_assumptions(doc))


def test_facts_come_from_the_pipeline(con):
    f = value.facts(con, as_of_date())
    assert f["quarantined_rows"] == sum(f["quarantined_by_dataset"].values()) > 0
    assert f["undeclared_pii_columns"] == ["approver_email"]
    assert f["governed_metrics"] == sum(1 for t in governance("glossary")["terms"]
                                        if t["type"] == "metric" and t["status"] == "approved")


def test_value_is_proportional_to_what_was_caught(con):
    f = value.facts(con, as_of_date())
    base = value.compute(f, value.assumptions())
    doubled = value.compute({**f, "quarantined_rows": f["quarantined_rows"] * 2}, value.assumptions())
    assert abs(doubled["parts"]["rework"]["hours"] - base["parts"]["rework"]["hours"] * 2) < 0.02
    nothing = value.compute({**f, "quarantined_rows": 0, "undeclared_pii_columns": [], "governed_metrics": 0},
                            value.assumptions())
    assert nothing["total_pen"] == 0
