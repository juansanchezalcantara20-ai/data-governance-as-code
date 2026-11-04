"""Data contracts in Open Data Contract Standard (ODCS) v3 format.

One YAML file per published dataset lives in ``contracts/``. This module parses the
subset of ODCS v3 that govkit uses and turns it into executable rules:

* ``schema[].properties[]``: name, logicalType, physicalType, required, unique,
  primaryKey, classification, businessName (the glossary term), tags (``pii:<category>``)
  and property-level ``quality`` rules.
* ``schema[].quality``: table-level rules.
* ``slaProperties``: ``latency`` becomes an executable freshness (timeliness) rule.
* ``team``: the Data Owner and Data Steward of the dataset.
* ``customProperties``: ``dataClassification`` and ``changePolicy``.

Quality rules keep the ODCS v3 shape (``type: library | sql``, ``dimension``,
``severity``). The library rule vocabulary is govkit's own; see ``RULE_TYPES``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .paths import contracts_dir, load_yaml, models_dir

LAYERS = ("bronze", "silver", "gold")
DIMENSIONS = ("completeness", "uniqueness", "validity", "consistency", "accuracy", "timeliness")
SEVERITIES = ("error", "warning")
LOGICAL_TYPES = {
    "string": {"VARCHAR"},
    "integer": {"INTEGER", "BIGINT", "HUGEINT", "SMALLINT"},
    "number": {"DOUBLE", "DECIMAL", "FLOAT", "REAL"},
    "date": {"DATE"},
    "timestamp": {"TIMESTAMP", "TIMESTAMP WITH TIME ZONE"},
    "boolean": {"BOOLEAN"},
}
# Library rule -> (row-level?, default dimension)
RULE_TYPES = {
    "notNull": (True, "completeness"),
    "unique": (True, "uniqueness"),
    "pattern": (True, "validity"),
    "validValues": (True, "validity"),
    "range": (True, "validity"),
    "references": (True, "consistency"),
    "expression": (True, "consistency"),
    "tolerance": (True, "accuracy"),
    "rowCount": (False, "completeness"),
    "freshness": (False, "timeliness"),
    "sql": (False, "consistency"),
}


@dataclass
class Rule:
    name: str
    kind: str
    column: str | None
    args: dict
    dimension: str
    severity: str
    description: str = ""
    origin: str = "declared"  # declared | derived

    @property
    def row_level(self) -> bool:
        return RULE_TYPES[self.kind][0]


@dataclass
class Property:
    name: str
    logical_type: str
    physical_type: str
    required: bool = False
    unique: bool = False
    primary_key: bool = False
    classification: str | None = None
    description: str = ""
    business_name: str | None = None
    tags: list[str] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)

    @property
    def pii(self) -> str | None:
        return next((t.split(":", 1)[1] for t in self.tags if t.startswith("pii:")), None)


@dataclass
class Contract:
    id: str
    name: str
    version: str
    status: str
    domain: str
    data_product: str
    purpose: str
    usage: str
    limitations: str
    classification: str
    owner: str | None
    steward: str | None
    properties: list[Property]
    table_rules: list[Rule]
    latency_days: float | None
    latency_column: str | None
    change_policy: dict
    tags: list[str]
    path: Path | None = None
    raw: dict = field(default_factory=dict)

    @property
    def layer(self) -> str:
        return self.name.split(".")[0]

    @property
    def table(self) -> str:
        return self.name.split(".")[1]

    @property
    def rules(self) -> list[Rule]:
        return [r for p in self.properties for r in p.rules] + self.table_rules

    @property
    def pii_columns(self) -> dict[str, str]:
        return {p.name: p.pii for p in self.properties if p.pii}

    @property
    def primary_key(self) -> list[str]:
        return [p.name for p in self.properties if p.primary_key]

    def column(self, name: str) -> Property | None:
        return next((p for p in self.properties if p.name == name), None)

    @property
    def sql_path(self) -> Path:
        return models_dir() / f"{self.name}.sql"


def _custom(items: list | None) -> dict:
    return {i["property"]: i.get("value") for i in items or [] if "property" in i}


def _rule(item: dict, column: str | None, index: int) -> Rule:
    kind = "sql" if item.get("type") == "sql" else item.get("rule")
    if kind not in RULE_TYPES:
        raise ValueError(f"Unknown quality rule {kind!r} (column {column}): {item}")
    args = dict(item.get("arguments") or {})
    if kind == "sql":
        args["query"] = item["query"]
        for key in ("mustBe", "mustNotBe", "mustBeLessThan", "mustBeLessOrEqualTo", "mustBeGreaterThan",
                    "mustBeGreaterOrEqualTo", "mustBeBetween"):
            if key in item:
                args[key] = item[key]
    return Rule(
        name=item.get("name") or f"{column or 'table'}_{kind}_{index}",
        kind=kind,
        column=column,
        args=args,
        dimension=item.get("dimension", RULE_TYPES[kind][1]),
        severity=item.get("severity", "error"),
        description=item.get("description", ""),
    )


def parse(doc: dict, path: Path | None = None) -> Contract:
    if not doc.get("schema"):
        raise ValueError(f"{path}: contract has no schema")
    obj = doc["schema"][0]
    custom = _custom(doc.get("customProperties"))
    team = {m.get("role"): m.get("username") for m in doc.get("team") or []}
    properties = []
    for p in obj.get("properties") or []:
        prop = Property(
            name=p["name"],
            logical_type=p.get("logicalType", "string"),
            physical_type=str(p.get("physicalType", "VARCHAR")).upper(),
            required=bool(p.get("required") or p.get("primaryKey")),
            unique=bool(p.get("unique") or (p.get("primaryKey") and len(
                [x for x in obj["properties"] if x.get("primaryKey")]) == 1)),
            primary_key=bool(p.get("primaryKey")),
            classification=p.get("classification"),
            description=p.get("description", "") or "",
            business_name=p.get("businessName"),
            tags=list(p.get("tags") or []),
        )
        if prop.required:
            prop.rules.append(Rule(f"{prop.name}_not_null", "notNull", prop.name, {}, "completeness", "error",
                                   "Derived from required: true.", "derived"))
        if prop.unique:
            prop.rules.append(Rule(f"{prop.name}_unique", "unique", prop.name, {}, "uniqueness", "error",
                                   "Derived from unique/primaryKey.", "derived"))
        prop.rules += [_rule(q, prop.name, i) for i, q in enumerate(p.get("quality") or [])]
        properties.append(prop)
    table_rules = [_rule(q, None, i) for i, q in enumerate(obj.get("quality") or [])]
    pk = [p.name for p in properties if p.primary_key]
    if len(pk) > 1:
        table_rules.append(Rule("primary_key_unique", "sql", None, {
            "query": f"SELECT count(*) - count(DISTINCT ({', '.join(pk)})) FROM {{object}}", "mustBe": 0},
            "uniqueness", "error", "Derived from the composite primary key.", "derived"))

    latency_days = latency_column = None
    for sla in doc.get("slaProperties") or []:
        if sla.get("property") == "latency":
            unit = str(sla.get("unit", "d")).lower()
            latency_days = float(sla["value"]) / (24 if unit in ("h", "hour", "hours") else 1)
            latency_column = str(sla.get("element", "")).split(".")[-1] or None
    if latency_days is not None and latency_column:
        table_rules.append(Rule("freshness_sla", "freshness", None,
                                {"column": latency_column, "maxAgeDays": latency_days}, "timeliness", "error",
                                f"Derived from the latency SLA ({latency_days:g} days on {latency_column}).",
                                "derived"))
    desc = doc.get("description") or {}
    return Contract(
        id=doc.get("id", ""),
        name=obj.get("physicalName") or doc.get("name"),
        version=str(doc.get("version", "0.0.0")),
        status=doc.get("status", "draft"),
        domain=doc.get("domain", ""),
        data_product=doc.get("dataProduct", ""),
        purpose=desc.get("purpose", "") if isinstance(desc, dict) else str(desc),
        usage=desc.get("usage", "") if isinstance(desc, dict) else "",
        limitations=desc.get("limitations", "") if isinstance(desc, dict) else "",
        classification=custom.get("dataClassification", "internal"),
        owner=team.get("data_owner"),
        steward=team.get("data_steward"),
        properties=properties,
        table_rules=table_rules,
        latency_days=latency_days,
        latency_column=latency_column,
        change_policy=custom.get("changePolicy") or {},
        tags=list(doc.get("tags") or []),
        path=path,
        raw=doc,
    )


def load(path: Path) -> Contract:
    return parse(load_yaml(path), path)


def load_all() -> list[Contract]:
    folder = contracts_dir()
    return [load(p) for p in sorted(folder.glob("*.odcs.yaml"))] if folder.exists() else []


def by_name() -> dict[str, Contract]:
    return {c.name: c for c in load_all()}
