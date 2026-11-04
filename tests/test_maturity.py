import pytest

from govkit.paths import governance
from govkit.validate import maturity as v
from tests.conftest import ROOT


@pytest.fixture(autouse=True)
def repo_root(monkeypatch):
    """Evidence paths point at the real repository, not the temp project copy."""
    monkeypatch.setenv("GOVKIT_HOME", str(ROOT))


def test_assessment_covers_the_11_areas_with_existing_evidence():
    doc = governance("maturity")
    assert len(doc["areas"]) == 11
    assert v.check() == []


def test_missing_evidence_is_rejected():
    doc = governance("maturity")
    doc["areas"][0]["evidence"].append("docs/does_not_exist.md")
    assert any("does not exist" in f.message for f in v.check_assessment(doc))


def test_high_scores_need_more_evidence():
    doc = governance("maturity")
    area = next(a for a in doc["areas"] if a["id"] == "data_architecture")
    area["score"] = 4
    assert any("at least three pieces of evidence" in f.message for f in v.check_assessment(doc))


def test_every_area_must_be_assessed():
    doc = governance("maturity")
    doc["areas"] = [a for a in doc["areas"] if a["id"] != "metadata"]
    assert any(f.subject == "metadata" for f in v.check_assessment(doc))
