# Documentation

**English** · [Español](es/README.md)

| Document | What it is |
|---|---|
| [STATUS.md](STATUS.md) | What exists, what is pending, chosen stack |
| [DECISIONS.md](DECISIONS.md) | Decision log (D-001 … D-037) |
| [examples/breaking-change.md](examples/breaking-change.md) | Worked example: a schema change fails CI |
| [../deploy/unity_catalog/README.md](../deploy/unity_catalog/README.md) | Applying the generated Unity Catalog SQL (not executed) |

## Generated (do not edit; `python -m govkit docs`)

| Document | Source |
|---|---|
| [operating_model.md](generated/operating_model.md) | `governance/roles.yaml`, `raci.yaml` |
| [access_model.md](generated/access_model.md) · [access_grants.sql](generated/access_grants.sql) | `governance/users.yaml`, `domains.yaml`, `classification.yaml`, `access_policy.yaml` |
| [glossary.md](generated/glossary.md) · [glossary.html](generated/glossary.html) | `governance/glossary.yaml` |
| [contracts.md](generated/contracts.md) | `contracts/*.odcs.yaml` |
| [quality_report.md](generated/quality_report.md) | last pipeline run |
| [lineage.md](generated/lineage.md) | SQL models + `models/exposures.yaml` |
| [maturity.md](generated/maturity.md) | `governance/maturity.yaml` |
