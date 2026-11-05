# Example: a schema change that breaks a contract fails CI

**English** · [Español](../es/ejemplo-cambio-que-rompe.md)

This is a real run, reproduced by `tests/test_contracts.py::test_breaking_schema_change_fails_the_build`.

## The change

A developer renames a column in the gold SQL model, but does not touch the data contract
`contracts/gold.service_order_economics.odcs.yaml` (v2.0.0), which still promises `gross_margin`:

```diff
-    round(o.price - coalesce(l.actual_labor_cost, 0) - coalesce(m.actual_material_cost, 0), 2) AS gross_margin,
+    round(o.price - coalesce(l.actual_labor_cost, 0) - coalesce(m.actual_material_cost, 0), 2) AS margin_amount,
```

## What happens

`govkit run` checks each built table against its contract **before** running quality rules, and exits with code 1:

```text
  ✗ gold.service_order_economics: breaks its contract (2 schema violation(s)); quality rules skipped
  ✗ gold.customer_value: Binder Error: Table "e" does not have a column named "gross_margin"
  ✗ gold.site_monthly_kpis: Binder Error: Table "e" does not have a column named "gross_margin"
Run 20261104-172018-45a6b4 (as of 2026-10-31): FAILED
  - [error] gold.service_order_economics · contract_violation: column 'gross_margin' is declared in contract v2.0.0 but missing
  - [error] gold.service_order_economics · contract_violation: column 'margin_amount' exists in the data but is not declared in the contract
```

`govkit verify` (a step of `make all`, which CI runs on every push) also exits with code 1:

```text
  ✗ gold.service_order_economics       v2.0.0   schema violations=2 failed rules=0
  ✗ gold.customer_value                not built in this run (see run errors: upstream contract break?)
  ✗ gold.site_monthly_kpis             not built in this run (see run errors: upstream contract break?)
3 dataset(s) break their contract.
```

The rename would have silently broken the profitability dashboard and the key-account review downstream
(see `govkit lineage gold.service_order_economics.gross_margin --impact`). It never reaches `main`.

## How to make the change correctly

Under the contract's `changePolicy`, renaming a column is **breaking**. The legitimate path is:

1. Update the contract: rename the property and bump the version to **3.0.0** (major).
2. Get Data Owner approval (`raci.yaml` → `change_data_contract`, Accountable: Data Owner).
3. Announce the deprecation to consumers (`deprecationNoticeDays: 30`), or ship both columns during the notice period.

On pull requests CI also runs `govkit compat --base origin/main`, which compares every contract with the
target branch and fails if a breaking change ships without a major version bump:

```text
[ERROR] gold.service_order_economics: breaking change without a major version bump (2.0.0 -> 2.1.0): column 'gross_margin' removed or renamed
```
