# Despliegue en Unity Catalog — NO EJECUTADO EN ESTE REPOSITORIO

[English](../../deploy/unity_catalog/README.md) · **Español**

> ⚠️ **No ejecutado en este repositorio.** Los archivos SQL de `deploy/unity_catalog/` los *genera*
> `govkit deploy` (también `govkit docs`) a partir del mismo YAML que valida la CI. **No** se han corrido en un
> workspace de Databricks. Su sintaxis solo se revisó con el parser del dialecto Databricks de sqlglot, que no
> modela `SET TAGS`, `SET MASK` ni `GRANT USE CATALOG`. Revísalos antes de aplicarlos.

| Archivo | Qué hace | Se genera desde |
|---|---|---|
| `01_catalog_and_schemas.sql` | Catálogo `governance_demo` y esquemas `bronze`, `silver` y `gold` con comentarios | estructura fija |
| `02_tables_from_contracts.sql` | Una tabla por contrato: tipos, `NOT NULL`, clave primaria (informativa) y comentarios | `contracts/*.odcs.yaml` |
| `03_classification_tags.sql` | Tags de tabla (clasificación, dominio, Owner, Steward, versión del contrato) y de columna (`pii`, `glossary_term`) | contratos + glosario |
| `04_grants_from_policy.sql` | Grants `USE CATALOG`, `USE SCHEMA` y `SELECT` por grupo, más los grants temporales a usuarios | `governance/access_policy.yaml`, `users.yaml` |
| `05_column_masks.sql` | Funciones y máscaras de columna: texto claro solo para el Owner y los Stewards del dominio | `access_policy.yaml` + tags `pii:` |

## Cómo aplicarlo en Databricks Free Edition

Los menús del producto cambian; si un paso se ve distinto, revisa la documentación vigente de Databricks.

1. **Crea un workspace** en Databricks Free Edition y abre el editor SQL conectado a un SQL warehouse.
2. **Crea los grupos** que aparecen al inicio de `04_grants_from_policy.sql` (por ejemplo
   `gov_operations_data_steward`) en la configuración de identidades y accesos del workspace, y agrégate a los que
   quieras probar. Los usuarios ficticios `example.org` no existen: reemplázalos por usuarios de prueba reales u
   omite los grants a usuarios.
3. **Ejecuta los archivos en orden**, de `01` a `05`. Cada sentencia se puede repetir sin problema (`IF NOT EXISTS`
   / `CREATE OR REPLACE`), y los grants también.
4. **Carga los datos** (opcional). En tu máquina:
   ```bash
   make all
   python -m govkit export      # escribe data/export/<capa>.<tabla>.parquet
   ```
   Sube los Parquet a un volumen de Unity Catalog y, para cada tabla:
   ```sql
   INSERT INTO governance_demo.gold.customer_value
   SELECT * FROM read_files('/Volumes/governance_demo/gold/landing/gold.customer_value.parquet');
   ```
5. **Verifica los controles**:
   - `DESCRIBE TABLE EXTENDED governance_demo.gold.customer_value` muestra comentarios, tags y máscaras.
   - Siendo solo miembro de `gov_customer_data_consumer`,
     `SELECT contact_email FROM governance_demo.gold.customer_value` devuelve valores enmascarados; como miembro de
     `gov_customer_data_steward` los devuelve en claro.
   - Siendo miembro de `gov_customer_data_consumer`, leer `governance_demo.silver.technicians` está denegado.

## Brechas conocidas

- No se crean tablas bronze: en Databricks se cargarían con Auto Loader o `COPY INTO`.
- Los grants que vencen no se revocan solos; el archivo generado lista las sentencias `REVOKE` que hay que programar.
- Las reglas de calidad no se portan a Databricks (el siguiente paso serían expectations o Lakehouse Monitoring).
