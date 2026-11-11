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


def _ds(name):
    return next(d for d in access.datasets() if d["name"] == name)


def test_field_technician_sees_orders_but_not_money():
    ds = _ds("silver.service_orders")
    view = access.column_view("rowan.pretendez", ds, ds["columns"])
    assert view["status"] == "visible" and view["opened_on"] == "visible"
    assert {view[c] for c in ("price", "planned_labor_cost", "planned_material_cost")} == {"hidden"}
    assert access.max_level("rowan.pretendez", _ds("gold.service_order_economics")) is None


def test_auditor_reads_everything_masked_and_cannot_act():
    ds = _ds("silver.technicians")
    view = access.column_view("ellis.checkwell", ds, ds["columns"])
    assert view["national_id"] == "masked" and view["trade"] == "visible"
    assert not access.can_act_on_quarantine("ellis.checkwell")
    assert access.can_act_on_quarantine("riley.placeholder")


def test_owner_sees_personal_data_only_in_own_domain():
    ops, cus = _ds("silver.technicians"), _ds("silver.customers")
    assert access.column_view("riley.placeholder", ops, ["email"])["email"] == "visible"
    assert access.column_view("riley.placeholder", cus, ["contact_email"])["contact_email"] == "hidden"


def test_column_grants_exclude_higher_classified_columns():
    g = next(x for x in grants.compile_grants()
             if x.dataset == "silver.service_orders" and x.principal == "gov_operations_field_technician")
    assert g.columns and "price" not in g.columns and "status" in g.columns


def test_read_only_role_cannot_be_given_quarantine_actions(model):
    model["policy"]["quarantine_actions"].append("auditor")
    assert "read_only and cannot act" in _messages(model)
