# Registro de decisiones

[English](../DECISIONS.md) · **Español**

Cada decisión registra la elección, las alternativas y el porqué. La más reciente va al final. Los
identificadores coinciden con la versión en inglés, que es la fuente principal.

## D-001 · Mantener el motor Python + DuckDB en lugar de pasar a dbt
- **Contexto:** el plan sugería dbt-core + DuckDB solo si no había un stack elegido. El repositorio ya tenía un
  pipeline Python + DuckDB + sqlglot funcionando, con cuarentena, linaje e interfaz.
- **Decisión:** conservarlo. Las transformaciones siguen siendo archivos SQL (uno por modelo), portables a dbt o
  Databricks más adelante.
- **Por qué:** respetar el stack existente era una regla explícita, y un motor propio permite que la capa de
  gobierno (contratos, RACI, política de accesos) dirija el pipeline, que es el objetivo del proyecto.

## D-002 · Reiniciar el historial de git antes de la primera publicación
- **Contexto:** la única commit del prototipo nunca se subió y tenía identificadores en español y nombres reales
  de lugares y fabricantes en el generador sintético.
- **Decisión:** descartarla y reconstruir el historial fase por fase, en inglés.
- **Por qué:** la regla "solo datos públicos o sintéticos, nada real" también aplica al historial: un repositorio
  público expone cada commit.

## D-003 · Una empresa ficticia de operaciones como dominio de datos
- **Decisión:** una empresa ficticia de servicios de campo con tres dominios: `operations` (activos, técnicos,
  órdenes de servicio, horas), `supply_chain` (maestro de materiales, salidas de almacén, posición de inventario) y
  `customer` (cuentas de clientes y su valor). Sedes `Site North/South/East/West/Central`, fabricantes
  `OEM Alpha…Delta` y personas con nombres evidentemente inventados y correos `example.org`.
- **Por qué:** es lo bastante realista para ejercitar todos los controles (datos personales, costos
  confidenciales, datos maestros, referencias entre dominios) sin dejar duda de que es sintético.

## D-004 · Datos con semilla fija y defectos a propósito
- **Decisión:** semilla `42` y fecha de corte fija (`2026-10-31`), de modo que cada corrida sea idéntica byte a
  byte. Se inyectan defectos conocidos: nulos, duplicados, valores imposibles, huérfanos, dos formatos de fecha,
  costos desplazados un decimal y una columna con datos personales no declarada.
- **Por qué:** una demostración de gobierno solo convence si hay algo que atrapar, y la semilla fija hace que el
  reporte de calidad sea reproducible en la CI y en una revisión.

## D-005 · Paquete `govkit` y YAML de gobierno en `governance/`
- **Decisión:** paquete Python `govkit` (CLI `govkit`), gobierno como código en `governance/`, contratos en
  `contracts/`, modelos SQL en `models/` y registro de fuentes crudas en `models/sources.yaml`.
- **Por qué:** nombres cortos y una estructura de carpetas que refleja lo que un revisor busca.

## D-006 · Reglas de validación del RACI
- **Decisión:** exactamente un Accountable y al menos un Responsible por actividad; todo rol citado debe existir;
  la cadena de escalamiento no tiene ciclos y termina en un único rol (el Data Sponsor).
- **Por qué:** son las propiedades que hacen útil un RACI: una persona responde por el resultado, alguien hace el
  trabajo y todo escalamiento llega a alguna parte.

## D-007 · La documentación generada se versiona y se verifica
- **Decisión:** `govkit docs` genera `docs/generated/*.md` desde el YAML y los metadatos de la corrida; la CI la
  regenera y falla si hay diferencias (`make docs-check`).
- **Por qué:** se puede leer en GitHub sin ejecutar nada, y nunca se desalinea del YAML que realmente se aplica.

## D-008 · Un rol de gobierno principal por persona
- **Decisión:** cada usuario tiene un solo rol; la pertenencia al Consejo de Gobierno es un rol en sí mismo.
- **Por qué:** mantiene sin ambigüedad la verificación de mínimo privilegio. Soportar varios roles está en la hoja
  de ruta.

## D-009 · Los accesos aprovisionados se declaran y deben justificarse
- **Decisión:** `users.yaml` lista los accesos que cada persona tiene en realidad, como los mostraría una
  exportación del sistema de identidades. Cada uno necesita una base: `role` (debe caber en el rol) o `request`
  (ticket, aprobador, fechas de aprobación y de vencimiento). Cualquier otro caso es "acceso que ningún rol
  justifica" y hace fallar la CI.
- **Por qué:** así funciona una revisión de accesos real: se compara lo aprovisionado con lo que la política
  permite.

## D-010 · Reglas de las solicitudes de acceso
- **Decisión:** las excepciones vencen en máximo 90 días; los datos restringidos nunca se otorgan por solicitud;
  lo confidencial lo aprueba el Owner del dominio y lo interno, el Owner o el Steward; el aprobador debe gobernar
  el dominio y nunca puede ser quien solicita. En la CI el vencimiento se valida como duración, para que el
  resultado no dependa del calendario; en tiempo de ejecución (`access.can_read`) se usa la fecha real.
- **Por qué:** la segregación de funciones y las excepciones con vencimiento son los dos controles que un auditor
  revisa primero.

## D-011 · GRANTs compilados desde la política, en sintaxis PostgreSQL
- **Decisión:** `govkit docs` genera `docs/generated/access_grants.sql` (un grupo por rol y dominio; grants a
  usuarios solo para excepciones aprobadas). DuckDB no tiene GRANT, así que el SQL apunta a motores compatibles con
  PostgreSQL; la versión para Unity Catalog se genera en la fase 7.
- **Por qué:** los permisos tienen que salir de la política, nunca escribirse a mano.

## D-012 · Qué significan "circular" y "huérfano" en el glosario
- **Circular:** un término cuya definición contiene su propio nombre, o cualquier ciclo en el grafo
  `depends_on` con el que las métricas declaran de qué términos está hecha su fórmula.
- **Huérfano:** un término que no es la columna fuente de ningún modelo SQL ni el `businessName` de ninguna
  propiedad de un contrato. Todo término debe apuntar a datos reales.
- **Por qué:** son las dos fallas que vuelven inútil un glosario: definiciones que no explican nada y términos que
  nadie encuentra en los datos.

## D-013 · El glosario se publica dos veces
- **Decisión:** `docs/generated/glossary.md` (legible en GitHub, con anclas) y `docs/generated/glossary.html`,
  autocontenido y con buscador.
- **Por qué:** el Markdown es lo que abre un revisor en GitHub; el HTML es lo que usaría un usuario de negocio.

## D-014 · ODCS v3 para los contratos, con un vocabulario de reglas documentado
- **Decisión:** los contratos siguen Open Data Contract Standard v3. Las reglas de calidad mantienen la forma de
  ODCS (`type: library | sql`, `dimension`, `severity`); los nombres de las reglas de librería (`pattern`,
  `validValues`, `range`, `references`, `expression`, `tolerance`, `rowCount`) son propios de govkit y están en
  `src/govkit/contracts.py`. La clasificación y la política de cambios van en `customProperties`; las categorías de
  datos personales son tags `pii:<categoría>`; el vínculo con el glosario es `businessName`.
- **Por qué:** ODCS es neutral respecto del proveedor y se traslada a Databricks, Snowflake o dbt. Los model
  contracts de dbt no aplicaban porque el stack no usa dbt (D-001).

## D-015 · Lo que promete el contrato se vuelve regla ejecutable automáticamente
- **Decisión:** `required` → regla de completitud; `unique` o clave primaria simple → regla de unicidad; clave
  compuesta → verificación SQL de unicidad; SLA de `latency` → regla de oportunidad contra la fecha de corte.
- **Por qué:** se prueba exactamente lo que el contrato promete, sin un segundo lugar que mantener sincronizado.

## D-016 · La conformidad del esquema se revisa antes que las reglas de calidad
- **Decisión:** cada tabla construida se compara primero con su contrato (columna faltante, columna no declarada,
  tipo lógico). Si el esquema se rompe, sus reglas no se ejecutan y la corrida falla.
- **Por qué:** se descubrió al escribir la prueba del cambio que rompe: sobre una tabla mal formada, las reglas
  fallan con errores SQL confusos. Revisar la forma primero le da al desarrollador la causa real.

## D-017 · Silver bloquea filas malas, gold bloquea la publicación
- **Decisión:** en silver, las filas que fallan una regla `error` van a `quarantine.<tabla>` y la corrida
  continúa. En gold, una regla `error` fallida o cualquier violación de esquema hace fallar `govkit verify`.
- **Por qué:** las filas malas en la fuente son esperables y las gestionan los stewards; un KPI publicado roto no
  es aceptable.

## D-018 · Un hallazgo abierto se deja a propósito
- **Decisión:** `labor_entries.approver_email` contiene correos pero no está marcado como dato personal. El
  pipeline lo reporta como hallazgo de severidad alta en cada corrida.
- **Por qué:** muestra que el descubrimiento atrapa lo que las declaraciones omiten. Corregirlo es una línea en el
  contrato (`tags: ["pii:email"]`) más una revisión de clasificación; está en la hoja de ruta.

## D-019 · Seis dimensiones de calidad y cómo se mide cada una
- **Decisión:** completitud (`required`, conteos), unicidad (claves), validez (patrones, dominios, rangos),
  consistencia (integridad referencial, lógica entre columnas, fórmulas), exactitud (concordancia con una fuente
  de referencia: costo de salida contra el maestro de materiales con ±25 %, totales gold conciliados con silver) y
  oportunidad (SLA de latencia contra la fecha de corte).
- **Por qué:** la exactitud es la dimensión que más proyectos omiten porque necesita una referencia; usar los datos
  maestros y la conciliación entre capas la vuelve medible sin fuentes externas.

## D-020 · Trazabilidad del glosario a las reglas
- **Decisión:** cada término del glosario lista las reglas de contrato que lo protegen; el reporte de calidad
  muestra, por término, cuántas reglas aplican y su tasa de cumplimiento. Las fórmulas de las métricas se prueban
  (`margin_definition_holds` y las reglas de conciliación).
- **Por qué:** cierra el ciclo definición de negocio → regla ejecutable → resultado medido.

## D-021 · Reporte en cada corrida y copia publicada en docs
- **Decisión:** `govkit run` escribe `reports/quality_report.{md,json}` (ignorado por git, uno por corrida).
  `govkit docs` publica el de la última corrida en `docs/generated/quality_report.md`. No lleva marcas de tiempo
  ni identificadores de corrida, así que es reproducible y la CI lo verifica como el resto.
- **Por qué:** el revisor ve una salida real en GitHub y la CI prueba que está al día.

## D-022 · Linaje en Mermaid generado desde el SQL
- **Decisión:** el linaje por dataset se emite como diagrama Mermaid (GitHub lo dibuja sin herramientas
  adicionales), con una tabla a nivel de columna para cada columna gold; los consumidores salen de
  `models/exposures.yaml`.
- **Por qué:** no requiere herramientas extra para verlo y no puede desalinearse, porque se calcula del SQL en
  cada corrida.

## D-023 · La autoevaluación de madurez se respalda con evidencia y es conservadora
- **Decisión:** escala propia de 1 a 5 (ad hoc, documentado, definido y aplicado, medido, optimizado) aplicada solo
  a este repositorio. Cada puntaje cita archivos como evidencia; la CI falla si falta un archivo, y todo puntaje de
  3 o más necesita al menos tres evidencias. Ninguna área tiene 4: todavía no hay seguimiento en el tiempo contra
  metas.
- **Por qué:** una autoevaluación solo es creíble si se puede refutar y si peca de baja.

## D-024 · La interfaz Streamlit del prototipo no se portó
- **Decisión:** el prototipo tenía una aplicación Streamlit de 8 páginas. Se retiró al pasar a inglés y no se
  reconstruyó; las piezas de gobierno se publican como Markdown/HTML generados.
- **Por qué:** el encargo es un programa que se verifica solo; una interfaz suma superficie sin sumar un control.
  Publicar en un catálogo real es el mejor siguiente paso y está en la hoja de ruta.

## D-025 · SQL de Unity Catalog generado, nunca ejecutado aquí
- **Decisión:** `govkit deploy` compila catálogo, esquemas, tablas (tipos, NOT NULL, claves primarias
  informativas, comentarios), tags (clasificación, dominio, Owner, Steward, `pii`, `glossary_term`), grants por
  grupo y máscaras de columna desde el mismo YAML. Cada archivo empieza con "NOT EXECUTED IN THIS REPO" y la CI
  verifica que estén al día.
- **Por qué:** este entorno no tiene acceso a Databricks y no se deben pedir credenciales. Generarlo desde la
  política hace que la configuración de la plataforma derive del gobierno y no sea una copia paralela.
- **Máscaras:** texto claro solo para los grupos cuyo rol tiene `unmasked_pii: true` y solo en su dominio, con
  `is_account_group_member`; la compensación numérica se enmascara como NULL.

## D-026 · Nombre del repositorio
- **Decisión:** `data-governance-as-code`. La carpeta local de trabajo conservó el nombre del prototipo; no es
  visible en el repositorio.

## D-027 · Documentación bilingüe, con el inglés como fuente principal
- **Contexto:** el encargo original pedía todo lo visible en inglés; luego el dueño del proyecto pidió también
  español.
- **Decisión:** `README.md` (inglés) y `README.es.md` (español) se enlazan entre sí. Los documentos narrativos
  clave tienen versión en español en `docs/es/`. El código, las claves del YAML, los nombres de archivo de
  gobierno, la documentación generada y el vocabulario de los estándares (ODCS, RACI, DAMA-DMBOK2) siguen en
  inglés, que es la fuente principal. Una prueba verifica que todo enlace relativo de todo archivo Markdown
  resuelva, para que las traducciones no apunten a archivos inexistentes.
- **Por qué:** llega a revisores locales e internacionales sin mantener dos bases de código; los documentos
  generados quedan en un solo idioma para que la CI pueda seguir verificándolos.

## D-028 · Orden estándar del repositorio
- **Decisión:** se agregan `CHANGELOG.md` (Keep a Changelog, versionado semántico), `CONTRIBUTING.md`,
  `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CODEOWNERS`, una plantilla de pull request con lista de verificación de
  gobierno, formularios de issues para los flujos de `raci.yaml` (término del glosario, incidente de calidad,
  solicitud de acceso, cambio de contrato), `.editorconfig`, configuración de pre-commit y CI en Python 3.10 y 3.12.
- **Por qué:** son las primeras señales con las que se juzga un repositorio de portafolio, y los formularios
  convierten las actividades del RACI en un proceso real de entrada.
