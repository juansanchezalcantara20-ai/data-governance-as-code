## What changes

<!-- One or two sentences. Link the issue (glossary term, quality incident, access request, contract change). -->

## Governance checklist

- [ ] `make all` passes locally (lint, validate, run, verify, docs, tests).
- [ ] Generated files were regenerated with `python -m govkit docs`, not edited by hand.
- [ ] Contract changes: breaking changes bump the major version (`python -m govkit compat --base origin/main`).
- [ ] Access changes: requester and approver are different people, and the exception has an expiry date.
- [ ] Non-obvious decisions are recorded in `docs/DECISIONS.md` and `docs/es/decisiones.md`.
- [ ] Only synthetic or public data; no real names, company data or secrets.

## Approval required (from `governance/raci.yaml`)

<!-- Example: change_data_contract → Accountable: Data Owner of the domain. -->
