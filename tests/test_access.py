from datetime import date

import pytest

from govkit import access, grants
from govkit.paths import governance
from govkit.validate import access as v


@pytest.fixture
def model():
    return {
        "roles": governance("roles")["roles"],
        "levels": {k: x["rank"] for k, x in governance("classification")["levels"].items()},
        "policy": governance("access_policy"),
        "domains": governance("domains")["domains"],
        "users": governance("users")["users"],
    }


def _user(model, uid):
    return next(u for u in model["users"] if u["id"] == uid)


def _messages(model):
    return " | ".join(f.message for f in v.check_model(**model) if f.level == "error")


def test_repository_access_model_is_valid():
    assert [f for f in v.check() if f.level == "error"] == []


def test_domain_without_owner(model):
    model["domains"]["customer"]["owner"] = None
    assert "domain has no Data Owner" in _messages(model)


def test_owner_without_steward(model):
    model["domains"]["customer"]["stewards"] = []
    assert "has no Data Steward appointed" in _messages(model)


def test_access_not_justified_by_any_role(model):
    _user(model, "robin.notreal")["access"].append({"basis": "role", "domain": "customer", "layers": ["silver"],
                                                     "up_to": "restricted"})
    msg = _messages(model)
    assert "access not justified by any role" in msg and "exceeds the data_consumer baseline" in msg


def test_access_outside_assigned_domain(model):
    _user(model, "robin.notreal")["access"].append({"basis": "role", "domain": "operations", "layers": ["gold"],
                                                     "up_to": "internal"})
    assert "outside the role scope" in _messages(model)


def _request(**overrides):
    base = {"basis": "request", "domain": "customer", "layers": ["gold"], "up_to": "confidential", "ticket": "AR-9",
            "reason": "test", "requested_by": "robin.notreal", "approved_by": "taylor.dummond",
            "approved_on": "2026-10-01", "expires_on": "2026-10-31"}
    return {**base, **overrides}


def test_valid_request_passes(model):
    _user(model, "robin.notreal")["access"].append(_request())
    assert _messages(model) == ""


def test_segregation_of_duties_requester_cannot_approve(model):
    owner = _user(model, "taylor.dummond")
    owner["access"].append(_request(requested_by="taylor.dummond", approved_by="taylor.dummond", layers=["silver"]))
    assert "approved their own request" in _messages(model)


def test_approver_must_govern_the_domain(model):
    _user(model, "robin.notreal")["access"].append(_request(approved_by="riley.placeholder"))
    assert "does not govern domain 'customer'" in _messages(model)


def test_steward_cannot_approve_confidential(model):
    _user(model, "robin.notreal")["access"].append(_request(approved_by="alex.exampleton"))
    assert "cannot approve 'confidential' access" in _messages(model)


def test_restricted_never_through_request(model):
    _user(model, "robin.notreal")["access"].append(_request(up_to="restricted"))
    assert "can never be granted through a request" in _messages(model)


def test_exceptions_must_expire(model):
    _user(model, "robin.notreal")["access"].append(_request(expires_on="2027-06-01"))
    assert "must be 1-90" in _messages(model)


def test_domain_scoped_role_cannot_have_all_domains(model):
    _user(model, "robin.notreal")["domains"] = ["*"]
    assert "breaks least privilege" in _messages(model)


def test_effective_access_honours_expiry():
    ds = {"name": "gold.x", "layer": "gold", "domain": "operations", "classification": "confidential"}
    assert access.can_read("jamie.fakeley", ds, on=date(2026, 11, 15))
    assert not access.can_read("jamie.fakeley", ds, on=date(2027, 1, 15))
    assert not access.can_read("robin.notreal", ds, on=date(2026, 11, 15))


def test_grants_never_exceed_policy():
    lv = access.levels()
    by_name = {d["name"]: d for d in access.datasets()}
    pol = access.policy()["baseline"]
    for g in grants.compile_grants():
        if g.kind != "group":
            continue
        role = next(r for r in pol if g.principal.endswith(r))
        ds = by_name[g.dataset]
        assert ds["layer"] in pol[role]["layers"]
        assert lv[ds["classification"]] <= lv[pol[role]["up_to"]]


def test_model_fixture_is_not_shared(model):
    model["domains"]["customer"]["owner"] = None
    assert governance("domains")["domains"]["customer"]["owner"] == "taylor.dummond"
