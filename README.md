# Data Governance as Code

A working data governance programme for a **fictional** field-services company, built on a Medallion
(bronze → silver → gold) lakehouse. Roles, users, glossary and data contracts live in versioned YAML, and every
one of them has an automated validator that fails CI when something breaks.

> Work in progress: see [`docs/STATUS.md`](docs/STATUS.md) for the phase tracker and
> [`docs/DECISIONS.md`](docs/DECISIONS.md) for the decision log.

## Run it

```bash
make install
make all        # lint, validate governance, generate data, run the pipeline, test
```

## How this was built

I designed and directed this project, and wrote it with [Claude Code](https://claude.com/claude-code) as the coding agent.
Scope, governance model, decisions and review are mine; the decision log records the reasoning.

## Scope & limitations

- All data is **synthetic** and generated with a fixed seed. Defects are injected on purpose; any quality finding
  illustrates the method and is **not** a result about a real organisation.
- Single-node DuckDB, not a distributed platform.
