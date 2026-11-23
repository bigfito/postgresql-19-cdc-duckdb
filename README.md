# 🎬 ElastiFlix PostgreSQL CDC Lakehouse Lab

> 🟦 **CDC** · 🟪 **Lakehouse** · 🟩 **Medallion Architecture** · 🟨 **SCD Type 2** · 🟥 **BI**
>
> **Laboratorio local de ingeniería de datos end-to-end**: PostgreSQL 19 → Flink CDC → Apache Iceberg (Bronze, Silver, Gold) → PySpark + Airflow → DuckDB → Superset, todo en contenedores y con un único `docker compose up`.

## 1. Propósito

Este repositorio contiene **ElastiFlix CDC Lakehouse Lab**, un laboratorio reproducible que sigue un cambio de datos desde que nace en una base transaccional hasta que aparece en un dashboard.

Un simulador en Java 25 lee un catálogo de 6,899 películas, repartido en un CSV por tabla, y ejecuta transacciones reales (`INSERT`, `UPDATE`, `DELETE`) sobre PostgreSQL 19. Apache Flink CDC captura esos cambios desde el WAL y los replica en Apache Iceberg. Dos jobs PySpark, orquestados por Apache Airflow, construyen un modelo dimensional con historial (SCD Type 2) y después productos analíticos listos para BI. Apache Superset los consulta a través de DuckDB.

El objetivo es demostrativo: que un revisor externo pueda clonar el proyecto, levantarlo y observar cada etapa.

> 🎨 **Leyenda visual:** 🥉 Bronze = réplica operacional; 🥈 Silver = modelo dimensional histórico; 🥇 Gold = serving analítico; 🟪 infraestructura compartida; 🟥 consumo BI.

## 2. 🚦 Estado del proyecto

> ⚠️ **Fase de diseño.** Todavía no hay código ejecutable: no existe `docker-compose.yml` ni ninguno de los servicios. El repositorio contiene hoy el documento de diseño y sus diagramas.

| Elemento | Estado |
|---|---|
| Documento de diseño ([`lab-design/LAB-DESIGN.md`](lab-design/LAB-DESIGN.md)) | ✅ Revisión 6 |
| Diagramas y bocetos ([`lab-design/diagrams/`](lab-design/diagrams/)) | ✅ Diez, generados con Archify |
| Versiones del stack | ✅ Última estable compatible de cada componente; verificadas contra Docker Hub, Maven Central y PyPI |
| Imágenes base en Docker Hub | ✅ Las diez existen para `amd64` y `arm64` |
| Estructura de directorios del proyecto | ✅ Creada (vacía) |
| Validaciones de compatibilidad entre componentes | ✅ 12 de 12 superadas. Resultados en el [documento de decisiones y validaciones](lab-design/DECISIONS-AND-VALIDATIONS.md#2-validaciones) |
| Dataset de entrada: 20 CSV en [`raw_data/`](raw_data/), uno por tabla | ✅ Definitivo: 6,899 películas sintéticas, 438,925 filas y 24.5 MB, con su script generador y su [README](raw_data/README.md) |
| Implementación (simulador, DDL, pipeline CDC, jobs, DAG, dashboards) | ⏳ Pendiente; ver el [plan de trabajo](planning/PLAN.md) |

## 3. 🗺️ Arquitectura

![Arquitectura end-to-end del laboratorio ElastiFlix: de los CSV a Superset pasando por PostgreSQL, Flink CDC, las tres capas Iceberg, PySpark, Airflow y DuckDB](lab-design/diagrams/lab-architecture.svg)

> 🔍 **Cómo leerlo:** la columna central es el camino del dato, de arriba abajo. La línea punteada que va del Event Simulator a Bronze no forma parte de ese camino: es la consulta de solo lectura con la que el simulador comprueba que cada cambio llegó. Airflow (izquierda) solo lanza los dos jobs PySpark. Las tres capas quedan registradas en el Iceberg REST Catalog y sus archivos viven en RustFS (derecha); Flink, Spark y DuckDB resuelven las tablas ahí.

### Flujo principal

**📄 CSV → ☕ Java → 🐘 PostgreSQL → 🌊 Flink CDC → 🥉 Bronze → ⚡ PySpark → 🥈 Silver → ⚡ PySpark → 🥇 Gold → 🦆 DuckDB → 📊 Superset**

### Ideas clave del diseño

- 🌊 **CDC real, no carga batch.** El simulador escribe transacción por transacción y Flink CDC lee el WAL lógico de forma continua.
- 🥉 **Bronze conserva los borrados.** Cada tabla es un espejo por clave primaria con dos columnas técnicas (`cdc_op_type`, `cdc_op_ts`); un `DELETE` queda como tombstone en lugar de desaparecer.
- 🥈 **Historial donde aporta.** SCD Type 2 en las dimensiones cuyos atributos cambian (`dim_movie`, `dim_collection`, `dim_keyword`); el resto son Tipo 1.
- 🥇 **Gold simple para BI.** Tablas planas que se recargan completas en cada corrida.
- 🦆 **DuckDB embebido.** No es un servicio de red: corre dentro del contenedor de Superset y lee Gold directamente desde Iceberg.
- 🧭 **Un catálogo, un almacenamiento.** Flink, Spark y DuckDB comparten el Iceberg REST Catalog y RustFS (`s3://warehouse/`).

## 4. 🧰 Software Stack

| Componente | Versión | Rol | Propósito en el laboratorio |
|---|---:|---|---|
| PostgreSQL | **19.0** | Base operacional y logical replication | Hacer de sistema transaccional real: es el origen cuyos cambios se capturan desde el WAL |
| Java | **25** | Event Simulator | Mostrar una aplicación que genera transacciones de verdad, en lugar de una carga por lotes |
| Apache Flink | **2.2.1** | Runtime de streaming | Mantener un job de streaming siempre encendido, con checkpoints y recuperación ante fallos |
| Apache Flink CDC | **3.7.0** | PostgreSQL CDC → Iceberg | Capturar cada INSERT, UPDATE y DELETE sin escribir código: el pipeline es un archivo YAML |
| Apache Iceberg | **1.10.2** en Flink · **1.12.0** en Spark | Formato de tablas del lakehouse | Guardar las tres capas como tablas transaccionales, con upsert, `MERGE` y snapshots |
| Apache Spark / PySpark | **4.1.4** | Bronze → Silver → Gold | Transformar por lotes: construir el modelo dimensional con historial y los productos Gold |
| Python | **3.12** | Intérprete común de Airflow, Spark y Superset | Evitar que PySpark falle porque el driver y los ejecutores usan versiones distintas |
| Apache Airflow | **3.4.0** | Orquestación de los jobs PySpark | Encadenar, validar y reintentar los jobs por lotes, y dejar visible cada corrida |
| DuckDB | **1.5.6** | SQL/query engine embebido | Consultar Gold con SQL sin levantar un motor de consultas aparte |
| Apache Superset | **6.1.0** | BI y dashboards | Presentar el resultado final: dashboards construidos sobre Gold |
| RustFS | **1.0.6** | Object storage S3-compatible | Sustituir a un servicio S3 de nube, para que todo corra en la máquina local |
| Iceberg REST Catalog | **1.10.1** | Catálogo compartido | Dar a Flink, Spark y DuckDB un único registro de tablas |
| Docker Compose | **v2 o posterior** | Runtime del laboratorio | Levantar todo el laboratorio con un solo comando reproducible |

> ℹ️ Cada componente usa la versión estable más reciente que el resto del stack admite, y toda imagen base está publicada en Docker Hub. Cuatro quedan por debajo de la última publicada por compatibilidad: Flink 2.2.1 (Flink CDC 3.7 no soporta Flink 2.3), Spark 4.1.4 (Iceberg no publica runtime para Spark 4.2 ni 4.3), Iceberg 1.10.2 en Flink (línea contra la que se compila Flink CDC 3.7.0) y DuckDB 1.5.6 (Superset 6.1.0 exige `duckdb<2`). El razonamiento completo y la tabla de imágenes están en la [sección 3 del diseño](lab-design/LAB-DESIGN.md#3--software-stack).

## 5. 🥉🥈🥇 Capas de datos

![Linaje de datos por capa: CSV, tablas operacionales de PostgreSQL, tablas espejo de Bronze, dimensiones, hechos y bridges de Silver, productos Gold y consumo en Superset](lab-design/diagrams/medallion-dataflow.svg)

| Capa | Escribe | Lee | Contenido |
|---|---|---|---|
| 🐘 PostgreSQL `catalog` | Event Simulator | Flink CDC | 20 tablas normalizadas |
| 🥉 Bronze | Flink CDC | `bronze_to_silver.py` | 20 tablas espejo + columnas CDC |
| 🥈 Silver | `bronze_to_silver.py` | `silver_to_gold.py` | 14 dimensiones, 2 hechos, 6 bridges |
| 🥇 Gold | `silver_to_gold.py` | DuckDB (Superset) | 7 productos analíticos |

## 6. 📁 Estructura del repositorio

Contenido actual:

```text
postgresql-19-cdc-duckdb/
|
|-- .gitattributes
|-- .gitignore
|-- AGENTS.md
|-- CLAUDE.md
|-- README.md
|-- planning/
|   |-- PLAN.md
|   `-- update_progress.py
|-- (esqueleto de directorios de los servicios, ver abajo)
`-- lab-design/
    |-- LAB-DESIGN.md
    |-- DECISIONS-AND-VALIDATIONS.md
    `-- diagrams/
        |-- lab-architecture.{json,html,svg}
        |-- medallion-dataflow.{json,html,svg}
        |-- operational-erd.{json,html,svg}
        |-- airflow-medallion-dag.{json,html,svg}
        |-- compose-startup-order.{json,html,svg}
        |-- plan-phases.{json,html,svg}
        |-- simulator-console.{json,html,svg}
        |-- superset-serving-path.{json,html,svg}
        |-- quality-by-layer.{json,html,svg}
        `-- end-to-end-change-path.{json,html,svg}
```

Esqueleto del proyecto (un directorio por servicio, con sus volúmenes dentro). Los directorios ya existen. `raw_data/` contiene el dataset; los demás están vacíos, con un `.gitkeep` cada uno. `docker-compose.yml`, `.env.example` y el contenido de cada servicio están pendientes. El detalle de subdirectorios está en la [sección 7 del diseño](lab-design/LAB-DESIGN.md#7--estructura-propuesta-del-repositorio).

```text
postgresql-19-cdc-duckdb/
|-- docker-compose.yml
|-- .env.example
|-- raw_data/          dataset de entrada: un CSV por tabla
|-- java-simulator/    Event Simulator (Java 25)
|-- postgresql/        DDL, roles y publicación
|-- metadata-db/       metadatos de Airflow y Superset
|-- flink/             pipeline CDC y checkpoints
|-- iceberg/           Iceberg REST Catalog
|-- rustfs/            object storage
|-- pyspark/           jobs y datos de referencia
|-- airflow/           DAG elastiflix_medallion
|-- duckdb/            SQL de inicialización y CLI opcional
`-- superset/          configuración y dashboards
```

## 7. ✅ Requisitos

- 🐳 Docker Engine con Docker Compose v2 o posterior. En Windows, Docker Desktop con el backend WSL 2.
- CPU x86_64/amd64. El laboratorio se construye y se valida en un solo equipo con Windows 11.
- En un Mac con Apple Silicon no está probado: las imágenes base existen para `arm64`, pero ninguna validación se ha ejecutado ahí. Los puntos a revisar están en la sección 2.2 del [diseño](lab-design/LAB-DESIGN.md).
- Recomendado: **8 CPU, 16 GB RAM y al menos 30 GB libres**.
- Acceso a Internet durante el primer build. El runtime no depende de servicios cloud externos.

## 8. ▶️ Ejecución

Cuando la implementación esté completa, un único comando levantará el laboratorio:

```bash
docker compose up -d --build
```

Ese comando también ejecutará los jobs de preparación (bucket, namespaces, envío del pipeline CDC, metadatos de Airflow y Superset), sin pasos manuales intermedios.

> ⚠️ Hoy este comando **no funciona**: el `docker-compose.yml` todavía no existe (ver [Estado del proyecto](#2--estado-del-proyecto)).

Flujo demostrativo esperado:

1. Arranca el stack; PostgreSQL tiene el esquema pero no las películas.
2. Flink CDC queda corriendo y el simulador empieza a insertar.
3. Las filas llegan a PostgreSQL y, segundos después, a Bronze.
4. El simulador genera `UPDATE` y `DELETE`; se reflejan por CDC.
5. Airflow ejecuta `bronze_to_silver` y luego `silver_to_gold`.
6. DuckDB consulta Gold y Superset muestra los dashboards.

## 9. 🚀 Hoja de ruta

El trabajo está dividido en 13 fases, de F0 a F12. Las actividades de cada una y el avance, por fase y global, están en el **[plan de trabajo](planning/PLAN.md)**.

| Fases | Contenido |
|---|---|
| F0 y F1 | Diseño, validaciones previas y dataset de entrada |
| F2 a F5 | Base del proyecto, PostgreSQL, almacenamiento, catálogo y pipeline CDC hasta Bronze |
| F6 | Event Simulator en Java 25 |
| F7 a F9 | Silver, Gold y orquestación con Airflow |
| F10 | DuckDB y Superset |
| F11 y F12 | Prueba de extremo a extremo, documentación y cierre |

## 10. 📚 Documentación

| Documento | Contenido |
|---|---|
| [`lab-design/LAB-DESIGN.md`](lab-design/LAB-DESIGN.md) | Diseño completo: requisitos, stack, modelos de datos, pipeline, despliegue y registro de cambios |
| [`lab-design/DECISIONS-AND-VALIDATIONS.md`](lab-design/DECISIONS-AND-VALIDATIONS.md) | Decisiones vigentes, abiertas y descartadas; validaciones con sus resultados; registro de cambios |
| [`planning/PLAN.md`](planning/PLAN.md) | Plan de actividades por fases, tablero de avance y bitácora |
| [`AGENTS.md`](AGENTS.md) | Reglas comunes para los agentes de programación que trabajen en el repositorio |
| [Arquitectura](lab-design/diagrams/lab-architecture.svg) | Componentes y camino del dato |
| [Linaje por capa](lab-design/diagrams/medallion-dataflow.svg) | Qué pasa de una capa a la siguiente |
| [Modelo operacional](lab-design/diagrams/operational-erd.svg) | ERD de las 20 tablas del esquema `catalog` |
| [DAG de Airflow](lab-design/diagrams/airflow-medallion-dag.svg) | Tareas, jobs y capas que tocan |
| [Orden de arranque](lab-design/diagrams/compose-startup-order.svg) | Dependencias entre servicios de Docker Compose |
| [Fases del plan](lab-design/diagrams/plan-phases.svg) | Dependencias entre las 13 fases y camino más largo |
| [Consola del simulador](lab-design/diagrams/simulator-console.svg) | Boceto de la pantalla del Event Simulator |
| [Ruta de consumo](lab-design/diagrams/superset-serving-path.svg) | De Superset a los archivos de Gold en RustFS |
| [Calidad por capa](lab-design/diagrams/quality-by-layer.svg) | Responsabilidad de cada capa sobre el dato |
| [Recorrido de un cambio](lab-design/diagrams/end-to-end-change-path.svg) | Los once pasos del criterio de éxito |

> 🔍 Cada diagrama tiene también una versión interactiva `.html` y su fuente `.json` en [`lab-design/diagrams/`](lab-design/diagrams/). Para explorarla, descarga el `.html` y ábrelo en un navegador; GitHub muestra su código en lugar de renderizarlo. Los diagramas se generan con [Archify](https://github.com/tt-a1i/archify).
