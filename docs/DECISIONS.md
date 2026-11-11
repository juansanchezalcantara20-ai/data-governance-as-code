# Decision log

**English** · [Español](es/decisiones.md)

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

## D-006 · RACI validation rules
- **Decision:** exactly one Accountable and at least one Responsible per activity; every role cited must exist;
  the escalation chain must be acyclic with a single top role (the Data Sponsor).
- **Why:** these are the properties that make a RACI usable in practice: one person answers for the outcome,
  someone does the work, and every escalation ends somewhere.

## D-007 · Generated documentation is committed and checked
- **Decision:** `govkit docs` renders `docs/generated/*.md` from YAML and run metadata; CI regenerates them and
  fails on any diff (`make docs-check`).
- **Why:** reviewers can read the governance model on GitHub without running anything, and the docs can never
  drift from the YAML that is actually enforced.

## D-008 · One primary governance role per person
- **Decision:** each user has exactly one role in `users.yaml`; Council membership is modelled as its own role.
- **Why:** keeps the least-privilege check unambiguous (a person's baseline is a single row of the policy).
  Real organisations often stack roles; supporting that is listed in the roadmap.

## D-009 · Provisioned access is declared and must be justified
- **Decision:** `users.yaml` lists the access each person actually has (as an identity-system export would show).
  Every entry needs a basis: `role` (must fit the role baseline) or `request` (ticket, approver, approval and
  expiry dates). Anything else is "access not justified by any role" and fails CI.
- **Why:** this is how access reviews work in practice: compare what is provisioned with what policy allows.

## D-010 · Access-request rules
- **Decision:** exceptions expire within 90 days; restricted data is never granted by request; confidential needs
  the domain's Data Owner, internal can be approved by Owner or Steward; the approver must govern the domain and
  can never be the requester. Expiry is validated as a duration (approval → expiry) rather than against today's
  date, so CI results do not change with the calendar; the runtime check (`access.can_read`) uses the real date.
- **Why:** segregation of duties and time-bound exceptions are the two controls auditors test first.

## D-011 · GRANTs compiled from policy, PostgreSQL syntax
- **Decision:** `govkit docs` compiles `docs/generated/access_grants.sql` (one group per role and domain, user
  grants only for approved exceptions). DuckDB has no GRANT, so the SQL targets PostgreSQL-compatible engines;
  the Databricks Unity Catalog flavour is generated in phase 7.
- **Why:** permissions must come from the policy, never typed by hand.

## D-012 · What "circular" and "orphan" mean for the glossary
- **Circular:** a term whose definition contains its own name, or any cycle in the `depends_on` graph that
  metrics use to declare which terms their formula is built from.
- **Orphan:** a term that is neither the source column of a SQL model nor the `businessName` of any contract
  property. Every term must point at real data.
- **Why:** these are the two failure modes that make glossaries useless in practice: definitions that explain
  nothing, and terms nobody can find in the data.

## D-013 · Glossary rendered twice
- **Decision:** `docs/generated/glossary.md` (readable on GitHub, with anchors) and a self-contained
  `docs/generated/glossary.html` with client-side search, no external assets.
- **Why:** Markdown is what a reviewer opens on GitHub; the HTML page is what a business user would actually browse.

## D-014 · ODCS v3 for contracts, with a documented rule vocabulary
- **Decision:** contracts follow Open Data Contract Standard v3 (`apiVersion: v3.0.2`, `kind: DataContract`,
  `schema[].properties[]`, `quality`, `slaProperties`, `team`, `customProperties`). Quality rules keep the ODCS
  shape (`type: library | sql`, `dimension`, `severity`); the library rule names (`pattern`, `validValues`,
  `range`, `references`, `expression`, `tolerance`, `rowCount`) are govkit's own, listed in
  `src/govkit/contracts.py`. Classification and change policy live in `customProperties`; PII categories are
  property tags `pii:<category>`; the glossary link is `businessName`.
- **Why:** ODCS is vendor-neutral and maps to Databricks, Snowflake or dbt. dbt model contracts were not an
  option because the stack has no dbt (D-001).

## D-015 · Contract obligations become executable rules automatically
- **Decision:** `required` → completeness rule, `unique`/single `primaryKey` → uniqueness rule, composite key →
  SQL uniqueness check, `latency` SLA → timeliness rule against the run's as-of date.
- **Why:** what the contract promises is exactly what gets tested; no second place to keep in sync.

## D-016 · Schema conformance runs before quality rules
- **Decision:** a built table is first compared with its contract (missing column, undeclared column, logical
  type). On a schema break its rules are skipped and the run fails.
- **Why:** found while writing the breaking-change test: rules on a mis-shaped table fail with confusing SQL
  errors. Checking the shape first gives the developer the actual cause.

## D-017 · Silver blocks bad rows, gold blocks the release
- **Decision:** on silver, rows failing an `error` rule go to `quarantine.<table>` and the run continues. On gold, a
  failing `error` rule or any schema violation makes `govkit verify` fail.
- **Why:** bad source rows are expected and handled by stewards; a broken published KPI is not acceptable.

## D-018 · One known open finding is left in on purpose
- **Decision:** `labor_entries.approver_email` holds email addresses but is not tagged as personal data. The
  pipeline reports it as a high-severity finding on every run.
- **Why:** shows that discovery catches what declarations miss. Remediation is in the roadmap; fixing it is a
  one-line contract change (`tags: ["pii:email"]`) plus a classification review.

## D-019 · Six quality dimensions and how each is measured
- **Decision:** completeness (`required`, row counts), uniqueness (keys), validity (patterns, domains, ranges),
  consistency (referential integrity, cross-column logic, formula checks), accuracy (agreement with an
  authoritative reference: issued cost vs material master within 25 %, gold totals reconciled to silver), and
  timeliness (latency SLA vs the run's as-of date).
- **Why:** accuracy is the dimension most projects skip because it needs a reference; using the master data and
  cross-layer reconciliation makes it measurable without external sources.

## D-020 · Glossary-to-rule traceability
- **Decision:** glossary terms list the contract rules that protect them; the quality report shows, per term,
  how many rules apply and their pass rate. Metric formulas are themselves tested (`margin_definition_holds`,
  reconciliation rules).
- **Why:** this closes the loop business definition → executable rule → measured result.

## D-021 · Report on every run, published copy in docs
- **Decision:** `govkit run` writes `reports/quality_report.{md,json}` (git-ignored, one per run). `govkit docs`
  publishes the latest run to `docs/generated/quality_report.md`. Reports contain no timestamps or run ids, so the
  published copy is reproducible and checked in CI like the other generated docs.
- **Why:** reviewers see real output on GitHub; CI proves it is current.

## D-022 · Lineage as Mermaid generated from SQL
- **Decision:** dataset-level lineage is emitted as a Mermaid flowchart (renders natively on GitHub) plus a
  column-level table for every gold column; consumers come from `models/exposures.yaml`.
- **Why:** no extra tooling to view it, and it cannot drift because it is computed from the SQL on every run.

## D-023 · Maturity assessment is evidence-backed and conservative
- **Decision:** own 1-5 scale (ad hoc, documented, defined and enforced, measured, optimising) applied to this
  repository only. Each score lists files as evidence; CI fails if a file is missing, and any score of 3 or more
  needs at least three pieces of evidence. No area is scored 4: nothing is yet tracked over time against targets.
- **Why:** a self-assessment is only credible if it is falsifiable and errs low.

## D-024 · The prototype Streamlit UI was not ported
- **Decision:** the Spanish prototype had an 8-page Streamlit app. It was removed during the English port and not
  rebuilt; the governance artefacts are published as generated Markdown/HTML instead.
- **Why:** the brief is a programme that verifies itself; a UI adds surface without adding a control. Publishing
  to a real catalog is on the roadmap and is the better next step.

## D-025 · Unity Catalog SQL generated, never executed here
- **Decision:** `govkit deploy` compiles catalog, schemas, tables (types, NOT NULL, informational primary keys,
  comments), tags (classification, domain, owner, steward, `pii`, `glossary_term`), grants per group and column
  masks from the same YAML. Every file starts with "NOT EXECUTED IN THIS REPO"; CI checks the files are current.
- **Why:** no Databricks access in this environment and no credentials should be requested. Generating from the
  policy keeps the platform configuration a derivative of governance, not a parallel copy.
- **Masks:** clear text only for groups whose role has `unmasked_pii: true` and only in their own domain, using
  `is_account_group_member`; numeric compensation is masked to NULL.

## D-026 · Repository name
- **Decision:** `data-governance-as-code`. The local working folder kept its prototype name; it is not visible
  in the repository.

## D-027 · Bilingual documentation, English as the source of truth
- **Context:** the original brief required everything visible in English; the owner later asked for Spanish too.
- **Decision:** `README.md` (English) and `README.es.md` (Spanish) link to each other. Key narrative documents
  have Spanish versions in `docs/es/`. Code, YAML keys, file names of governance artefacts, generated
  documentation and standard vocabulary (ODCS, RACI, DAMA-DMBOK2) stay in English, which remains the source of
  truth. A test checks that every relative link in every Markdown file resolves, so translations cannot point at
  missing files.
- **Why:** reaches both local and international reviewers without maintaining two codebases; generated docs stay
  single-language so CI can keep checking them.

## D-028 · Standard repository hygiene
- **Decision:** add `CHANGELOG.md` (Keep a Changelog, semantic versioning), `CONTRIBUTING.md`, `SECURITY.md`,
  `CODE_OF_CONDUCT.md`, `CODEOWNERS`, a pull-request template with a governance checklist, issue forms for the
  governance workflows in `raci.yaml` (glossary term, quality incident, access request, contract change),
  `.editorconfig`, a pre-commit configuration, and a CI matrix on Python 3.10 and 3.12.
- **Why:** reviewers judge a portfolio repository by these signals first, and the issue forms turn the RACI
  activities into an actual intake process.

## D-029 · Two more roles: Field Technician and Data Auditor
- **Decision:** add `field_technician` (operational data of the assigned domain, silver and gold, up to internal)
  and `auditor` (every domain and layer up to restricted, personal data masked, `read_only: true`). Only
  `quarantine_actions` roles (owner, steward, custodian) may release or discard quarantined rows.
- **Why:** the navigable demo lets a visitor switch persona; these two make least privilege visible in both
  directions (the technician sees orders but no money; the auditor sees everything but changes nothing).

## D-030 · Column-level classification
- **Decision:** a contract property may carry its own `classification`, never below its dataset's. The effective
  level of a column is the higher of both. `silver.service_orders` becomes `internal` with price and planned costs
  `confidential`. Readers below a column's level do not get it: column-level `GRANT` in the PostgreSQL output,
  NULL-returning column masks in Unity Catalog. Raising a column's effective level is a breaking change.
- **Why:** whole-table classification forces a choice between hiding operational data from field teams or
  exposing money to them; column level removes that trade-off.

## D-031 · Spanish glossary content lives next to the glossary
- **Decision:** `governance/glossary_translations.yaml` holds, per term id, the Spanish name, definition and
  example, and an English example. The validator requires every term to be translated and rejects circular Spanish
  definitions.
- **Why:** the demo app is Spanish-first; translations are governed content with the same checks, not UI strings.

## D-032 · A static demo app fed only by the engine (honesty lock)
- **Decision:** `app/` is a dependency-free static single-page app published on GitHub Pages. Its data is
  `app/data/*.json`, written only by `govkit export-app`; `make docs-check`, CI and the Pages workflow fail if the
  committed JSON differs from what the engine produces. No server, no framework, no external assets at runtime.
- **Why:** a reviewer understands a governance tool by using it; a mock-up would prove nothing, so every number must be
  traceable to the engine and impossible to edit by hand.

## D-033 · Deterministic output: single-threaded DuckDB
- **Decision:** connections run with one thread. Parallel aggregation summed floats in a varying order and moved a
  rounded cent between runs (found by the honesty lock).
- **Why:** reproducibility is what makes generated, committed artefacts checkable; the dataset is small.

## D-034 · Personas mapped to real users and the real policy
- **Decision:** the app's "View as" personas are the users `riley.placeholder` (owner), `drew.stubbs` (custodian),
  `jamie.fakeley` (analyst), `rowan.pretendez` (field technician) and `ellis.checkwell` (auditor). What each sees per
  table and column is computed by `access.column_view` at export time; the e2e test checks the screen matches.
- **Why:** least privilege is demonstrated with the same code that would grant it, not with UI-only rules.

## D-035 · Value shown under illustrative assumptions
- **Decision:** `governance/supuestos_valor.yaml` (name requested by the owner) holds labelled, ranged assumptions in
  soles. Facts come only from the pipeline run. Law No. 29733 is cited as context; no fines are estimated. The same
  formula runs in Python (`govkit/value.py`) and JavaScript (`app/js/value.js`), both rounding half up; the e2e test
  compares them.
- **Why:** value is what decision-makers ask for, and assumptions must be visible and changeable to be honest.

## D-036 · Project 2 catalog governed as a report, not a gate
- **Decision:** an offline copy of the KPI catalog of `kpi-catalog-storytelling` (commit `67e3e37`) is checked with
  glossary, ownership and contract rules; results are shown in the app. Its gaps (no steward field, KPIs without
  declared input or reference SQL) do not fail this repository's CI because the catalog belongs to another repo.
- **Why:** shows the engine is reusable on someone else's metadata without coupling the two projects.

## D-037 · The change log uses recorded CI runs
- **Decision:** `docs/ci_history.yaml` records real GitHub Actions runs with links, and the app reads it. It is not
  fetched at build time.
- **Why:** fetching would make the exported JSON change on every run and break the honesty lock.
