"""Personal data discovery and masking.

Discovery inspects column names and a sample of values (emails, phone numbers) and
compares what it finds with the ``pii:<category>`` tags declared in contracts. Personal
data that is present but not declared escapes masking, so it is reported as a
high-severity finding.
"""

from __future__ import annotations

import hashlib
import re

import duckdb
import pandas as pd

PII_CATEGORIES = ("national_id", "name", "email", "phone", "address", "compensation")

BY_NAME = [
    ("national_id", re.compile(r"(^|_)(national_id|dni|ssn|tax_id|passport)($|_)")),
    ("email", re.compile(r"(^|_)(e?mail|email_address)($|_)")),
    ("phone", re.compile(r"(^|_)(phone|mobile|cell)($|_)")),
    ("name", re.compile(r"(^|_)(first_name|last_name|full_name|contact_name|person_name)($|_)")),
    ("address", re.compile(r"(^|_)(address|street)($|_)")),
    ("compensation", re.compile(r"(^|_)(salary|wage|hourly_cost|compensation)($|_)")),
]
BY_VALUE = [
    ("email", re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.I), 0.6),
    ("phone", re.compile(r"^9\d{8}$"), 0.8),
]


def detect_column(name: str, sample: list) -> str | None:
    lowered = name.lower()
    for category, pattern in BY_NAME:
        if pattern.search(lowered):
            return category
    values = [str(v).strip() for v in sample if v is not None and str(v).strip()]
    if len(values) >= 5:
        for category, pattern, threshold in BY_VALUE:
            if sum(bool(pattern.match(v)) for v in values) / len(values) >= threshold:
                return category
    return None


def detect_table(con: duckdb.DuckDBPyConnection, table: str, sample: int = 200) -> dict[str, str]:
    df = con.execute(f"SELECT * FROM {table} USING SAMPLE {sample} ROWS (reservoir, 7)").fetchdf()
    found = {}
    for column in df.columns:
        if column.startswith("_"):
            continue
        category = detect_column(column, df[column].tolist())
        if category:
            found[column] = category
    return found


def mask_value(value, category: str):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return value
    text = str(value)
    if category in ("national_id", "phone"):
        return "*" * max(len(text) - 4, 4) + text[-4:]
    if category == "email":
        user, _, domain = text.partition("@")
        return f"{user[:1]}***@{domain}" if domain else "***"
    if category == "name":
        return " ".join(part[:1] + "." for part in text.split())
    if category == "compensation":
        return "[redacted]"
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()[:10]


def mask_frame(df: pd.DataFrame, pii_columns: dict[str, str]) -> pd.DataFrame:
    df = df.copy()
    for column, category in pii_columns.items():
        if column in df.columns:
            df[column] = df[column].astype(object).map(lambda v, c=category: mask_value(v, c))
    return df
