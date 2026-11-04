"""Project paths and YAML loading. Override the project root with ``GOVKIT_HOME``."""

from __future__ import annotations

import copy
import os
from functools import lru_cache
from pathlib import Path

import yaml


def root() -> Path:
    return Path(os.environ.get("GOVKIT_HOME", Path.cwd())).resolve()


def governance_dir() -> Path:
    return root() / "governance"


def contracts_dir() -> Path:
    return root() / "contracts"


def models_dir() -> Path:
    return root() / "models"


def data_dir() -> Path:
    return root() / "data"


def sources_dir() -> Path:
    return data_dir() / "sources"


def db_path() -> Path:
    return Path(os.environ.get("GOVKIT_DB", data_dir() / "lakehouse.duckdb"))


def docs_dir() -> Path:
    return root() / "docs"


def reports_dir() -> Path:
    return root() / "reports"


def load_yaml(path: Path) -> dict | list:
    return copy.deepcopy(_load_yaml(str(path), path.stat().st_mtime_ns))


@lru_cache(maxsize=256)
def _load_yaml(path: str, _mtime: int):
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def governance(name: str) -> dict:
    """Load ``governance/<name>.yaml``."""
    return load_yaml(governance_dir() / f"{name}.yaml")
