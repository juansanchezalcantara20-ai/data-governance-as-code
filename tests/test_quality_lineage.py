"""Phase 5: quality in six dimensions, per-run report, generated end-to-end lineage."""

import json

from govkit import lineage, report
from govkit.contracts import DIMENSIONS


def test_rules_cover_all_six_dimensions(con):
    dims = {r[0] for r in con.execute("SELECT DISTINCT dimension FROM meta.quality_results").fetchall()}
    assert dims == set(DIMENSIONS)


def test_accuracy_rule_catches_decimal_shift_costs(con):
    failed = con.execute("SELECT failed FROM meta.quality_results WHERE rule = 'issue_cost_matches_master' "
                         "ORDER BY run_id DESC LIMIT 1").fetchone()[0]
    assert failed >= 4


def test_timeliness_is_measured_against_the_as_of_date(con):
    status = con.execute("SELECT status FROM meta.quality_results WHERE rule = 'freshness_sla' "
                         "AND dataset = 'silver.service_orders' ORDER BY run_id DESC LIMIT 1").fetchone()[0]
    assert status == "pass"


def test_every_run_writes_a_quality_report(project):
    folder = project["root"] / "reports"
    md = (folder / "quality_report.md").read_text()
    data = json.loads((folder / "quality_report.json").read_text())
    assert "## By dataset and dimension" in md and "illustrate the method" in md
    assert set(data["by_dimension"]) == set(DIMENSIONS)
    assert "silver.material_issues" in data["quarantine"]


def test_glossary_rules_are_traced_in_the_report(con):
    coverage = {g["term"]: g for g in report.data(con)["glossary_coverage"]}
    assert coverage["Material issue"]["rules"] == 4
    assert coverage["Gross margin"]["pass_rate"] == 100.0


def test_lineage_runs_from_source_file_to_consumer(con):
    consumers = {d["dataset"] for d in lineage.downstream(con, "file:labor_entries.csv")}
    assert "exposure:Service profitability dashboard" in consumers
    assert "exposure:Key-account review" in consumers


def test_mermaid_diagram_is_generated_from_code(con):
    diagram = lineage.mermaid(con)
    assert diagram.startswith("flowchart LR")
    assert "n_gold_service_order_economics --> n_exposure_Service_profitability_dashboard" in diagram
