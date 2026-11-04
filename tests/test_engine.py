from __future__ import annotations

import hashlib

import pytest

from govkit import generator, lineage, privacy, quality
from govkit.contracts import Rule


def _digest(folder):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.glob("*"))}


def test_generator_is_deterministic(tmp_path):
    generator.generate(out=tmp_path / "a")
    generator.generate(out=tmp_path / "b")
    assert _digest(tmp_path / "a") == _digest(tmp_path / "b")


def test_pipeline_builds_every_model(project):
    report = project["report"]
    assert report.errors == []
    assert report.datasets == 18


def test_lineage_traces_gold_metric_back_to_source_file(con):
    sources = {n["dataset"] for n in lineage.upstream(con, "gold.site_monthly_kpis", "gross_margin_pct")}
    assert "silver.technicians" in sources
    assert "file:labor_entries.csv" in sources


def test_impact_analysis_reaches_consumers(con):
    impacted = {n["dataset"] for n in lineage.downstream(con, "silver.technicians", "hourly_cost")}
    assert "gold.service_order_economics" in impacted
    assert "exposure:Service profitability dashboard" in impacted
    assert not any(d.startswith("gold.inventory") for d in impacted)


def test_referenced_tables_ignores_ctes():
    sql = "WITH x AS (SELECT * FROM silver.a) SELECT * FROM x JOIN silver.b USING (id)"
    assert lineage.referenced_tables(sql) == {"silver.a", "silver.b"}


def test_row_predicates(con):
    con.execute("CREATE OR REPLACE TEMP TABLE t AS SELECT * FROM (VALUES (1, 'a@b.org'), (NULL, 'x'), (5, NULL)) v(n, c)")
    cases = [
        (Rule("r", "notNull", "n", {}, "completeness", "error"), 1),
        (Rule("r", "range", "n", {"min": 2}, "validity", "error"), 1),
        (Rule("r", "pattern", "c", {"pattern": r"^[^@]+@[^@]+\.org$"}, "validity", "error"), 1),
        (Rule("r", "validValues", "n", {"values": [1, 5]}, "validity", "error"), 0),
    ]
    for rule, expected in cases:
        failed = con.execute(f"SELECT count(*) FROM t AS src WHERE NOT COALESCE({quality.row_predicate(rule)}, TRUE)"
                             ).fetchone()[0]
        assert failed == expected, rule


@pytest.mark.parametrize("value,category,expected", [
    ("45781236", "national_id", "****1236"),
    ("a.fictus12@example.org", "email", "a***@example.org"),
    ("Avery Fictus", "name", "A. F."),
    ("987654321", "phone", "*****4321"),
    (38.5, "compensation", "[redacted]"),
])
def test_masking(value, category, expected):
    assert privacy.mask_value(value, category) == expected


def test_pii_discovery_by_name_and_by_value():
    assert privacy.detect_column("contact_email", []) == "email"
    assert privacy.detect_column("notes", ["x@example.org"] * 10) == "email"
    assert privacy.detect_column("description", ["Oil filter"] * 10) is None
