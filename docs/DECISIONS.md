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
