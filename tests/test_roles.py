from govkit.paths import governance
from govkit.validate import roles as v


def _roles():
    return governance("roles")["roles"]


def test_repository_roles_and_raci_are_valid():
    assert v.check() == []


def test_raci_requires_exactly_one_accountable():
    acts = [{"id": "x", "raci": {"data_owner": "A", "data_steward": "A", "data_custodian": "R"}}]
    assert any("exactly one Accountable" in f.message for f in v.check_raci(acts, _roles()))


def test_raci_requires_a_responsible():
    acts = [{"id": "x", "raci": {"data_owner": "A", "data_steward": "C"}}]
    assert any("at least one Responsible" in f.message for f in v.check_raci(acts, _roles()))


def test_raci_rejects_unknown_roles_and_letters():
    acts = [{"id": "x", "raci": {"data_owner": "A", "data_wizard": "R", "data_steward": "Z"}}]
    messages = " ".join(f.message for f in v.check_raci(acts, _roles()))
    assert "unknown role 'data_wizard'" in messages and "invalid letter 'Z'" in messages


def test_escalation_cycle_is_detected():
    roles = _roles()
    roles["data_sponsor"]["escalates_to"] = "data_owner"
    assert any("cycle" in f.message for f in v.check_roles(roles))
