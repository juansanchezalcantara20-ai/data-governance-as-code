# Ejemplo: un cambio de esquema que rompe un contrato hace fallar la CI

[English](../examples/breaking-change.md) · **Español**

Es una corrida real, reproducida por la prueba
`tests/test_contracts.py::test_breaking_schema_change_fails_the_build`.

## El cambio

Un desarrollador renombra una columna en el modelo SQL de gold, pero no toca el contrato de datos
`contracts/gold.service_order_economics.odcs.yaml` (v2.0.0), que sigue prometiendo `gross_margin`:

```diff
-    round(o.price - coalesce(l.actual_labor_cost, 0) - coalesce(m.actual_material_cost, 0), 2) AS gross_margin,
+    round(o.price - coalesce(l.actual_labor_cost, 0) - coalesce(m.actual_material_cost, 0), 2) AS margin_amount,
```

## Qué pasa

`govkit run` compara cada tabla construida con su contrato **antes** de ejecutar las reglas de calidad, y termina
con código 1 (la salida de la herramienta está en inglés):

```text
  ✗ gold.service_order_economics: breaks its contract (2 schema violation(s)); quality rules skipped
  ✗ gold.customer_value: Binder Error: Table "e" does not have a column named "gross_margin"
  ✗ gold.site_monthly_kpis: Binder Error: Table "e" does not have a column named "gross_margin"
Run 20261104-172018-45a6b4 (as of 2026-10-31): FAILED
  - [error] gold.service_order_economics · contract_violation: column 'gross_margin' is declared in contract v2.0.0 but missing
  - [error] gold.service_order_economics · contract_violation: column 'margin_amount' exists in the data but is not declared in the contract
```

`govkit verify`, que es un paso de `make all` y la CI lo corre en cada push, también termina con código 1:

```text
  ✗ gold.service_order_economics       v2.0.0   schema violations=2 failed rules=0
  ✗ gold.customer_value                not built in this run (see run errors: upstream contract break?)
  ✗ gold.site_monthly_kpis             not built in this run (see run errors: upstream contract break?)
3 dataset(s) break their contract.
```

El renombre habría roto en silencio el tablero de rentabilidad y la revisión de cuentas clave, que están aguas
abajo (ver `govkit lineage gold.service_order_economics.gross_margin --impact`). Nunca llega a `main`.

## Cómo hacer el cambio correctamente

Según la `changePolicy` del contrato, renombrar una columna es un cambio **que rompe**. El camino legítimo es:

1. Actualizar el contrato: renombrar la propiedad y subir la versión a **3.0.0** (mayor).
2. Obtener la aprobación del Data Owner (`raci.yaml` → `change_data_contract`, Accountable: Data Owner).
3. Avisar a los consumidores con 30 días de anticipación (`deprecationNoticeDays: 30`), o publicar ambas columnas
   durante ese periodo.

En los pull requests la CI corre además `govkit compat --base origin/main`, que compara cada contrato con la rama
destino y falla si un cambio que rompe se publica sin subir la versión mayor:

```text
[ERROR] gold.service_order_economics: breaking change without a major version bump (2.0.0 -> 2.1.0): column 'gross_margin' removed or renamed
```
