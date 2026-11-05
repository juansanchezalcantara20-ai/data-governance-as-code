"""Governance-as-code validators.

Each validator module exposes ``check() -> list[Finding]``. ``run_all`` aggregates them;
any finding at level ``error`` fails ``govkit validate`` and therefore the CI build.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass

VALIDATORS = ("roles", "access", "glossary", "contracts", "maturity", "value")


@dataclass(frozen=True)
class Finding:
    check: str
    level: str  # error | warning
    subject: str
    message: str

    def __str__(self) -> str:
        return f"[{self.level.upper():7}] {self.check:<10} {self.subject}: {self.message}"


def run_all(only: list[str] | None = None) -> list[Finding]:
    findings: list[Finding] = []
    for name in VALIDATORS:
        if only and name not in only:
            continue
        try:
            module = importlib.import_module(f"{__name__}.{name}")
        except ModuleNotFoundError:
            continue
        findings += module.check()
    return findings
