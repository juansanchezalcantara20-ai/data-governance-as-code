from govkit import contracts as contracts_mod
from govkit import grants, unity


def test_every_contract_becomes_a_table_with_its_keys():
    sql = unity.tables_sql()
    for c in contracts_mod.load_all():
        assert f"CREATE TABLE IF NOT EXISTS governance_demo.{c.name} (" in sql
        assert f"PRIMARY KEY ({', '.join(c.primary_key)})" in sql


def test_every_file_is_labelled_not_executed():
    for fn in unity.FILES.values():
        assert fn().startswith("-- NOT EXECUTED IN THIS REPO")


def test_grants_are_derived_from_policy_not_typed():
    sql = unity.grants_sql()
    governed = {c.name for c in contracts_mod.load_all()}
    expected = [g for g in grants.compile_grants() if g.dataset in governed]
    assert sql.count("GRANT SELECT ON TABLE") == len(expected)
    assert "governance_demo.silver.technicians TO `gov_operations_data_consumer`" not in sql


def test_every_personal_data_column_gets_a_mask_and_a_tag():
    masks, tags = unity.masks_sql(), unity.tags_sql()
    for c in contracts_mod.load_all():
        for column, category in c.pii_columns.items():
            assert f"ALTER TABLE governance_demo.{c.name} ALTER COLUMN {column} SET MASK" in masks
            assert f"'pii' = '{category}'" in tags
