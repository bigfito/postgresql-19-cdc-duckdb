# 🎬 ElastiFlix PostgreSQL CDC Lakehouse Lab

> 🟦 **CDC** · 🟪 **Lakehouse** · 🟩 **Medallion Architecture** · 🟨 **SCD Type 2** · 🟥 **BI**
>
> **Laboratorio local de ingeniería de datos end-to-end**: PostgreSQL 19 → Flink CDC → Apache Iceberg (Bronze, Silver, Gold) → PySpark + Airflow → DuckDB → Superset, todo en contenedores y con un único `docker compose up`.

## 1. Propósito

Este repositorio contiene **ElastiFlix CDC Lakehouse Lab**, un laboratorio reproducible que sigue un cambio de datos desde que nace en una base transaccional hasta que aparece en un dashboard.

Un simulador en Java 25 lee un catálogo de 6,899 películas y ejecuta transacciones reales (`INSERT`, `UPDATE`, `DELETE`) sobre PostgreSQL 19. Apache Flink CDC captura esos cambios desde el WAL y los replica en Apache Iceberg. Dos jobs PySpark, orquestados por Apache Airflow, construyen un modelo dimensional con historial (SCD Type 2) y después productos analíticos listos para BI. Apache Superset los consulta a través de DuckDB.

El objetivo es demostrativo: que un revisor externo pueda clonar el proyecto, levantarlo y observar cada etapa.

> 🎨 **Leyenda visual:** 🥉 Bronze = réplica operacional; 🥈 Silver = modelo dimensional histórico; 🥇 Gold = serving analítico; 🟪 infraestructura compartida; 🟥 consumo BI.

## 2. 🚦 Estado del proyecto

> ⚠️ **Fase de diseño.** Todavía no hay código ejecutable: no existe `docker-compose.yml` ni ninguno de los servicios. El repositorio contiene hoy el documento de diseño y sus diagramas.

| Elemento | Estado |
|---|---|
| Documento de diseño ([`lab-design/LAB-DESIGN.md`](lab-design/LAB-DESIGN.md)) | ✅ Revisión 3 |
| Diagramas de arquitectura, linaje, ERD, DAG y arranque ([`lab-design/diagrams/`](lab-design/diagrams/)) | ✅ Generados |
| Versiones del stack | ✅ Última estable compatible de cada componente; verificadas contra Docker Hub, Maven Central y PyPI |
| Imágenes base en Docker Hub | ✅ Las diez existen para `amd64` y `arm64` |
| Estructura de directorios del proyecto | ✅ Creada (vacía) |
| Validaciones de compatibilidad entre componentes | ⏳ 1 de 9 superada: Flink CDC 3.7.0 lee el WAL de PostgreSQL 19.0 |
| Dataset `raw_data/elastiflix.csv` | ⏳ Pendiente de incorporar |
| Implementación (simulador, DDL, pipeline CDC, jobs, DAG, dashboards) | ⏳ Pendiente |

## 3. 🗺️ Arquitectura

![Arquitectura end-to-end del laboratorio ElastiFlix: del CSV a Superset pasando por PostgreSQL, Flink CDC, las tres capas Iceberg, PySpark, Airflow y DuckDB](lab-design/diagrams/lab-architecture.svg)

> 🔍 **Cómo leerlo:** la columna central es el camino del dato, de arriba abajo. Airflow (izquierda) solo lanza los dos jobs PySpark. Las tres capas quedan registradas en el Iceberg REST Catalog y sus archivos viven en RustFS (derecha); Flink, Spark y DuckDB resuelven las tablas ahí.

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

| Componente | Versión | Rol |
|---|---:|---|
| PostgreSQL | **19.0** | Base operacional y logical replication |
| Java | **25** | Event Simulator |
| Apache Flink | **2.2.1** | Runtime de streaming |
| Apache Flink CDC | **3.7.0** | PostgreSQL CDC → Iceberg |
| Apache Iceberg | **1.10.2** en Flink · **1.12.0** en Spark | Formato de tablas del lakehouse |
| Apache Spark / PySpark | **4.1.4** | Bronze → Silver → Gold |
| Python | **3.12** | Intérprete común de Airflow, Spark y Superset |
| Apache Airflow | **3.4.0** | Orquestación de los jobs PySpark |
| DuckDB | **1.5.6** | SQL/query engine embebido |
| Apache Superset | **6.1.0** | BI y dashboards |
| RustFS | **1.0.6** | Object storage S3-compatible |
| Iceberg REST Catalog | **1.10.1** | Catálogo compartido |
| Docker Compose | **v2 o posterior** | Runtime del laboratorio |

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
|-- CLAUDE.md
|-- README.md
|-- (esqueleto de directorios de los servicios, ver abajo)
`-- lab-design/
    |-- LAB-DESIGN.md
    `-- diagrams/
        |-- lab-architecture.{json,html,svg}
        |-- medallion-dataflow.{json,html,svg}
        |-- operational-erd.{json,html,svg}
        |-- airflow-medallion-dag.{json,html,svg}
        `-- compose-startup-order.{json,html,svg}
```

Esqueleto del proyecto (un directorio por servicio, con sus volúmenes dentro). Los directorios ya existen, vacíos y con un `.gitkeep` cada uno; `docker-compose.yml`, `.env.example` y el contenido de cada servicio están pendientes. El detalle de subdirectorios está en la [sección 7 del diseño](lab-design/LAB-DESIGN.md#7--estructura-propuesta-del-repositorio).

```text
postgresql-19-cdc-duckdb/
|-- docker-compose.yml
|-- .env.example
|-- raw_data/          dataset fuente
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
- CPU x86_64/amd64 o ARM64.
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

1. **Fase 0: validaciones previas.** Nueve pruebas cortas de compatibilidad entre componentes. La primera, que Flink CDC 3.7.0 lea el WAL de PostgreSQL 19.0, ya pasó, así que no hace falta el respaldo a PostgreSQL 18. Detalle y resultados en la [sección 46 del diseño](lab-design/LAB-DESIGN.md#46--validaciones-previas-fase-0).
2. Preparar y perfilar el CSV de 6,899 películas.
3. DDL de PostgreSQL y logical replication.
4. Java Event Simulator.
5. RustFS, Iceberg REST Catalog y pipeline Flink CDC → Bronze.
6. `bronze_to_silver.py` (dimensiones, SCD2, hechos y bridges) y `silver_to_gold.py`.
7. DAG de Airflow.
8. DuckDB y Superset; dashboards y KPIs.
9. Prueba end-to-end con `INSERT`, `UPDATE` y `DELETE`.

## 10. 📚 Documentación

| Documento | Contenido |
|---|---|
| [`lab-design/LAB-DESIGN.md`](lab-design/LAB-DESIGN.md) | Diseño completo: requisitos, stack, modelos de datos, pipeline, despliegue y registro de cambios |
| [Arquitectura](lab-design/diagrams/lab-architecture.svg) | Componentes y camino del dato |
| [Linaje por capa](lab-design/diagrams/medallion-dataflow.svg) | Qué pasa de una capa a la siguiente |
| [Modelo operacional](lab-design/diagrams/operational-erd.svg) | ERD de las 20 tablas del esquema `catalog` |
| [DAG de Airflow](lab-design/diagrams/airflow-medallion-dag.svg) | Tareas, jobs y capas que tocan |
| [Orden de arranque](lab-design/diagrams/compose-startup-order.svg) | Dependencias entre servicios de Docker Compose |

> 🔍 Cada diagrama tiene también una versión interactiva `.html` y su fuente `.json` en [`lab-design/diagrams/`](lab-design/diagrams/). Para explorarla, descarga el `.html` y ábrelo en un navegador; GitHub muestra su código en lugar de renderizarlo. Los diagramas se generan con [Archify](https://github.com/tt-a1i/archify).
