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

> 🔄 **Implementación en curso.** El diseño, las validaciones y el dataset están terminados. Las fases F2 a F7 dejaron el camino del dato hasta Silver: el Event Simulator ejecuta transacciones sobre `postgresql`, el pipeline de Flink CDC replica cada cambio en Bronze, sobre RustFS y el catálogo Iceberg, y el job `bronze_to_silver.py` construye con Spark el modelo dimensional de Silver. Ese job todavía se lanza a mano: Airflow, Gold y Superset llegan fase a fase según el [plan de trabajo](planning/PLAN.md).

| Elemento | Estado |
|---|---|
| Documento de diseño ([`lab-design/LAB-DESIGN.md`](lab-design/LAB-DESIGN.md)) | ✅ Revisión 6 |
| Diagramas y bocetos ([`lab-design/diagrams/`](lab-design/diagrams/)) | ✅ Diez, generados con Archify |
| Versiones del stack | ✅ Última estable compatible de cada componente; verificadas contra Docker Hub, Maven Central y PyPI |
| Imágenes base en Docker Hub | ✅ Las diez existen para `amd64` y `arm64` |
| Estructura de directorios del proyecto | ✅ Creada; con contenido en `raw_data/`, `metadata-db/`, `postgresql/`, `flink/`, `java-simulator/`, `pyspark/` y `duckdb/` |
| Validaciones de compatibilidad entre componentes | ✅ 12 de 12 superadas. Resultados en el [documento de decisiones y validaciones](lab-design/DECISIONS-AND-VALIDATIONS.md#2-validaciones) |
| Dataset de entrada: 20 CSV en [`raw_data/`](raw_data/), uno por tabla | ✅ Definitivo: 6,899 películas sintéticas, 438,925 filas y 25.7 MB, con su script generador y su [README](raw_data/README.md) |
| Base del proyecto: `.env.example`, `docker-compose.yml`, `volumes-init` y `metadata-db` | ✅ Fase F2 terminada |
| PostgreSQL operacional: esquema `catalog`, cuentas, publicación y servicio en el Compose | ✅ Fase F3 terminada |
| Almacenamiento y catálogo: RustFS, bucket `warehouse`, catálogo Iceberg y sus tres namespaces | ✅ Fase F4 terminada |
| Flink CDC hacia Bronze: imagen, pipeline, envío idempotente y reconstrucción | ✅ Fase F5 terminada |
| Event Simulator: transacciones reales, interfaz de consola y seguimiento de cada cambio hasta Bronze | ✅ Fase F6 terminada |
| Spark y capa Silver: imagen, clúster y el job que mantiene 14 dimensiones, 2 hechos y 6 bridges con historial | ✅ Fase F7 terminada |
| Implementación del resto (Gold, DAG y Superset) | ⏳ Fases F8 a F12; ver el [plan de trabajo](planning/PLAN.md) |

## 3. 🗺️ Arquitectura

![Arquitectura end-to-end del laboratorio ElastiFlix: de los CSV a Superset pasando por PostgreSQL, Flink CDC, las tres capas Iceberg, PySpark, Airflow y DuckDB](lab-design/diagrams/lab-architecture.svg)

> 🔍 **Cómo leerlo:** la columna central es el camino del dato, de arriba abajo. La línea punteada que va del Event Simulator a Bronze no forma parte de ese camino: es la consulta de solo lectura con la que el simulador comprueba que cada cambio llegó. Airflow (izquierda) lanza los jobs PySpark; el diagrama muestra los dos de transformación. Las tres capas quedan registradas en el Iceberg REST Catalog y sus archivos viven en RustFS (derecha); Flink, Spark y DuckDB resuelven las tablas ahí.

### Flujo principal

El recorrido de un cambio, paso a paso, del CSV hasta Superset, está en el [diagrama del criterio de éxito](lab-design/diagrams/end-to-end-change-path.svg).

### Ideas clave del diseño

- 🌊 **CDC real, no carga batch.** El simulador escribe transacción por transacción y Flink CDC lee el WAL lógico de forma continua.
- 🥉 **Bronze conserva los borrados.** Cada tabla es un espejo por clave primaria con dos columnas técnicas (`cdc_op_type`, `cdc_op_ts`); un `DELETE` queda como tombstone en lugar de desaparecer.
- 🥈 **Historial donde aporta.** SCD Type 2 en las dimensiones cuyos atributos cambian (`dim_movie`, `dim_collection`, `dim_keyword`); el resto son Tipo 1.
- 🥇 **Gold simple para BI.** Tablas planas que se recargan completas en cada corrida.
- 🦆 **DuckDB embebido.** No es un servicio de red: corre dentro del contenedor de Superset, donde lee Gold directamente desde Iceberg, y dentro del simulador, que lo usa para comprobar que cada cambio llegó a Bronze.
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
| Apache Superset | **6.1.0** | BI y dashboards | Presentar el resultado final: los gráficos y dashboards que cada quien construye sobre Gold |
| RustFS | **1.0.6** | Object storage S3-compatible | Sustituir a un servicio S3 de nube, para que todo corra en la máquina local |
| Iceberg REST Catalog | **1.10.1** | Catálogo compartido | Dar a Flink, Spark y DuckDB un único registro de tablas |
| Docker Compose | **v2 o posterior** | Runtime del laboratorio | Levantar todo el laboratorio con un solo comando reproducible |

> ℹ️ Cada componente usa la versión estable más reciente que el resto del stack admite, y toda imagen base está publicada en Docker Hub. Cuatro quedan por debajo de la última publicada por compatibilidad entre librerías: Flink 2.2.1 (Flink CDC 3.7 no soporta Flink 2.3), Spark 4.1.4 (Iceberg no publica runtime para Spark 4.2 ni 4.3), Iceberg 1.10.2 en Flink (línea contra la que se compila Flink CDC 3.7.0) y DuckDB 1.5.6 (Superset 6.1.0 exige `duckdb<2`). Otros tres siguen su propio criterio: el catálogo REST 1.10.1 (no hay imagen versionada más nueva), Java 25 (la LTS vigente) y Python 3.12 (la versión más alta común a Airflow y Superset). El razonamiento completo y la tabla de imágenes están en la [sección 3 del diseño](lab-design/LAB-DESIGN.md#3--software-stack).

## 5. 🥉🥈🥇 Capas de datos

![Linaje de datos por capa: CSV, tablas operacionales de PostgreSQL, tablas espejo de Bronze, dimensiones, hechos y bridges de Silver, productos Gold y consumo en Superset](lab-design/diagrams/medallion-dataflow.svg)

| Capa | Escribe | Lee | Contenido |
|---|---|---|---|
| 🐘 PostgreSQL `catalog` | Event Simulator | Flink CDC | 20 tablas normalizadas |
| 🥉 Bronze | Flink CDC | `bronze_to_silver.py` y el simulador | 20 tablas espejo + columnas CDC |
| 🥈 Silver | `bronze_to_silver.py` | `silver_to_gold.py` | 14 dimensiones, 2 hechos, 6 bridges |
| 🥇 Gold | `silver_to_gold.py` | DuckDB (Superset) | 7 productos analíticos |

## 6. 📁 Estructura del repositorio

Contenido actual:

```text
postgresql-19-cdc-duckdb/
|
|-- .env.example
|-- .gitattributes
|-- .gitignore
|-- docker-compose.yml
|-- AGENTS.md
|-- CLAUDE.md
|-- README.md
|-- planning/
|   |-- PLAN.md
|   `-- update_progress.py
|-- raw_data/
|   |-- README.md
|   |-- generate_raw_data.py
|   `-- <tabla>.csv   (20 archivos)
|-- flink/
|   |-- Dockerfile
|   |-- config/flink-properties.conf
|   `-- jobs/      (pipeline YAML y scripts de envío y de borrado de Bronze)
|-- metadata-db/
|   `-- init/01-create-databases.sh
|-- postgresql/
|   |-- init/      (DDL de las 20 tablas, cuentas, identidad de réplica y publicación)
|   `-- scripts/load_dev_data.sql
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

Esqueleto del proyecto (un directorio por servicio, con sus volúmenes dentro). Los directorios ya existen. `raw_data/` contiene el dataset, `metadata-db/init/` su script de inicialización, `postgresql/init/` el DDL de las 20 tablas, sus cuentas, la identidad de réplica y la publicación, `postgresql/scripts/` la carga de desarrollo, `flink/` la imagen, la configuración y el pipeline CDC, `java-simulator/` el proyecto Maven del simulador y su imagen, `pyspark/` la imagen de Spark, su configuración, los datos de referencia y el job de Silver, y `duckdb/init/` el SQL con el que DuckDB adjunta el lakehouse; los demás están vacíos, con un `.gitkeep` cada uno. El contenido del resto de servicios llega con su fase del plan. El detalle de subdirectorios está en la [sección 7 del diseño](lab-design/LAB-DESIGN.md#7--estructura-del-repositorio).

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
`-- superset/          configuración
```

## 7. ✅ Requisitos

- 🐳 Docker Engine con Docker Compose v2 o posterior. En Windows, Docker Desktop con el backend WSL 2.
- CPU x86_64/amd64. El laboratorio se construye y se valida en un solo equipo con Windows 11.
- En un Mac con Apple Silicon no está probado: las imágenes base existen para `arm64`, pero ninguna validación se ha ejecutado ahí. Los puntos a revisar están en la sección 2.2 del [diseño](lab-design/LAB-DESIGN.md).
- Recomendado: **8 CPU, 16 GB RAM y al menos 30 GB libres**.
- Acceso a Internet durante el primer build. El runtime no depende de servicios cloud externos.

## 8. ▶️ Ejecución

Antes del primer arranque, copia la plantilla de configuración. Sus valores son de laboratorio y sirven tal cual en una máquina local:

```bash
cp .env.example .env
```

Cuando la implementación esté completa, un único comando levantará el laboratorio:

```bash
docker compose up -d --build
```

Ese comando también ejecutará los jobs de preparación (permisos de los directorios de datos, bucket, namespaces, envío del pipeline CDC, metadatos de Airflow y Superset), sin pasos manuales intermedios.

> ⚠️ Hoy ese comando solo levanta una parte: los jobs `volumes-init`, que prepara los directorios de datos, `rustfs-init`, que crea el bucket `warehouse`, e `iceberg-init`, que crea los namespaces `bronze`, `silver` y `gold`; `metadata-db`, el PostgreSQL de metadatos de Airflow y Superset; `postgresql`, la base operacional con sus 20 tablas vacías, lista para el CDC; `rustfs`, el almacenamiento de objetos; `iceberg-rest`, el catálogo de tablas; y Flink (`flink-jobmanager`, `flink-taskmanager` y el job `flink-cdc-submit`), que deja corriendo el pipeline que replica PostgreSQL en Bronze; `java-simulator`, que empieza a insertar películas en cuanto el pipeline está en marcha; y `spark-master` y `spark-worker`, el clúster que ejecuta los jobs por lotes (ver [Estado del proyecto](#2--estado-del-proyecto)). Para esperar a que un servicio esté sano, nómbralo: `docker compose up -d --wait metadata-db`. Sin nombre, `--wait` devuelve error en cuanto termina un job one-shot, aunque termine bien.

### El simulador

El simulador arranca solo y escribe una línea por transacción. Para verlo y manejarlo:

| Qué | Cómo |
|---|---|
| Ver las transacciones | `docker compose logs -f java-simulator` |
| Abrir la interfaz de consola | `docker compose attach java-simulator` y después cualquier tecla. La terminal debe medir al menos 100×30 |
| Manejar la simulación | `Espacio` pausa o reanuda, `+` y `-` cambian la velocidad, `P` los pesos, `M` lanza una operación a mano, `↑` y `↓` recorren la lista |
| Salir de la interfaz | `Q` y después `Ctrl-P`, `Ctrl-Q`. El simulador sigue en marcha |
| Ver el log con la interfaz abierta | `docker compose exec java-simulator tail -f /tmp/simulator.log` |
| Detener y volver a arrancar | `docker compose stop java-simulator` y `docker compose start java-simulator`. Continúa donde quedó |

La columna `Bronze` de la interfaz dice si cada cambio ya llegó al lakehouse y cuánto tardó: entre 11 y 50 segundos. Al detenerlo, el contenedor queda en `Exited (143)`; es lo normal. El detalle está en la [sección 9 del diseño](lab-design/LAB-DESIGN.md#9--aplicación-java-25-event-simulator).

### El job de Silver

Mientras no exista Airflow, Silver se construye y se pone al día lanzando el job a mano:

```bash
docker compose run --rm --no-deps spark-worker spark-submit /opt/spark/jobs/bronze_to_silver.py
```

La primera corrida crea las 22 tablas de Silver; las siguientes solo escriben lo que cambió en Bronze, y una corrida sin cambios no escribe nada. Tarda entre uno y dos minutos con el dataset completo. Si RustFS lleva más de una hora en marcha puede tardar entre 6 y 9 minutos: es un problema conocido, descrito en la [sección 15 del diseño](lab-design/LAB-DESIGN.md#15--rustfs). En Git Bash hay que anteponer `MSYS_NO_PATHCONV=1` al comando. La interfaz de Spark está en <http://127.0.0.1:8082>. El detalle del job está en la [sección 19 del diseño](lab-design/LAB-DESIGN.md#19--job-pyspark-1-bronze--silver).

### Carga de desarrollo

Para desarrollar sin esperar al simulador, las tablas se pueden llenar de una vez con la carga de desarrollo, que mete los 20 CSV (438,925 filas). Solo carga sobre una base vacía, así que se levanta todo menos el simulador (`docker compose up -d flink-cdc-submit`), se lanza la carga y después `docker compose up -d`. El detalle está en la [sección 39 del diseño](lab-design/LAB-DESIGN.md#datos-de-desarrollo):

```bash
docker compose run --rm --no-deps -v ./raw_data:/raw_data:ro -v ./postgresql/scripts:/scripts:ro postgresql bash -c 'PGPASSWORD="$ELASTIFLIX_APP_PASSWORD" psql -h postgresql -U elastiflix_app -d elastiflix -v ON_ERROR_STOP=1 -f /scripts/load_dev_data.sql'
```

### Flujo demostrativo esperado

1. Arranca el stack; PostgreSQL tiene el esquema pero no las películas.
2. Flink CDC queda corriendo y el simulador empieza a insertar.
3. Las filas llegan a PostgreSQL y, segundos después, a Bronze.
4. El simulador genera `UPDATE` y `DELETE`; se reflejan por CDC.
5. Airflow, cada 10 minutos, ejecuta `bronze_to_silver` y luego `silver_to_gold`.
6. DuckDB consulta Gold. En Superset se conecta esa fuente de datos y se crea la primera visualización.

Superset arranca sin dashboards: quien usa el laboratorio diseña los suyos. Cómo conectar la fuente de datos y crear una visualización está en la [guía de la sección 35 del diseño](lab-design/LAB-DESIGN.md#guía-conectar-gold-y-crear-una-visualización).

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
