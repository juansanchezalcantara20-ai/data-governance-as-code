# Unity Catalog deployment — NOT EXECUTED IN THIS REPO

**English** · [Español](../../docs/es/despliegue-unity-catalog.md)

> ⚠️ **Not executed in this repo.** These SQL files are *generated* by `govkit deploy` (also run by `govkit docs`)
> from the same YAML that CI validates. They have **not** been run against a Databricks workspace. Syntax was
> checked only by parsing with sqlglot's Databricks dialect, which does not model `SET TAGS`, `SET MASK` or
> `GRANT USE CATALOG`. Review them before applying.

| File | What it does | Generated from |
|---|---|---|
| `01_catalog_and_schemas.sql` | Catalog `governance_demo` and schemas `bronze`, `silver`, `gold` with comments | fixed layout |
| `02_tables_from_contracts.sql` | One table per contract: types, `NOT NULL`, primary key (informational), comments | `contracts/*.odcs.yaml` |
| `03_classification_tags.sql` | Table tags (classification, domain, owner, steward, contract version) and column tags (`pii`, `glossary_term`) | contracts + glossary |
| `04_grants_from_policy.sql` | `USE CATALOG`, `USE SCHEMA` and `SELECT` grants per group, plus time-bound user grants | `governance/access_policy.yaml`, `users.yaml` |
| `05_column_masks.sql` | Masking functions and column masks: clear text only for the domain's owner and stewards | `access_policy.yaml` + `pii:` tags |

## Applying it in Databricks Free Edition

Product menus change; check the current Databricks documentation if a step looks different.

1. **Create a workspace** in Databricks Free Edition and open the SQL editor attached to a SQL warehouse.
2. **Create the groups** listed at the top of `04_grants_from_policy.sql` (for example
   `gov_operations_data_steward`) in the workspace's identity and access settings, and add yourself to the
   ones you want to test. The fictional `example.org` users do not exist: replace them with real test users or
   skip the user-level grants.
3. **Run the files in order**, `01` → `05`. Each statement is idempotent (`IF NOT EXISTS` / `CREATE OR REPLACE`)
   except grants, which are safe to repeat.
4. **Load data** (optional). Locally:
   ```bash
   make all
   python -m govkit export      # writes data/export/<layer>.<table>.parquet
   ```
   Upload the Parquet files to a Unity Catalog volume, then for each table:
   ```sql
   INSERT INTO governance_demo.gold.customer_value
   SELECT * FROM read_files('/Volumes/governance_demo/gold/landing/gold.customer_value.parquet');
   ```
5. **Verify the controls**:
   - `DESCRIBE TABLE EXTENDED governance_demo.gold.customer_value` shows comments, tags and the masks.
   - As a member of `gov_customer_data_consumer` only, `SELECT contact_email FROM governance_demo.gold.customer_value`
     returns masked values; as a member of `gov_customer_data_steward` it returns clear text.
   - As a member of `gov_customer_data_consumer`, selecting from `governance_demo.silver.technicians` is denied.

## Known gaps

- Bronze tables are not created: in Databricks they would be loaded with Auto Loader or `COPY INTO`.
- Expiring grants are not revoked automatically; the generated file lists the `REVOKE` statements to schedule.
- Quality rules are not ported to Databricks (expectations or Lakehouse Monitoring would be the next step).
