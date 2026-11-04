# Decision log

Each decision records the choice, the alternatives considered and why. Newest last.

## D-001 · Keep the existing Python + DuckDB engine instead of switching to dbt
- **Context:** the plan suggests dbt-core + DuckDB only if no stack had been chosen. The repo already had a working
  Python + DuckDB + sqlglot pipeline with quarantine, lineage and a UI.
- **Decision:** keep it. Transformations stay as plain SQL files (one per model), so they remain portable to dbt or
  Databricks later.
- **Why:** respecting an existing stack is the stated rule; the custom engine also lets the governance layer
  (contracts, RACI, access policy) drive the pipeline directly, which is the point of the project.

## D-002 · Restart git history before the first publication
- **Context:** the single prototype commit was never pushed. It contained Spanish identifiers and real place and
  manufacturer names in the synthetic generator.
- **Decision:** discard that commit and rebuild history phase by phase, in English.
- **Why:** rule "only public or synthetic data, nothing real" applies to history too; a public repo exposes every commit.

## D-003 · Fictional operations company as the data domain
- **Context:** the plan asks for service orders, assets, inventory and customers.
- **Decision:** one fictional field-services company with three data domains: `operations` (assets, technicians,
  service orders, labor), `supply_chain` (materials, material issues, inventory position) and `customer`
  (customer accounts and value). Sites are `Site North/South/East/West/Central`; manufacturers are `OEM Alpha…Delta`.
  People are obviously invented (`Riley Placeholder`, `Sam Samplewood`) with `example.org` emails.
- **Why:** realistic enough to exercise every governance control (PII, confidential costs, master data,
  cross-domain references) while being unmistakably synthetic.

## D-004 · Seeded, deliberately imperfect data
- **Decision:** the generator uses a fixed seed (`42`) and an anchored "today" (`2026-10-31`) so every run is
  byte-identical, and it injects known defects (nulls, duplicates, impossible values, orphans, two date formats,
  decimal-shift cost errors, an undeclared PII column).
- **Why:** a governance demo is only convincing if there is something to catch. Fixed seed and anchor date make
  the quality report reproducible in CI and in reviews.

## D-005 · Rename the package to `govkit`, governance YAML under `governance/`
- **Decision:** Python package `govkit` (CLI `govkit`), governance-as-code files in `governance/`, contracts in
  `contracts/`, SQL models in `models/`, raw-source registry in `models/sources.yaml`.
- **Why:** English, short, and the folder layout mirrors the governance artifacts a reviewer looks for.
