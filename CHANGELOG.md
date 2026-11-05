# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/). Data contracts are versioned separately (see each contract's `version`).

## [Unreleased]

### Added
- Spanish documentation: `README.es.md` and `docs/es/` (decision log, breaking-change example, Unity Catalog guide).
- Repository hygiene: `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CODEOWNERS`, pull-request template,
  issue forms for the governance workflows, `.editorconfig`, pre-commit configuration, docs index.
- Test that every relative link in every Markdown file resolves.
- CI matrix on Python 3.10 and 3.12.

## [1.0.0] - 2026-11-05

### Added
- Phase 0: Medallion pipeline on DuckDB, seeded synthetic data with documented injected defects, SQL-derived
  column lineage, personal-data discovery and masking, ODCS v3 parser, quality engine, `make all`, CI.
- Phase 1: roles, responsibilities, escalation and RACI as YAML with a validator.
- Phase 2: users, domains, classification, least-privilege access policy, segregation of duties, compiled GRANTs.
- Phase 3: 38-term business glossary with validator, Markdown and searchable HTML output.
- Phase 4: eleven ODCS v3 data contracts, data-vs-contract verification, change-policy compatibility check.
- Phase 5: quality rules in six dimensions, per-run quality report, generated end-to-end lineage.
- Phase 6: DAMA-DMBOK2 maturity self-assessment with evidence and a prioritised roadmap.
- Phase 7: Unity Catalog SQL generated from the governance YAML (not executed) and final README.

[Unreleased]: https://github.com/juansanchezalcantara20-ai/data-governance-as-code/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/juansanchezalcantara20-ai/data-governance-as-code/releases/tag/v1.0.0
