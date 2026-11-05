# Contributing

[README](README.md) · [Español](README.es.md)

This repository is a governance programme expressed as code. A change to governance follows the same path as a
change to code: a branch, a pull request, automated checks and an approval by the role the RACI names.

## Set up

```bash
make install
pre-commit install   # optional: runs ruff and the governance validators before each commit
make all             # lint, validate, generate, run, verify, docs, tests
```

## Common changes and who approves them

| Change | Files | Run | Accountable (`governance/raci.yaml`) |
|---|---|---|---|
| Propose or edit a glossary term | `governance/glossary.yaml` | `python -m govkit validate --only glossary` | Data Owner of the term's domain |
| Add or change a quality rule | `contracts/<dataset>.odcs.yaml` | `make run verify` | Data Owner of the dataset |
| Change a contract schema | `contracts/`, `models/` | `python -m govkit compat --base origin/main` | Data Owner; breaking changes need a major version |
| Grant or change access | `governance/users.yaml`, `access_policy.yaml` | `python -m govkit validate --only access` | Data Owner (never the requester) |
| Retire a dataset | contract `status: retired` | `make all` | Governance Council |

Use the matching issue form (**New issue**) to open the request before the pull request.

## Rules of the road

- Generated files (`docs/generated/`, `deploy/unity_catalog/*.sql`) are never edited by hand: run
  `python -m govkit docs` and commit the result. CI fails if they are stale.
- Record any non-obvious choice in `docs/DECISIONS.md` (and its Spanish twin `docs/es/decisiones.md`).
- English is the source of truth for documentation; keep `README.es.md` and `docs/es/` in step when you change
  the English originals.
- Only synthetic or public data. Never commit real names, real company data or credentials.
- Commit messages: imperative mood, one logical change per commit.
