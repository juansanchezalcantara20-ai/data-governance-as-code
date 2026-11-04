# Project status

_Last updated: 2026-11-04. This file tracks what exists, what is missing against the plan, and the chosen stack._

## Starting point (inventory before the governance phases)

The repository started as a working prototype, written in Spanish, built and run in this same environment:

| Area | What existed | Location (prototype) |
|---|---|---|
| Stack | Python 3.10+, DuckDB (single-file lakehouse), sqlglot (SQL parsing), Streamlit (UI), pytest | `pyproject.toml` |
| Pipeline | Medallion pipeline bronze → silver → gold, topological ordering from SQL, quarantine of rows that fail blocking rules | `src/gobdatos/pipeline.py`, `calidad.py` |
| Data | Seeded synthetic generator for two domains with deliberately injected defects | `src/gobdatos/generador.py` |
| Governance config | Roles and users in one file, per-domain glossaries, one YAML contract per table (custom format) | `config/` |
| Lineage | Column-level lineage computed from SQL with sqlglot, impact analysis | `src/gobdatos/linaje.py` |
| Privacy | PII discovery by column name and content, role-based masking, access-request workflow with segregation of duties | `clasificacion.py`, `politicas.py`, `flujos.py` |
| UI | 8-page Streamlit app (catalog, glossary, lineage, quality, privacy, requests, audit) | `app/app.py` |
| Quality of repo | 18 pytest tests, GitHub Actions workflow, Dockerfile, Makefile | `tests/`, `.github/` |

### Gaps found in the prototype against the plan

- All visible text, file names and identifiers were in Spanish (plan requires English).
- The synthetic data used real place names for sites and real equipment manufacturers (plan requires purely fictional data).
- No RACI, no Sponsor/Custodian/Council roles, no access-policy matrix, no domain → owner → steward model.
- Glossary lacked steward, source table/column, linked quality rules, related terms, status and review date.
- Contracts used a custom format instead of a standard (ODCS v3), had no SLA, keys, change policy or compatibility check.
- Quality rules covered five dimensions (no *accuracy*), no generated quality report, lineage only inside the UI.
- No linter, no single reproduce command, no maturity assessment, no Unity Catalog deployment.

## Chosen stack (kept)

Python + DuckDB + sqlglot + Streamlit, with pytest and ruff. dbt was **not** introduced because the repo already had
a working engine; see `docs/DECISIONS.md` (D-001).

## Phase tracker

| Phase | Scope | Status |
|---|---|---|
| 0 | English port, fictional operations dataset, tooling (`make all`, ruff, CI) | ✅ done |
| 1 | Roles, responsibilities, RACI + validator | ✅ done |
| 2 | Users, domains, classification, access policy, SoD, generated GRANTs | ⏳ pending |
| 3 | Business glossary + validator + generated browsable glossary | ⏳ pending |
| 4 | ODCS v3 data contracts, data-vs-contract verification, breaking-change detection | ⏳ pending |
| 5 | Executable quality rules (6 dimensions), quality report, generated lineage | ⏳ pending |
| 6 | DAMA-DMBOK2 maturity self-assessment + roadmap | ⏳ pending |
| 7 | Unity Catalog deployment SQL (not executed), final README, pull request | ⏳ pending |
