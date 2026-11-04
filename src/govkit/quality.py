"""Executable data quality rules.

Every contract rule compiles to SQL:

* **Row-level rules** become a boolean predicate per row. On silver, rows failing an
  ``error`` rule are moved to ``quarantine.<table>`` with the failing rule names;
  ``warning`` rules are only measured.
* **Table-level rules** (``rowCount``, ``freshness``, ``sql``) are evaluated once per run.

Dimensions follow DAMA-DMBOK2: completeness, uniqueness, validity, consistency,
accuracy and timeliness. Freshness is measured against the dataset's as-of date
(taken from the source manifest) so results are reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import duckdb

from .contracts import Contract, Rule


def ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def literal(value) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return repr(value)
    return "'" + str(value).replace("'", "''") + "'"


def row_predicate(rule: Rule) -> str:
    """SQL expression that is TRUE when a row satisfies ``rule``. NULLs pass unless notNull."""
    c = ident(rule.column) if rule.column else None
    a = rule.args
    if rule.kind == "notNull":
        return f"({c} IS NOT NULL AND trim(CAST({c} AS VARCHAR)) <> '')"
    if rule.kind == "unique":
        return f"({c} IS NULL OR count(*) OVER (PARTITION BY {c}) = 1)"
    if rule.kind == "pattern":
        return f"({c} IS NULL OR regexp_full_match(CAST({c} AS VARCHAR), {literal(a['pattern'])}))"
    if rule.kind == "validValues":
        return f"({c} IS NULL OR {c} IN ({', '.join(literal(v) for v in a['values'])}))"
    if rule.kind == "range":
        parts = []
        if "min" in a:
            parts.append(f"{c} >= {literal(a['min'])}")
        if "max" in a:
            parts.append(f"{c} <= {literal(a['max'])}")
        return f"({c} IS NULL OR ({' AND '.join(parts) or 'TRUE'}))"
    if rule.kind == "references":
        return f"({c} IS NULL OR {c} IN (SELECT {ident(a['column'])} FROM {a['table']}))"
    if rule.kind == "expression":
        return f"COALESCE(({a['sql']}), TRUE)"
    if rule.kind == "tolerance":
        ref = (f"(SELECT r.{ident(a['referenceColumn'])} FROM {a['referenceTable']} r "
               f"WHERE r.{ident(a['referenceKey'])} = src.{ident(a['key'])})")
        return f"({c} IS NULL OR {ref} IS NULL OR abs({c} - {ref}) <= {float(a['maxDeviationPct']) / 100} * abs({ref}))"
    raise ValueError(f"{rule.kind} is not a row-level rule")


_COMPARATORS = {
    "mustBe": lambda v, t: v == t,
    "mustNotBe": lambda v, t: v != t,
    "mustBeLessThan": lambda v, t: v < t,
    "mustBeLessOrEqualTo": lambda v, t: v <= t,
    "mustBeGreaterThan": lambda v, t: v > t,
    "mustBeGreaterOrEqualTo": lambda v, t: v >= t,
    "mustBeBetween": lambda v, t: t[0] <= v <= t[1],
}


def table_check(con: duckdb.DuckDBPyConnection, rule: Rule, table: str, as_of: date) -> tuple[bool, object]:
    """Evaluate a table-level rule. Returns (passed, observed value)."""
    a = rule.args
    if rule.kind == "rowCount":
        n = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        return n >= int(a.get("min", 1)) and n <= int(a.get("max", 10**12)), n
    if rule.kind == "freshness":
        age = con.execute(f"SELECT date_diff('day', CAST(max({ident(a['column'])}) AS DATE), "
                          f"DATE '{as_of.isoformat()}') FROM {table}").fetchone()[0]
        return age is not None and age <= float(a["maxAgeDays"]), age
    if rule.kind == "sql":
        value = con.execute(a["query"].replace("{object}", table)).fetchone()[0]
        value = 0 if value is None else value
        checks = [(k, v) for k, v in a.items() if k in _COMPARATORS]
        if not checks:
            raise ValueError(f"Rule {rule.name}: sql rule needs a mustBe* comparator")
        return all(_COMPARATORS[k](value, v) for k, v in checks), value
    raise ValueError(f"{rule.kind} is not a table-level rule")


@dataclass
class Result:
    dataset: str
    rule: Rule
    evaluated: int
    failed: int
    observed: object = None

    @property
    def pass_rate(self) -> float:
        return 100.0 if self.evaluated == 0 else round(100.0 * (self.evaluated - self.failed) / self.evaluated, 2)

    @property
    def status(self) -> str:
        if self.failed == 0:
            return "pass"
        return "fail" if self.rule.severity == "error" else "warn"


def evaluate(con: duckdb.DuckDBPyConnection, contract: Contract, source: str, as_of: date,
             quarantine: bool = False) -> tuple[list[Result], int]:
    """Evaluate ``contract`` rules on ``source``.

    With ``quarantine=True`` the contract's table is materialised with valid rows only and
    rejected rows go to ``quarantine.<table>``. Returns results and quarantined row count.
    """
    row_rules = [r for r in contract.rules if r.row_level]
    table_rules = [r for r in contract.rules if not r.row_level]
    columns = [r[0] for r in con.execute(f"DESCRIBE {source}").fetchall()]
    cols = ", ".join(f"src.{ident(c)}" for c in columns)
    flags = [f"COALESCE({row_predicate(r)}, TRUE) AS __r{i}" for i, r in enumerate(row_rules)]
    con.execute(f"CREATE OR REPLACE TEMP TABLE __eval AS SELECT {', '.join([cols] + flags)} FROM {source} AS src")
    total = con.execute("SELECT count(*) FROM __eval").fetchone()[0]
    results: list[Result] = []
    if row_rules:
        failed = con.execute("SELECT " + ", ".join(f"count(*) FILTER (WHERE NOT __r{i})" for i in range(len(row_rules)))
                             + " FROM __eval").fetchone()
        results += [Result(contract.name, r, total, int(f)) for r, f in zip(row_rules, failed, strict=True)]

    quarantined = 0
    plain = ", ".join(ident(c) for c in columns)
    if quarantine:
        blocking = [i for i, r in enumerate(row_rules) if r.severity == "error"]
        valid = " AND ".join(f"__r{i}" for i in blocking) or "TRUE"
        reason = ", ".join(f"CASE WHEN NOT __r{i} THEN {literal(row_rules[i].name)} END" for i in blocking) or "NULL"
        con.execute(f"CREATE OR REPLACE TABLE {contract.name} AS SELECT {plain} FROM __eval WHERE {valid}")
        con.execute(f"CREATE OR REPLACE TABLE quarantine.{contract.table} AS SELECT {plain}, "
                    f"concat_ws('; ', {reason}) AS quarantine_reason FROM __eval WHERE NOT ({valid})")
        quarantined = con.execute(f"SELECT count(*) FROM quarantine.{contract.table}").fetchone()[0]

    target = contract.name if quarantine else source
    for rule in table_rules:
        passed, observed = table_check(con, rule, target, as_of)
        results.append(Result(contract.name, rule, 1, 0 if passed else 1, observed))
    con.execute("DROP TABLE IF EXISTS __eval")
    return results, int(quarantined)


def score(results: list[Result]) -> float | None:
    """0-100 quality score: mean pass rate, blocking rules weigh double."""
    if not results:
        return None
    weights = [2.0 if r.rule.severity == "error" else 1.0 for r in results]
    return round(sum(w * r.pass_rate for w, r in zip(weights, results, strict=True)) / sum(weights), 2)
