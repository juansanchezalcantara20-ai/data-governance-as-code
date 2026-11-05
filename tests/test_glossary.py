import copy

import pytest

from govkit.lineage import model_columns
from govkit.paths import governance
from govkit.validate import glossary as v


@pytest.fixture
def ctx():
    return {
        "terms": governance("glossary")["terms"],
        "users": {u["id"]: u for u in governance("users")["users"]},
        "domains": governance("domains")["domains"],
        "models": model_columns(),
        "contracts": {},
    }


def _errors(ctx):
    return " | ".join(f.message for f in v.check_terms(**ctx) if f.level == "error")


def _term(ctx, tid):
    return next(t for t in ctx["terms"] if t["id"] == tid)


def test_glossary_has_25_to_40_terms(ctx):
    assert 25 <= len(ctx["terms"]) <= 40


def test_repository_glossary_has_no_errors(ctx):
    assert _errors(ctx) == ""


def test_owner_and_steward_must_exist(ctx):
    _term(ctx, "asset")["owner"] = "nobody.here"
    assert "owner 'nobody.here' does not exist" in _errors(ctx)


def test_metric_needs_formula_and_source(ctx):
    t = _term(ctx, "gross_margin")
    t.pop("formula")
    t.pop("source")
    msg = _errors(ctx)
    assert "metric without a formula" in msg and "metric without a source" in msg


def test_self_referencing_definition_is_circular(ctx):
    _term(ctx, "revenue")["definition"] = "Revenue is the total revenue of the period."
    assert "uses the term itself" in _errors(ctx)


def test_dependency_cycle_is_circular(ctx):
    _term(ctx, "actual_cost")["depends_on"] = ["gross_margin"]
    assert "circular definition: " in _errors(ctx)


def test_orphan_term_is_rejected(ctx):
    ctx["terms"].append({"id": "lonely", "name": "Lonely term", "domain": "operations", "type": "concept",
                         "definition": "Nobody uses this.", "owner": "riley.placeholder",
                         "steward": "sam.samplewood", "status": "draft", "next_review": "2027-01-01"})
    assert "orphan term" in _errors(ctx)


def test_source_column_must_exist_in_a_model(ctx):
    _term(ctx, "asset")["source"] = {"table": "silver.assets", "column": "asset_code"}
    assert "source column 'asset_code' not in silver.assets" in _errors(ctx)


def test_term_used_by_contract_is_not_orphan(ctx):
    class P:
        business_name = "Lonely term"

    class C:
        properties = [P()]
        rules = []
        name = "x"

    ctx["terms"].append({"id": "lonely", "name": "Lonely term", "domain": "operations", "type": "concept",
                         "definition": "Used through a contract only.", "owner": "riley.placeholder",
                         "steward": "sam.samplewood", "status": "draft", "next_review": "2027-01-01"})
    ctx["contracts"] = {"x": C()}
    assert "orphan" not in _errors(copy.copy(ctx))
