# Project status

_Last updated: 2026-11-04. This file tracks what exists, what is missing against the plan, and the chosen stack._

## Starting point (inventory before the governance phases)

The repository started as a working prototype, written in Spanish, built and run in this same environment:

| Area | What existed | Location (prototype) |
|---|---|---|
| Stack | Python 3.10+, DuckDB (single-file lakehouse), sqlglot (SQL parsing), Streamlit (UI), pytest | `pyproject.toml` |
| Pipeline | Medallion pipeline bronze → silver → gold, topological ordering from SQL, quarantine of rows that fail blocking rules | prototype modules (since replaced by `src/govkit/`) |
| Data | Seeded synthetic generator for two domains with deliberately injected defects | prototype modules (since replaced by `src/govkit/`) |
| Governance config | Roles and users in one file, per-domain glossaries, one YAML contract per table (custom format) | `config/` |
| Lineage | Column-level lineage computed from SQL with sqlglot, impact analysis | prototype modules (since replaced by `src/govkit/`) |
| Privacy | PII discovery by column name and content, role-based masking, access-request workflow with segregation of duties | prototype modules (since replaced by `src/govkit/`) |
| UI | 8-page Streamlit app (catalog, glossary, lineage, quality, privacy, requests, audit) | prototype UI (removed, see D-024) |
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
| 2 | Users, domains, classification, access policy, SoD, generated GRANTs | ✅ done |
| 3 | Business glossary + validator + generated browsable glossary | ✅ done |
| 4 | ODCS v3 data contracts, data-vs-contract verification, breaking-change detection | ✅ done |
| 5 | Executable quality rules (6 dimensions), quality report, generated lineage | ✅ done |
| 6 | DAMA-DMBOK2 maturity self-assessment + roadmap | ✅ done |
| 7 | Unity Catalog deployment SQL (not executed), final README, pull request | ✅ done · ⏳ push and PR blocked (see below) |

## Current state (end of the governance phases)

- `make all` reproduces everything from a clean checkout: lint (ruff), 5 validators, data generation, pipeline,
  data-vs-contract verification, generated docs and Unity Catalog SQL, 66 pytest tests.
- 6 roles, 9 RACI activities, 3 domains, 11 fictional users, 4 classification levels, 38 glossary terms,
  11 ODCS v3 contracts, 102 executable quality rules in 6 dimensions, 11 DAMA-DMBOK2 areas assessed.

## Pending

| Item | Why it is pending |
|---|---|
| Push to GitHub and open the pull request | This session cannot create repositories; the target repo did not exist. All phases are committed locally. |
| CI run on GitHub Actions | Depends on the push. The same steps pass locally (`make all`, `make docs-check`). |
| Unity Catalog SQL applied in Databricks | No workspace access by design; generated and labelled "not executed". |
| Open finding `labor_entries.approver_email` | Kept on purpose to show discovery (D-018); first item of the roadmap. |
| Roadmap items | See `docs/generated/maturity.md`. |
