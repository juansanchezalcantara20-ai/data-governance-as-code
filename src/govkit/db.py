"""DuckDB lakehouse connection and the governance metadata schema.

Schemas in ``data/lakehouse.duckdb``:

* ``bronze``, ``silver``, ``gold``: Medallion layers.
* ``quarantine``: silver rows rejected by blocking (``severity: error``) rules, with the reason.
* ``meta``: the governance metadata store (datasets, columns, lineage, quality results,
  findings, runs, access requests, temporary grants and the audit log).
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from .paths import db_path

SCHEMAS = ("bronze", "silver", "gold", "quarantine", "meta")

DDL = """
CREATE TABLE IF NOT EXISTS meta.runs (
    run_id VARCHAR PRIMARY KEY, started_at TIMESTAMP, finished_at TIMESTAMP, as_of DATE, status VARCHAR,
    datasets INTEGER, quarantined_rows BIGINT, errors VARCHAR);
CREATE TABLE IF NOT EXISTS meta.datasets (
    dataset VARCHAR PRIMARY KEY, layer VARCHAR, domain VARCHAR, classification VARCHAR, owner VARCHAR,
    steward VARCHAR, contract_version VARCHAR, description VARCHAR, has_pii BOOLEAN, row_count BIGINT,
    quarantined_rows BIGINT, quality_score DOUBLE, built_at TIMESTAMP);
CREATE TABLE IF NOT EXISTS meta.columns (
    dataset VARCHAR, column_name VARCHAR, position INTEGER, contract_type VARCHAR, actual_type VARCHAR,
    required BOOLEAN, is_unique BOOLEAN, primary_key BOOLEAN, description VARCHAR, business_term VARCHAR,
    pii_declared VARCHAR, pii_detected VARCHAR);
CREATE TABLE IF NOT EXISTS meta.lineage (
    target_dataset VARCHAR, target_column VARCHAR, source_dataset VARCHAR, source_column VARCHAR);
CREATE TABLE IF NOT EXISTS meta.quality_results (
    run_id VARCHAR, dataset VARCHAR, rule VARCHAR, kind VARCHAR, column_name VARCHAR, dimension VARCHAR,
    severity VARCHAR, origin VARCHAR, evaluated BIGINT, failed BIGINT, pass_rate DOUBLE, status VARCHAR,
    description VARCHAR);
CREATE TABLE IF NOT EXISTS meta.findings (
    run_id VARCHAR, dataset VARCHAR, kind VARCHAR, severity VARCHAR, detail VARCHAR);
CREATE SEQUENCE IF NOT EXISTS meta.request_seq START 1;
CREATE TABLE IF NOT EXISTS meta.access_requests (
    id INTEGER PRIMARY KEY DEFAULT nextval('meta.request_seq'), requested_at TIMESTAMP, requester VARCHAR,
    domain VARCHAR, classification VARCHAR, reason VARCHAR, status VARCHAR, approver VARCHAR,
    decided_at TIMESTAMP, comment VARCHAR, expires_at TIMESTAMP);
CREATE TABLE IF NOT EXISTS meta.audit_log (
    logged_at TIMESTAMP, actor VARCHAR, action VARCHAR, object_name VARCHAR, detail VARCHAR);
"""


def connect(path: Path | str | None = None, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    path = Path(path or db_path())
    # One thread: parallel aggregation sums floats in a varying order, which can move a rounded cent between runs.
    # Single-threaded execution keeps every published number byte-for-byte reproducible.
    if read_only:
        return duckdb.connect(str(path), read_only=True, config={"threads": 1})
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path), config={"threads": 1})
    for schema in SCHEMAS:
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    con.execute(DDL)
    return con


def audit(con: duckdb.DuckDBPyConnection, actor: str, action: str, obj: str, detail: str = "") -> None:
    con.execute("INSERT INTO meta.audit_log VALUES (now(), ?, ?, ?, ?)", [actor, action, obj, detail])


def table_columns(con: duckdb.DuckDBPyConnection, name: str) -> dict[str, str]:
    schema, _, table = name.partition(".")
    rows = con.execute(
        "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = ? AND table_name = ? "
        "ORDER BY ordinal_position", [schema, table]).fetchall()
    return dict(rows)
