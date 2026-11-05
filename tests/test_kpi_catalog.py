from govkit import kpi_catalog


def test_project_2_catalog_is_evaluated_offline():
    r = kpi_catalog.evaluate()
    assert r["kpis"] == 28
    by = {c["check"]: c for c in r["checks"]}
    assert by["owner"]["failed"] == 0 and by["definition"]["failed"] == 0
    assert by["steward"]["failed"] == 28          # the catalog format has no steward field: a real gap
    assert set(by["input_declared"]["failed_kpis"]) == {"dq_completeness", "dq_uniqueness", "dq_validity",
                                                         "dq_timeliness"}
    assert 0 < r["pass_rate"] < 100


def test_checks_detect_a_broken_kpi(tmp_path):
    import yaml

    doc = {"cases": {"svc": {"tables": ["tickets"]}},
           "kpis": [{"id": "x", "name": "Backlog", "case": "svc", "definition": "The backlog of tickets.",
                     "formula": "count", "unit": "tickets", "owner": "", "related": ["missing"],
                     "input": {"table": "orders", "columns": []}, "direction": "lower_is_better",
                     "thresholds": {"green": 10, "amber": 5}}]}
    path = tmp_path / "c.yaml"
    path.write_text(yaml.safe_dump(doc))
    failed = {c["check"] for c in kpi_catalog.evaluate(path)["checks"] if c["failed"]}
    assert {"not_circular", "related_exist", "owner", "input_declared", "reference_sql", "thresholds"} <= failed
