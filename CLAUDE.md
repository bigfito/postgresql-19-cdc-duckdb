# CLAUDE.md

## Plan de trabajo

El trabajo del laboratorio sigue [planning/PLAN.md](planning/PLAN.md). Las reglas comunes a todos los agentes están en [AGENTS.md](AGENTS.md); aplícalas también aquí.

## Consulta de documentación

1. **Context7 es la primera fuente.** Para cualquier duda sobre una librería, framework, herramienta o servicio (sintaxis, opciones de configuración, versiones, compatibilidad, ejemplos), consulta primero el servidor MCP de Context7: `resolve-library-id` y después `query-docs`.
2. **Internet es la segunda fuente.** Solo si Context7 no tiene la librería, no cubre la versión que usa el proyecto o no devuelve lo que se busca, recurre a la búsqueda web o a la documentación oficial en línea.
3. **Di de dónde salió cada dato.** Al reportar, distingue lo verificado en Context7 de lo verificado en otra fuente y de lo que no se pudo verificar.

Identificadores de Context7 ya resueltos para el stack de este proyecto (pueden cambiar; si alguno falla, vuelve a resolverlo):

| Componente | ID en Context7 |
|---|---|
| Apache Flink CDC | `/apache/flink-cdc` |
| Apache Flink | `/apache/flink` |
| Apache Iceberg | `/websites/iceberg_apache` |
| Apache Airflow | `/websites/airflow_apache` |
| Apache Superset | `/apache/superset` |
| DuckDB (también su cliente JDBC) | `/duckdb/duckdb-web` |
| Apache Spark y PySpark | `/websites/spark_apache` |
| Lanterna | `/mabe02/lanterna` |
| Apache Commons CSV | `/websites/commons_apache_proper_commons-csv` |
