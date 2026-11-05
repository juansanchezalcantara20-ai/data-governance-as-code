"""Contract change policy enforcement: is a contract change breaking, and was it versioned as such?

Breaking (requires a major version bump, see each contract's ``changePolicy``):
removed or renamed column, changed logical type, optional column made required,
changed primary key, raised classification.
Non-breaking: added optional column, quality rules added or relaxed, descriptions.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

from . import contracts as contracts_mod
from .paths import contracts_dir, governance, root


@dataclass
class Change:
    contract: str
    breaking: bool
    detail: str


def _major(version: str) -> int:
    return int(version.split(".")[0])


def diff(old: contracts_mod.Contract, new: contracts_mod.Contract) -> list[Change]:
    levels = {k: v["rank"] for k, v in governance("classification")["levels"].items()}
    changes: list[Change] = []
    before = {p.name: p for p in old.properties}
    after = {p.name: p for p in new.properties}
    for name in before.keys() - after.keys():
        changes.append(Change(new.name, True, f"column '{name}' removed or renamed"))
    for name in after.keys() - before.keys():
        breaking = after[name].required
        changes.append(Change(new.name, breaking, f"column '{name}' added" + (" as required" if breaking else "")))
    for name in before.keys() & after.keys():
        a, b = before[name], after[name]
        if a.logical_type != b.logical_type:
            changes.append(Change(new.name, True, f"column '{name}' type {a.logical_type} -> {b.logical_type}"))
        if b.required and not a.required:
            changes.append(Change(new.name, True, f"column '{name}' became required"))
        before_cls, after_cls = old.column_classification(name, levels), new.column_classification(name, levels)
        if levels.get(after_cls, 0) > levels.get(before_cls, 0):
            changes.append(Change(new.name, True, f"column '{name}' classification raised {before_cls} -> {after_cls}"))
    if old.primary_key != new.primary_key:
        changes.append(Change(new.name, True, f"primary key {old.primary_key} -> {new.primary_key}"))
    if levels.get(new.classification, 0) > levels.get(old.classification, 0):
        changes.append(Change(new.name, True, f"classification raised {old.classification} -> {new.classification}"))
    return changes


def check_pair(old: contracts_mod.Contract | None, new: contracts_mod.Contract) -> list[str]:
    """Policy violations for one contract change."""
    if old is None:
        return []
    breaking = [c for c in diff(old, new) if c.breaking]
    if breaking and _major(new.version) <= _major(old.version):
        return [f"{new.name}: breaking change without a major version bump ({old.version} -> {new.version}): "
                + "; ".join(c.detail for c in breaking)]
    return []


def load_at_ref(ref: str) -> dict[str, contracts_mod.Contract]:
    rel = contracts_dir().relative_to(root())
    names = subprocess.run(["git", "ls-tree", "--name-only", ref, f"{rel}/"], cwd=root(), capture_output=True,
                           text=True, check=True).stdout.split()
    out = {}
    for name in names:
        if name.endswith(".odcs.yaml"):
            text = subprocess.run(["git", "show", f"{ref}:{name}"], cwd=root(), capture_output=True, text=True,
                                  check=True).stdout
            c = contracts_mod.parse(yaml.safe_load(text), Path(name))
            out[c.name] = c
    return out


def check_against(ref: str) -> list[str]:
    old = load_at_ref(ref)
    problems = []
    for new in contracts_mod.load_all():
        problems += check_pair(old.get(new.name), new)
    for name in old.keys() - {c.name for c in contracts_mod.load_all()}:
        problems.append(f"{name}: contract deleted; retire it through raci.retire_dataset (status: retired) instead")
    return problems
