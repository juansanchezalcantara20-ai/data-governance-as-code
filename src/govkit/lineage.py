"""Column-level lineage generated from the SQL models (never drawn by hand).

Each model in ``models/<layer>.<table>.sql`` is parsed with sqlglot; for every output
column the source columns are traced through CTEs, joins and aggregations. Bronze
tables trace back to their source file, and gold tables forward to their declared
consumers (``models/exposures.yaml``), giving end-to-end lineage from source to use.
"""

from __future__ import annotations

from collections import deque

import duckdb
from sqlglot import exp, parse_one
from sqlglot.lineage import lineage

from .db import table_columns


def referenced_tables(sql: str) -> set[str]:
    """Physical tables (schema.table) a query reads, excluding CTE names."""
    tree = parse_one(sql, dialect="duckdb")
    ctes = {c.alias_or_name for c in tree.find_all(exp.CTE)}
    out = set()
    for t in tree.find_all(exp.Table):
        if t.name in ctes and not t.db:
            continue
        out.add(f"{t.db}.{t.name}" if t.db else t.name)
    return out


def model_edges(con: duckdb.DuckDBPyConnection, target: str, sql: str) -> list[tuple[str, str, str, str]]:
    """Edges (target_dataset, target_column, source_dataset, source_column) for one model."""
    schema: dict = {}
    for t in referenced_tables(sql):
        db, _, name = t.partition(".")
        schema.setdefault(db, {})[name] = table_columns(con, t)
    edges: list[tuple[str, str, str, str]] = []
    for column in table_columns(con, target):
        try:
            node = lineage(column, sql, schema=schema, dialect="duckdb")
        except Exception:  # noqa: BLE001 - constant or untraceable expression
            continue
        for leaf in node.walk():
            if leaf.downstream or not isinstance(leaf.expression, exp.Table):
                continue
            table = leaf.expression
            source = f"{table.db}.{table.name}" if table.db else table.name
            edge = (target, column, source, leaf.name.split(".")[-1])
            if edge not in edges:
                edges.append(edge)
    return edges


def source_edges(con: duckdb.DuckDBPyConnection, target: str, file: str) -> list[tuple[str, str, str, str]]:
    return [(target, c, f"file:{file}", c) for c in table_columns(con, target) if not c.startswith("_")]


def exposure_edges(exposures: list[dict]) -> list[tuple[str, str, str, str]]:
    edges = []
    for e in exposures:
        for dep in e.get("depends_on", []):
            edges.append((f"exposure:{e['name']}", "*", dep, "*"))
    return edges


def _walk(con, dataset: str, column: str | None, upstream: bool) -> list[dict]:
    if upstream:
        sql = ("SELECT source_dataset, source_column FROM meta.lineage WHERE target_dataset = ? "
               "AND (? IS NULL OR target_column = ? OR target_column = '*')")
    else:
        sql = ("SELECT target_dataset, target_column FROM meta.lineage WHERE source_dataset = ? "
               "AND (? IS NULL OR source_column = ? OR source_column = '*')")
    seen, out = set(), []
    queue = deque([(dataset, column, 0)])
    while queue:
        d, c, depth = queue.popleft()
        c = None if c == "*" else c
        for nd, nc in con.execute(sql, [d, c, c]).fetchall():
            if (nd, nc) in seen:
                continue
            seen.add((nd, nc))
            out.append({"dataset": nd, "column": nc, "depth": depth + 1, "via": f"{d}.{c or '*'}"})
            queue.append((nd, nc, depth + 1))
    return out


def upstream(con, dataset: str, column: str | None = None) -> list[dict]:
    """Everything that feeds ``dataset.column``, back to the source file."""
    return _walk(con, dataset, column, upstream=True)


def downstream(con, dataset: str, column: str | None = None) -> list[dict]:
    """Impact analysis: everything affected if ``dataset.column`` changes."""
    return _walk(con, dataset, column, upstream=False)


def _node_id(name: str) -> str:
    return "n_" + "".join(ch if ch.isalnum() else "_" for ch in name)


def mermaid(con, focus: str | None = None) -> str:
    """Dataset-level lineage as a Mermaid flowchart (renders natively on GitHub)."""
    edges = con.execute("SELECT DISTINCT source_dataset, target_dataset FROM meta.lineage ORDER BY 1, 2").fetchall()
    if focus:
        related = {focus} | {x["dataset"] for x in upstream(con, focus)} | {x["dataset"] for x in downstream(con, focus)}
        edges = [(s, t) for s, t in edges if s in related and t in related]
    nodes = sorted({n for e in edges for n in e})
    lines = ["flowchart LR"]
    styles = {"file": "source", "bronze": "bronze", "silver": "silver", "gold": "gold", "exposure": "exposure"}
    for n in nodes:
        kind = n.split(":")[0] if ":" in n else n.split(".")[0]
        label = n.split(":", 1)[1] if ":" in n else n
        shape = f'[("{label}")]' if kind == "file" else (f'[/"{label}"/]' if kind == "exposure" else f'["{label}"]')
        lines.append(f"    {_node_id(n)}{shape}:::{styles.get(kind, 'silver')}")
    for s, t in edges:
        lines.append(f"    {_node_id(s)} --> {_node_id(t)}")
    lines += [
        "    classDef source fill:#eeeeee,stroke:#888",
        "    classDef bronze fill:#e3b58c,stroke:#8a5a2b",
        "    classDef silver fill:#d5dbe1,stroke:#6b7785",
        "    classDef gold fill:#f2d06b,stroke:#9a7b12",
        "    classDef exposure fill:#cfe8d5,stroke:#2f7a45",
    ]
    return "\n".join(lines)


def dot(con, focus: str | None = None) -> str:
    """Dataset-level lineage in Graphviz DOT (used by the Streamlit app)."""
    edges = con.execute("SELECT DISTINCT source_dataset, target_dataset FROM meta.lineage").fetchall()
    if focus:
        related = {focus} | {x["dataset"] for x in upstream(con, focus)} | {x["dataset"] for x in downstream(con, focus)}
        edges = [(s, t) for s, t in edges if s in related and t in related]
    colors = {"file": "#eeeeee", "bronze": "#e3b58c", "silver": "#d5dbe1", "gold": "#f2d06b", "exposure": "#cfe8d5"}
    nodes = sorted({n for e in edges for n in e} | ({focus} if focus else set()))
    out = ["digraph lineage {", '  rankdir=LR; node [shape=box, style="rounded,filled", fontname="Helvetica"];']
    for n in nodes:
        kind = n.split(":")[0] if ":" in n else n.split(".")[0]
        border = ', penwidth=3, color="#c0392b"' if n == focus else ""
        out.append(f'  "{n}" [fillcolor="{colors.get(kind, "#ffffff")}"{border}];')
    out += [f'  "{s}" -> "{t}";' for s, t in edges]
    return "\n".join(out + ["}"])
