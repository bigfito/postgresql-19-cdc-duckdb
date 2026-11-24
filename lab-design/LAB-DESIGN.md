# 🎬 ElastiFlix PostgreSQL CDC Lakehouse Lab

> 🟦 **CDC** · 🟪 **Lakehouse** · 🟩 **Medallion Architecture** · 🟨 **SCD Type 2** · 🟥 **BI**
>
> **Laboratorio local, reproducible y orientado a demostración técnica**, construido completamente con contenedores y un único `docker compose up`.

## 1. Propósito

Este documento consolida las decisiones acordadas para diseñar e implementar un laboratorio reproducible de ingeniería de datos end-to-end para **ElastiFlix**.

El laboratorio simulará actividad transaccional sobre PostgreSQL 19, capturará cambios mediante Apache Flink CDC, persistirá las capas de datos con Apache Iceberg sobre almacenamiento S3-compatible local, construirá un modelo dimensional mediante PySpark, materializará productos analíticos para consumo y los expondrá mediante DuckDB y Apache Superset.

Todo el entorno deberá levantarse desde un único `docker-compose.yml`.

> 📝 **Revisión 6 (2026-11-22):** dataset definitivo, validaciones 10 a 12, reconstrucción de Bronze, medición de memoria con todo el stack y decisiones 26 a 65; los diagramas y bocetos que estaban dibujados en texto pasan a Archify. El detalle está en el registro de cambios de [DECISIONS-AND-VALIDATIONS.md](DECISIONS-AND-VALIDATIONS.md).
>
> 🛠️ **Revisión 7 (2026-11-23), implementación:** decisiones 66 a 73. El laboratorio está construido y comprobado de extremo a extremo (fases F2 a F11 del [plan](../planning/PLAN.md)). Donde la implementación concretó o corrigió el diseño, la sección correspondiente lo dice, casi siempre en un apartado «Cómo está implementado». El documento conserva el futuro con el que se escribió: «deberá» y «será» describen lo que el laboratorio ya hace.

> 🎨 **Leyenda visual:** 🥉 Bronze = réplica operacional; 🥈 Silver = modelo dimensional histórico; 🥇 Gold = serving analítico; 🟪 infraestructura compartida; 🟥 consumo BI.

## 2. ✅ Requisitos

### 2.1 Requisitos funcionales

- 📄 Contar con el dataset de entrada en `raw_data/`: 20 archivos CSV, uno por tabla del modelo relacional, con datos sintéticos que reproducen el perfil del catálogo ElastiFlix y sin los campos vectoriales (sección 8).
- ☕ Ejecutar un simulador de eventos en Java 25 que lea esos CSV y produzca transacciones `INSERT`, `UPDATE` y `DELETE` reales.
- 🐘 Mantener el modelo operacional normalizado dentro de PostgreSQL 19, base `elastiflix`, esquema `catalog`.
- 🌊 Capturar cambios por logical replication mediante Flink CDC.
- 🥉 Replicar PostgreSQL **as-is** en Iceberg Bronze, añadiendo únicamente dos columnas técnicas de CDC (`cdc_op_type`, `cdc_op_ts`) y conservando los DELETE como tombstones.
- 🥈 Construir Silver mediante PySpark con modelo dimensional, FACT, DIM, bridges y SCD Type 2 donde el atributo realmente cambia.
- 🥇 Crear productos analíticos Gold materializados a partir de Silver.
- 🦆 Consultar Gold desde DuckDB, que corre embebido en el proceso que lo usa.
- 📊 Consumir Gold desde Apache Superset a través de DuckDB. Superset queda listo para usarse; quien usa el laboratorio conecta la fuente de datos y crea sus propias visualizaciones (guía en la sección 35).
- ⏱️ Orquestar mediante Apache Airflow los jobs PySpark (`bronze_to_silver.py`, `silver_to_gold.py`, las validaciones y el mantenimiento).
- 🧰 Inicializar bucket, namespaces, pipeline CDC, metadatos de Airflow y Superset mediante jobs one-shot declarados en el mismo Docker Compose.

### 2.2 Requisitos técnicos

- 🐳 Docker Engine con Docker Compose v2 o posterior. En Windows, Docker Desktop con el backend WSL 2; el repositorio puede vivir en una unidad NTFS (los bind mounts sobre NTFS se comprobaron en la validación 4; el cambio de propietario de los directorios `data/` lo hace `volumes-init`, sección 45.2).
- CPU x86_64/amd64. El laboratorio se construyó y se validó en un equipo con Windows 11 y Docker Desktop sobre WSL 2. Después de la versión `v1.0.1` se comprobó completo en un segundo equipo, con Ubuntu 24.04, Docker Engine 29 y sus datos en `ext4` (sección 44).
- **Mac con Apple Silicon y otros equipos ARM64: sin probar.** Todas las imágenes base existen también para `linux/arm64` (sección 3.2), así que debería construirse sin cambios, pero ninguna validación se ha ejecutado en esa arquitectura. Lo que conviene revisar primero: que las extensiones de DuckDB se instalan para `linux_arm64` en las imágenes de Superset y del simulador, que el JAR de DuckDB JDBC carga su librería nativa, y que Docker Desktop tiene asignados al menos 12 GB de memoria. Tampoco se ha probado en Linux nativo, donde el job `volumes-init` (sección 45.2) es el que ajusta los permisos de los directorios de datos.
- Recomendación para una ejecución cómoda del laboratorio: **8 CPU, 16 GB RAM y al menos 30 GB libres**. Con 16 GB el margen es estrecho (Flink, Spark, Airflow 3, Superset y dos PostgreSQL a la vez), por lo que cada servicio declarará límites de memoria en el Compose; ver [sección 39](#39--docker-compose).
- Puertos locales disponibles para las interfaces que decidamos publicar, por ejemplo PostgreSQL, Flink UI, Airflow UI, RustFS, Iceberg REST y Superset. Se publicarán ligados a `127.0.0.1`, no a todas las interfaces.
- Acceso a Internet durante el primer build para descargar imágenes y dependencias.
- El runtime final no deberá depender de servicios cloud externos. Esto incluye las extensiones de DuckDB (`iceberg`, `httpfs` y `avro`), que se instalarán durante el build de la imagen y no en la primera consulta.

### 2.3 Requisitos de interoperabilidad

> 🔑 **Regla de oro:** un tipo de dato del modelo operacional solo se utilizará si puede recorrer de forma segura la cadena **PostgreSQL → Flink CDC → Iceberg → PySpark/DuckDB → Superset**.

Se privilegiarán `bigint`, `integer`, `numeric(p,s)`, `text`, `boolean`, `date` y timestamps interoperables. Se evitarán tipos especializados cuando dificulten CDC o consumo analítico.

## 3. 🧰 Software Stack

Las versiones base recomendadas se fijan para que el laboratorio sea reproducible. Cuando dos componentes mantienen una relación de compatibilidad estricta, esa compatibilidad tiene prioridad sobre usar simplemente “la versión más nueva”.

| Componente | Versión base | Imagen o artefacto | Rol | Propósito en el laboratorio |
|---|---:|---|---|---|
| PostgreSQL | **19.0** | `postgres:19.0` | Base operacional con logical replication; la misma imagen sirve a `metadata-db` | Hacer de sistema transaccional real: es el origen cuyos cambios se capturan desde el WAL |
| Java | **25** (LTS) | `eclipse-temurin:25.0.5.1_2-jre` | Event Simulator | Mostrar una aplicación que genera transacciones de verdad, en lugar de una carga por lotes |
| Apache Maven | **3.10.0** | `maven:3.10.0-eclipse-temurin-25` | Etapa de build del simulador | Compilar el simulador dentro de Docker, sin exigir un JDK en la máquina de quien revisa |
| PostgreSQL JDBC | **42.7.14** | `org.postgresql:postgresql` | Driver del simulador | Conectar el simulador con PostgreSQL y controlar cada transacción |
| Apache Commons CSV | **1.14.1** | `org.apache.commons:commons-csv` | Lectura de los CSV en el simulador | Leer sin errores celdas con comas, comillas y saltos de línea |
| Lanterna | **3.1.5** | `com.googlecode.lanterna:lanterna` | Interfaz de consola del simulador | Dar al simulador una pantalla desde la que observar, controlar y dirigir la simulación |
| DuckDB JDBC | **1.5.6.0** | `org.duckdb:duckdb_jdbc` | Seguimiento aguas abajo desde el simulador | Comprobar desde el simulador si cada cambio ya llegó a Bronze |
| Apache Flink | **2.2.1** | `flink:2.2.1-java21` | Runtime de streaming | Mantener un job de streaming siempre encendido, con checkpoints y recuperación ante fallos |
| Apache Flink CDC | **3.7.0** | conectores `postgres` e `iceberg`, versión `3.7.0-2.2` | PostgreSQL CDC → Iceberg | Capturar cada INSERT, UPDATE y DELETE sin escribir código: el pipeline es un archivo YAML |
| Apache Iceberg en Flink | **1.10.2** | `iceberg-flink-runtime-2.0`, `iceberg-aws-bundle` | Sink Iceberg del pipeline CDC | Escribir Bronze como tabla transaccional, con upsert por clave primaria |
| Apache Spark / PySpark | **4.1.4** | `apache/spark:4.1.4-scala2.13-java21-python3-ubuntu` | Bronze → Silver → Gold | Transformar por lotes: construir el modelo dimensional con historial y los productos Gold |
| Apache Iceberg en Spark | **1.12.0** | `iceberg-spark-runtime-4.1_2.13`, `iceberg-aws-bundle` | Lectura y escritura de Silver y Gold | Aportar `MERGE`, snapshots y mantenimiento de tablas sobre object storage |
| Python | **3.12** | variantes `-python3.12` y `-py312` de las imágenes; se instala en la de Spark | Intérprete común de Airflow, Spark y Superset | Evitar que PySpark falle porque el driver y los ejecutores usan versiones distintas |
| Apache Airflow | **3.4.0** | `apache/airflow:3.4.0-python3.12` | Orquestación | Encadenar, validar y reintentar los jobs por lotes, y dejar visible cada corrida |
| Proveedor Spark de Airflow | **6.3.4** | `apache-airflow-providers-apache-spark` | `SparkSubmitOperator` | Lanzar `spark-submit` desde una tarea del DAG |
| DuckDB | **1.5.6** | paquete Python `duckdb`; `duckdb/duckdb:1.5.6` para la línea de comandos | SQL/query engine embebido | Consultar Gold con SQL sin levantar un motor de consultas aparte |
| duckdb-engine | **0.17.0** | paquete Python `duckdb-engine` | Dialecto SQLAlchemy para Superset | Hacer que Superset trate a DuckDB como una base de datos más |
| Apache Superset | **6.1.0** | `apache/superset:6.1.0-py312` | BI y dashboards | Presentar el resultado final: los gráficos y dashboards que cada quien construye sobre Gold |
| RustFS | **1.0.6** | `rustfs/rustfs:1.0.6` | Object storage S3-compatible | Sustituir a un servicio S3 de nube, para que todo corra en la máquina local |
| Iceberg REST Catalog | **1.10.1** | `apache/iceberg-rest-fixture:1.10.1` | Catálogo compartido | Dar a Flink, Spark y DuckDB un único registro de tablas |
| Docker Compose | **v2 o posterior** | — | Runtime del laboratorio | Levantar todo el laboratorio con un solo comando reproducible |

> ℹ️ Cada componente usa la versión estable más reciente que el resto del stack admite. El motivo de cada versión, y de las que se descartaron, está en el [documento de decisiones y validaciones](DECISIONS-AND-VALIDATIONS.md).

### 3.1 Política de versiones

- 🔒 Las imágenes Docker deberán quedar **pinneadas** a una versión exacta, evitando `latest`, etiquetas móviles como `25-jre` y rangos como `1.0.x`.
- 🆕 Se usa la versión estable más reciente de cada componente que sea compatible con el resto. No se adoptan candidatas (`rc`), `preview` ni `dev`.
- 🐳 Toda imagen base debe existir en Docker Hub con esa etiqueta exacta y para `linux/amd64` y `linux/arm64`. No se usan otros registros.
- 🧪 Las actualizaciones deberán probarse end-to-end antes de modificar el stack base.
- 🔗 Las versiones de Flink, Flink CDC e Iceberg runtime deberán tratarse como un conjunto compatible. Lo mismo aplica al par Spark / `iceberg-spark-runtime` y a la versión de Python de Airflow y Spark.
- 📌 Las dependencias Maven/Python deberán fijarse explícitamente cuando sean parte del runtime.
- 📥 Los JAR de Flink y Spark se descargan durante el build de cada imagen; no se versionan en el repositorio.

### 3.2 Imágenes en Docker Hub

Todas las imágenes base del laboratorio están publicadas en Docker Hub para `linux/amd64` y `linux/arm64`. Comprobado el 2026-11-22 con `docker manifest inspect` y la API de etiquetas de Docker Hub; la de Debian, que se añadió en la fase F10, el 2026-11-23.

| Servicio del Compose | Imagen base | Última actualización de la etiqueta |
|---|---|---|
| `postgresql`, `metadata-db` | `postgres:19.0` | 2026-11-20 |
| `java-simulator` (build) | `maven:3.10.0-eclipse-temurin-25` | 2026-11-21 |
| `java-simulator` (runtime) | `eclipse-temurin:25.0.5.1_2-jre` | 2026-11-20 |
| `flink-jobmanager`, `flink-taskmanager`, `flink-cdc-submit` | `flink:2.2.1-java21` | 2026-11-20 |
| `spark-master`, `spark-worker` | `apache/spark:4.1.4-scala2.13-java21-python3-ubuntu` | 2026-10-28 |
| `airflow-*` | `apache/airflow:3.4.0-python3.12` | 2026-11-06 |
| `superset`, `superset-init` | `apache/superset:6.1.0-py312` | 2026-09-21 |
| `rustfs` | `rustfs/rustfs:1.0.6` | 2026-11-15 |
| `iceberg-rest` | `apache/iceberg-rest-fixture:1.10.1` | 2025-12-22 |
| `duckdb` (perfil `tools`), de donde se copia el binario | `duckdb/duckdb:1.5.6` | 2026-09-29 |
| `duckdb` (perfil `tools`), imagen final | `debian:trixie-20261104-slim` | 2026-11-05 |

Los componentes que son librerías no tienen imagen propia: se instalan durante el build de la imagen que los aloja.

| Componente | Dónde se instala | Origen |
|---|---|---|
| Flink CDC 3.7.0 (distribución y conectores `3.7.0-2.2`) | Imagen de Flink | Descargas de Apache y Maven Central |
| Iceberg 1.10.2 (`iceberg-flink-runtime-2.0`, `iceberg-aws-bundle`) | Imagen de Flink | Maven Central |
| Iceberg 1.12.0 (`iceberg-spark-runtime-4.1_2.13`, `iceberg-aws-bundle`) | Imágenes de Spark y Airflow | Maven Central |
| JDBC 42.7.14, Commons CSV 1.14.1, Lanterna 3.1.5 y DuckDB JDBC 1.5.6.0 | JAR del simulador | Maven Central |
| JUnit 6.1.3 | Etapa de build del simulador, para sus pruebas; no va en el JAR | Maven Central |
| Extensiones `httpfs`, `iceberg` y `avro` de DuckDB | Imágenes del simulador y del contenedor `duckdb` | Repositorio de extensiones de DuckDB |
| PySpark 4.1.4, `pyspark-client` 4.1.4 y proveedor Spark 6.3.4 | Imagen de Airflow | PyPI |
| Java 21 (`openjdk-21-jre-headless`) | Imagen de Airflow | Repositorio de paquetes de Debian |
| Python 3.12, instalado con `uv` | Imagen de Spark | PyPI (`uv`) y builds de CPython que descarga `uv` desde GitHub |
| DuckDB 1.5.6, `duckdb-engine` 0.17.0, `psycopg2-binary` y extensiones `httpfs`, `iceberg` y `avro` | Imagen de Superset | PyPI y repositorio de extensiones de DuckDB |

Los seis jobs one-shot (`volumes-init`, `rustfs-init`, `iceberg-init`, `flink-cdc-submit`, `airflow-init` y `superset-init`) reutilizan alguna de las imágenes anteriores; no añaden imágenes nuevas al laboratorio.

## 4. 🗺️ Diagrama de Arquitectura

![Arquitectura end-to-end del laboratorio ElastiFlix: de los CSV a Superset pasando por PostgreSQL, Flink CDC, las tres capas Iceberg, PySpark, Airflow y DuckDB](diagrams/lab-architecture.svg)

> 🔍 **Cómo leerlo:** la columna central es el camino del dato, de arriba abajo. La línea punteada que va del Event Simulator a Bronze no forma parte de ese camino: es la consulta de solo lectura con la que el simulador comprueba que cada cambio llegó (sección 9.3). Airflow (izquierda) lanza los jobs PySpark; el diagrama muestra los dos de transformación, y el DAG completo está en la sección 18. Las tres capas quedan registradas en el Iceberg REST Catalog y sus archivos viven en RustFS (derecha). Por legibilidad no se dibuja una flecha de cada motor hacia el catálogo: Flink, Spark y DuckDB resuelven las tablas ahí.
>
> Versión interactiva: [`diagrams/lab-architecture.html`](diagrams/lab-architecture.html) · Fuente editable: [`diagrams/lab-architecture.json`](diagrams/lab-architecture.json). Los diagramas de este documento se generan con [Archify](https://github.com/tt-a1i/archify); ver [sección 7](#7--estructura-del-repositorio).

### Flujo principal

El recorrido de un cambio, paso a paso, del CSV hasta Superset, está en el diagrama de la sección 44.

### Plano de control y almacenamiento

- 🧭 **Iceberg REST Catalog**: catálogo compartido para las tablas Iceberg.
- 🪣 **RustFS**: almacenamiento físico S3-compatible de Bronze, Silver y Gold.
- ⏱️ **Airflow**: controla únicamente los jobs PySpark del pipeline analítico.
- 🌊 **Flink CDC**: permanece ejecutándose continuamente y no depende del scheduler batch.
- 🦆 **DuckDB**: no es un servicio de red. Es una librería que corre dentro del contenedor de Superset, dentro del simulador (para seguir cada cambio hasta Bronze) y, opcionalmente, en un contenedor de línea de comandos para exploración.

---

## 5. 🎯 Principios de diseño acordados

1. El proyecto será completamente autocontenido y reproducible con Docker Compose.
2. La base operacional será PostgreSQL 19 y la base de datos se llamará `elastiflix`.
3. El dataset de entrada será un conjunto de 20 archivos CSV, uno por tabla del modelo relacional, con 6,899 películas sintéticas que reproducen el perfil del catálogo original.
4. Los CSV no se cargarán masivamente con `COPY` como mecanismo principal del laboratorio. Una aplicación Java 25 simulará actividad transaccional insertando registros gradualmente.
5. El simulador Java podrá generar `INSERT`, `UPDATE` y `DELETE` reales sobre PostgreSQL.
6. Apache Flink CDC capturará los cambios de PostgreSQL y los escribirá en Apache Iceberg.
7. Bronze será una réplica `as-is` del modelo relacional normalizado de PostgreSQL: mismas tablas y columnas, más dos columnas técnicas de CDC. Guarda el último estado por clave primaria y conserva las filas borradas como tombstones.
8. Silver será un modelo dimensional de tipo estrella, con dimensiones, hechos y bridges.
9. Las dimensiones de negocio en Silver soportarán SCD Type 2 cuando sus atributos puedan cambiar en la fuente (`dim_movie`, `dim_collection`, `dim_keyword`). El resto serán Type 1.
10. Apache Airflow gobernará los jobs PySpark de Bronze a Silver y de Silver a Gold.
11. Flink CDC será un proceso continuo y no será ejecutado evento por evento por Airflow.
12. Gold contendrá productos analíticos materializados derivados de Silver y será la fuente de verdad para visualizaciones.
13. DuckDB será el motor SQL de consulta sobre los datos analíticos. Al ser una librería embebida, correrá dentro del proceso que lo usa y no como servidor.
14. Apache Superset consumirá Gold a través de DuckDB, mediante el dialecto `duckdb-engine`.
15. Apache Iceberg será el formato de tablas del lakehouse.
16. Iceberg REST Catalog será el catálogo compartido por Flink, Spark y DuckDB.
17. RustFS será el almacenamiento S3-compatible local donde residirán físicamente los archivos Iceberg.
18. Los tipos vectoriales del dataset original quedan completamente fuera del laboratorio.
19. Los tipos de PostgreSQL se elegirán con una premisa prioritaria: deben poder viajar de forma segura por PostgreSQL -> Flink CDC -> Iceberg -> PySpark/DuckDB -> Superset.
20. Cada volumen persistente de Docker deberá vivir dentro del directorio del servicio al que pertenece, para facilitar la revisión externa. La única excepción son los datos de RustFS, que van en el volumen con nombre `rustfs-data` (decisión 67).
21. Todo paso de preparación (bucket, namespaces, envío del pipeline CDC, migraciones de metadatos) será un job one-shot del mismo Docker Compose. No habrá pasos manuales entre `docker compose up` y el primer dato en Bronze.
22. Los metadatos de Airflow y Superset vivirán en una base PostgreSQL separada (`metadata-db`), no en la base operacional que se captura por CDC.
23. Todo el laboratorio trabajará en UTC. Ningún servicio declara otra zona horaria: las marcas de tiempo se guardan como instantes y se muestran en UTC (decisión 75; sección 39).

## 6. 🏗️ Arquitectura end-to-end

El diagrama de la sección 4 muestra los componentes. Este muestra qué datos pasan de una capa a la siguiente y quién los mueve.

![Linaje de datos por capa: CSV, tablas operacionales de PostgreSQL, tablas espejo de Bronze, dimensiones, hechos y bridges de Silver, productos Gold y consumo en Superset](diagrams/medallion-dataflow.svg)

> 🔍 **Cómo leerlo:** de izquierda a derecha. Las flechas verdes son captura continua de Flink CDC; las grises, el resto de movimientos (la carga transaccional del simulador, los jobs batch de PySpark y la consulta de Superset); las punteadas, resolución de claves dentro de Silver. Los conteos del hecho (géneros, keywords, reparto y demás) salen de las tablas de relación de Bronze, no de los bridges. Los bridges también alimentan Gold (pesos N:M), aunque esa flecha no se dibuja.
>
> Versión interactiva: [`diagrams/medallion-dataflow.html`](diagrams/medallion-dataflow.html) · Fuente editable: [`diagrams/medallion-dataflow.json`](diagrams/medallion-dataflow.json).

Resumen de quién escribe y quién lee cada capa:

| Capa | Escribe | Lee | Contenido |
|---|---|---|---|
| PostgreSQL `catalog` | Event Simulator | Flink CDC | 20 tablas normalizadas |
| 🥉 Bronze | Flink CDC | `bronze_to_silver.py`; el simulador lee `bronze.movie` para su seguimiento | 20 tablas espejo + `cdc_op_type`, `cdc_op_ts` |
| 🥈 Silver | `bronze_to_silver.py` | `silver_to_gold.py` | 14 dimensiones, 2 hechos, 6 bridges |
| 🥇 Gold | `silver_to_gold.py` | DuckDB (Superset) | 7 productos analíticos |

Las tres capas comparten catálogo (Iceberg REST Catalog) y almacenamiento (RustFS, `s3://warehouse/`).

## 7. 📁 Estructura del repositorio

El directorio raíz coincide con el nombre del repositorio:

```text
postgresql-19-cdc-duckdb/
|
|-- docker-compose.yml
|-- .env.example
|-- .gitattributes
|-- .gitignore
|-- AGENTS.md
|-- CLAUDE.md
|-- LICENSE
|-- README.md
|
|-- lab-design/
|   |-- LAB-DESIGN.md
|   |-- DECISIONS-AND-VALIDATIONS.md
|   `-- diagrams/
|
|-- planning/
|   |-- PLAN.md
|   `-- update_progress.py
|
|-- raw_data/
|   |-- README.md
|   |-- generate_raw_data.py
|   `-- <tabla>.csv        (20 archivos, uno por tabla)
|
|-- java-simulator/
|   |-- Dockerfile
|   |-- pom.xml
|   `-- src/
|
|-- postgresql/
|   |-- data/
|   |-- init/
|   `-- scripts/
|
|-- metadata-db/
|   |-- data/
|   `-- init/
|
|-- flink/
|   |-- Dockerfile
|   |-- config/
|   |-- jobs/
|   `-- data/
|
|-- iceberg/
|   |-- config/
|   `-- data/
|
|-- pyspark/
|   |-- Dockerfile
|   |-- jobs/
|   |   |-- bronze_to_silver.py
|   |   |-- silver_to_gold.py
|   |   |-- iceberg_maintenance.py
|   |   |-- validate_bronze.py
|   |   |-- validate_silver.py
|   |   `-- validate_gold.py
|   |-- reference/
|   `-- conf/
|
|-- airflow/
|   |-- Dockerfile
|   |-- dags/
|   |-- logs/
|   |-- config/
|   `-- plugins/
|
|-- duckdb/
|   |-- Dockerfile
|   |-- entrypoint.sh
|   `-- init/
|
|-- superset/
|   |-- Dockerfile
|   |-- data/
|   `-- config/
|
`-- wiki/
    |-- Home.md        (y una página .md por tema)
    |-- _Sidebar.md
    `-- publish.sh
```

Notas sobre la estructura:

- `.env.example` se versiona; `.env` es local y queda en `.gitignore`, igual que el contenido de todos los directorios `data/` y `logs/`.
- Cada directorio vacío lleva un archivo `.gitkeep` para que Git lo conserve y la estructura sea visible al clonar. En los directorios `data/` y `logs/` ese marcador es lo único que se versiona.
- `.gitattributes` fuerza finales de línea LF en todo archivo de texto. Los scripts, SQL, YAML y jobs de este repositorio se ejecutan dentro de contenedores Linux, y un clon en Windows con `core.autocrlf=true` los dejaría con CRLF, que rompe la ejecución. El dataset `*.csv` queda excluido de cualquier conversión.
- `lab-design/diagrams/` guarda, por cada diagrama, la fuente `.json`, la página interactiva `.html` y el `.svg` que se incrusta en la documentación. Se regeneran con Archify: `archify finalize <tipo> <fuente>.json <salida>.html` y `export-svg.mjs <salida>.html <salida>.svg auto`.
- `wiki/` contiene las páginas del wiki de GitHub, escritas para lectores de negocio, sin comandos ni código. El wiki de GitHub es un repositorio aparte; las páginas se escriben y se revisan aquí, y `wiki/publish.sh` las copia allí. Sus dibujos son los diagramas `wiki-*` de `lab-design/diagrams/`. No añaden datos propios: cada cifra que citan sale de este documento.
- `planning/PLAN.md` es el único plan de actividades del laboratorio, con su tablero de avance por fase y global. `planning/update_progress.py` recalcula ese tablero a partir de las actividades marcadas y, con `--done`, registra cada actividad terminada en la bitácora e imprime el avance de su fase y el global, que es lo que se reporta a la persona responsable.
- `AGENTS.md` da a cualquier agente de programación las reglas comunes y lo dirige al plan; `CLAUDE.md` añade lo propio de Claude Code.
- `LICENSE` es el texto de la licencia Apache 2.0, bajo la que se publica el repositorio. Las herramientas que el laboratorio descarga conservan cada una la suya.
- `raw_data/` contiene el dataset de entrada descrito en la sección 8: un CSV por tabla, el script que los genera y su README.
- `postgresql/` usa la imagen oficial sin Dockerfile propio; `postgresql/init/` contiene el DDL, los roles y la publicación, en nueve archivos numerados que la imagen ejecuta en orden: esquema, catálogos, entidades compartidas, `movie`, relaciones, cuentas, contraseñas, identidad de réplica y publicación.
- `metadata-db/` es el PostgreSQL de metadatos de Airflow y Superset; `metadata-db/init/01-create-databases.sh` crea sus cuentas y sus bases (sección 45.3).
- `flink/jobs/` contiene el YAML del pipeline CDC y los dos scripts de operación, `submit-pipeline.sh` y `drop-bronze-tables.sh`; `flink/config/flink-properties.conf`, la configuración de Flink, que el Dockerfile aplica al construir la imagen; y `flink/data/`, los checkpoints. Los JAR se descargan en el build, comprobando la suma de cada uno, por eso no hay `flink/lib/`. La configuración da dos slots al TaskManager (`taskmanager.numberOfTaskSlots: 2`). **`flink/jobs/` se copia dentro de la imagen al construirla; no se monta.** Un cambio en el YAML del pipeline o en los scripts no tiene efecto hasta reconstruir la imagen (`docker compose build flink-jobmanager`) y recrear los servicios de Flink.
- `pyspark/reference/` contiene los datos de referencia versionados que Silver usa para enriquecer catálogos (nombres de idioma, códigos de país, descripción de ratings): seis archivos CSV (sección 24).
- `pyspark/conf/` contiene `spark-defaults.conf`, con el catálogo Iceberg, la memoria de cada job y cuatro particiones de shuffle (`spark.sql.shuffle.partitions 4`), y `log4j2.properties`, el perfil de registro por defecto de Spark con un aviso silenciado (sección 19). `pyspark/conf/`, `pyspark/jobs/` y `pyspark/reference/` se montan en solo lectura en `spark-master` y `spark-worker`; la imagen no copia ninguno.
- `pyspark/jobs/` contiene los dos jobs de transformación, el de mantenimiento (sección 38) y un job corto por cada tarea `validate_*` del DAG (sección 18).
- No hay directorio de pruebas para los jobs: sus comprobaciones son las tareas `validate_*` de cada corrida del DAG (decisión 73).
- `airflow/config/` y `airflow/plugins/` siguen la estructura de la imagen oficial de Airflow y quedan vacíos: la configuración va por variables de entorno y no hay plugins. `iceberg/config/` también está vacío y hoy no tiene uso.
- `postgresql/scripts/` contiene `load_dev_data.sql`, que carga los 20 CSV para desarrollar sin esperar al simulador. Se ejecuta a mano y no forma parte del arranque (sección 39).
- `superset/config/` contiene `superset_config.py`, con el hook de conexión de DuckDB (sección 35). No guarda dashboards: los crea quien usa el laboratorio.
- `duckdb/init/` contiene el SQL de inicialización de DuckDB en dos archivos, `attach_lakehouse.sql` y `gold_views.sql` (sección 34). Se monta en solo lectura en Superset, en el contenedor de línea de comandos y en el simulador, que solo usa el primero. DuckDB no guarda datos propios, por eso no hay `duckdb/data/`.
- `duckdb/entrypoint.sh` es el arranque de la línea de comandos opcional: ejecuta `attach_lakehouse.sql` con las credenciales del entorno y abre la consola (sección 34).

### Regla de persistencia

Cada bind mount o volumen de datos persistentes deberá residir dentro del directorio del servicio propietario. Hay una excepción: los datos de RustFS van en el volumen con nombre `rustfs-data`, que vive en el disco de Docker. RustFS no tiene directorio propio en el repositorio (sección 15, decisiones 67 y 69). La regla no aplica a los montajes de solo lectura de código o configuración que un servicio toma de otro: `pyspark/jobs/`, `pyspark/conf/` y `pyspark/reference/` en Airflow, `duckdb/init/` en Superset, en el simulador y en el contenedor de línea de comandos, y `raw_data/` en el simulador.

Ejemplos:

```yaml
postgresql:
  volumes:
    - ./postgresql/data:/var/lib/postgresql

metadata-db:
  volumes:
    - ./metadata-db/data:/var/lib/postgresql

rustfs:
  volumes:
    - rustfs-data:/data        # la excepción: volumen con nombre

flink-jobmanager:
  volumes:
    - ./flink/data:/opt/flink/state

iceberg-rest:
  volumes:
    - ./iceberg/data:/catalog   # con CATALOG_URI=jdbc:sqlite:/catalog/iceberg_catalog.db

airflow:
  volumes:
    - ./airflow/dags:/opt/airflow/dags
    - ./airflow/logs:/opt/airflow/logs

superset:
  volumes:
    - ./superset/data:/app/superset_home
```

> ⚠️ **PostgreSQL 18 o superior:** la imagen oficial cambió el volumen a `/var/lib/postgresql` (los datos quedan en `/var/lib/postgresql/19/docker`). Montar en `/var/lib/postgresql/data`, como en versiones anteriores, impide que el contenedor arranque.

> ⚠️ **Permisos de los bind mounts:** varias imágenes corren con un usuario no root y necesitan que el directorio del host sea escribible por ese UID. RustFS usa `10001:10001`, sobre su volumen, y Airflow `50000:0`. El job one-shot `volumes-init` ajusta la propiedad de esos directorios y de ese volumen antes de arrancar los servicios (sección 45.2).

No se utilizará un directorio raíz genérico `volumes/`.

## 8. 🎞️ Dataset fuente ElastiFlix

El dataset de entrada son **20 archivos CSV, uno por cada tabla del esquema `catalog`**, en `raw_data/`. El simulador los lee ya normalizados y con sus claves.

### 8.1 Naturaleza de los datos

- **Los datos son sintéticos.** Títulos, sinopsis, personas y compañías son inventados; no reproducen películas, personas ni textos reales. Los nombres se forman combinando palabras, nombres y apellidos corrientes, así que alguno coincide por azar con el de una persona, una película o una compañía que existe; no se refiere a ella.
- **El perfil es el del catálogo original.** Volúmenes, tasas de nulos, distribuciones y catálogos (géneros, países, idiomas, clasificaciones, códigos de enrichment) siguen los del índice Elasticsearch `elastiflix-reloaded` (índice concreto `elastiflix-dq-staging-20261113-220031`), que contiene 6,899 películas.
- Junto a los CSV se versionan el script que los genera, `generate_raw_data.py`, y un `README.md` con la semilla, la forma de regenerarlos y sus comprobaciones.

### 8.2 Archivos y columnas

Cada archivo lleva el nombre exacto de su tabla. Las columnas, tipos, claves y restricciones son los de la sección 12; el orden de columnas dentro de cada archivo es este:

| Archivo | Columnas, en este orden | Clave primaria |
|---|---|---|
| `movie_status.csv` | `status_code` | `status_code` |
| `content_rating.csv` | `rating_code` | `rating_code` |
| `original_language.csv` | `language_code`, `description` | `language_code` |
| `enrichment_field.csv` | `field_name` | `field_name` |
| `genre.csv` | `genre_id`, `name` | `genre_id` |
| `keyword.csv` | `keyword_id`, `name` | `keyword_id` |
| `person.csv` | `person_id`, `name` | `person_id` |
| `production_company.csv` | `company_id`, `name` | `company_id` |
| `production_country.csv` | `country_id`, `name` | `country_id` |
| `spoken_language.csv` | `spoken_language_id`, `name` | `spoken_language_id` |
| `collection.csv` | `collection_id`, `name` | `collection_id` |
| `movie.csv` | `movie_id`, `imdb_id`, `title`, `original_title`, `original_language_code`, `overview`, `plot`, `tagline`, `status_code`, `rating_code`, `release_date`, `runtime_minutes`, `budget_usd`, `revenue_usd`, `popularity`, `user_score`, `vote_average`, `vote_count`, `adult`, `video`, `homepage`, `poster_path`, `backdrop_path` | `movie_id` |
| `movie_collection.csv` | `movie_id`, `collection_id`, `observed_poster_path`, `observed_backdrop_path` | `movie_id` |
| `movie_genre.csv` | `movie_id`, `genre_id`, `source_position` | `movie_id`, `genre_id` |
| `movie_keyword.csv` | `movie_id`, `keyword_id`, `source_position` | `movie_id`, `keyword_id` |
| `movie_cast.csv` | `movie_id`, `person_id`, `billing_order` | `movie_id`, `person_id` |
| `movie_production_company.csv` | `movie_id`, `company_id`, `source_position` | `movie_id`, `company_id` |
| `movie_production_country.csv` | `movie_id`, `country_id`, `source_position` | `movie_id`, `country_id` |
| `movie_spoken_language.csv` | `movie_id`, `spoken_language_id`, `source_position` | `movie_id`, `spoken_language_id` |
| `movie_enrichment.csv` | `movie_id`, `field_name`, `code` | `movie_id`, `field_name` |

Lo que el simulador puede dar por cierto al leerlos:

- Se cumplen las claves primarias, las claves foráneas y las restricciones de la sección 12.
- Dentro de una película no se repite ningún género, keyword, persona, compañía, país ni idioma.
- `source_position` y `billing_order` empiezan en 1 y son consecutivos dentro de cada película.
- Toda entidad está referenciada por al menos una película.
- No hay columnas `created_at` ni `updated_at`: las asigna PostgreSQL.
- `original_language.description` llega `NULL`; el nombre del idioma lo aporta Silver (sección 24).

### 8.3 Formato

- UTF-8 sin BOM, finales de línea LF y una fila de cabecera con los nombres de columna.
- RFC 4180: separador coma, comillas dobles solo cuando hacen falta y comilla doble escapada duplicándola. `plot` contiene saltos de línea y comillas dentro de la celda; `overview` y `tagline`, comillas y comas, pero no saltos de línea.
- `NULL` es un campo vacío sin comillas. No existen cadenas vacías.
- Booleanos `true` o `false`. Fechas `YYYY-MM-DD`. Decimales con punto y la escala de su columna.

`.gitattributes` marca los `*.csv` como `-text`, así que Git no altera sus bytes.

### 8.4 Orden e identificadores

- `movie.csv` va ordenado por `movie_id` ascendente. Es el orden en que el simulador da de alta las películas.
- Los archivos de relación van ordenados por `movie_id` y después por su posición.
- **Claves sustitutas asignadas por el dataset.** En `genre`, `person`, `production_company`, `production_country` y `spoken_language` el identificador es consecutivo desde 1, en orden de primera aparición al recorrer las películas. PostgreSQL no las genera: el simulador inserta el valor del archivo, de modo que un identificador significa lo mismo en el CSV, en PostgreSQL y en Bronze.
- `movie_id`, `keyword_id` y `collection_id` son claves naturales dispersas, no consecutivas.

### 8.5 Volumen

| Tabla | Filas |
|---|---:|
| `movie` | 6,899 |
| `collection` / `movie_collection` | ~1,040 / ~1,930 |
| `genre` / `movie_genre` | 19 / ~18,600 |
| `keyword` / `movie_keyword` | ~11,800 / ~53,900 |
| `person` / `movie_cast` | ~95,000 / ~179,000 |
| `production_company` / `movie_production_company` | ~8,100 / ~24,000 |
| `production_country` / `movie_production_country` | 98 / ~10,100 |
| `spoken_language` / `movie_spoken_language` | 68 / ~9,900 |
| `original_language` | 43 |
| `movie_status`, `content_rating`, `enrichment_field` | 1, 7, 21 |
| `movie_enrichment` | ~18,600 |

El reparto de una película tiene 20 personas de mediana y hasta varios cientos; por eso `movie_cast` es la tabla más grande.

### 8.6 Defectos de calidad presentes a propósito

El dataset conserva los defectos del catálogo original que Silver debe tratar (sección 36):

- nombres de keyword compartidos por dos `keyword_id` distintos;
- un nombre de colección compartido por dos `collection_id`;
- colecciones cuyas películas traen rutas de imagen distintas entre sí en `movie_collection`;
- `Guadaloupe` en `production_country` y `cn` en `original_language`;
- variantes del nombre de una misma compañía como filas separadas;
- `plot` truncado alrededor de 3,000 caracteres.

Dos defectos del catálogo original no llegan a los archivos, porque un CSV por tabla no puede representarlos: un `keyword_id` con dos nombres distintos y un nombre repetido dentro de la lista de una película. Llegan ya resueltos.

### 8.7 Tipos vectoriales expresamente excluidos

No se generan, modelan ni propagan:

```text
plot_1024
plot_512
plot_256
```

La exclusión aplica a los CSV de `raw_data/`, PostgreSQL, Bronze, Silver, Gold, DuckDB y Superset.

## 9. ☕ Aplicación Java 25 Event Simulator

El simulador hace de aplicación transaccional: lee el dataset de `raw_data/` y ejecuta transacciones reales sobre PostgreSQL. Tiene una **interfaz de consola enriquecida**, a pantalla completa en la terminal, desde la que se observa, se controla y se dirige la simulación.

### 9.1 Requisitos funcionales

| Id | Requisito |
|---|---|
| RF-01 | Leer los 20 archivos de `raw_data/` (sección 8) y cargarlos en memoria al arrancar: catálogos, entidades y relaciones indexadas por `movie_id`. |
| RF-02 | Dar de alta las películas en el orden de `movie.csv`, cada una en una sola transacción JDBC con sus catálogos, entidades y relaciones. |
| RF-03 | Generar también `UPDATE` y `DELETE` sobre películas ya insertadas, y reinsertar películas borradas. |
| RF-04 | Decidir la siguiente operación con pesos configurables de INSERT, UPDATE y DELETE, y un intervalo entre transacciones. |
| RF-05 | Ser reproducible: con la misma semilla, sin intervención manual y partiendo de una base vacía, la secuencia de operaciones es la misma. |
| RF-06 | **Ver la actividad en vivo:** estado de la simulación, avance sobre las 6,899 películas, contadores por tipo de operación, ritmo de transacciones y las últimas transacciones con su detalle. |
| RF-07 | **Controlar la simulación en caliente:** iniciar, pausar y reanudar, y cambiar la velocidad y los pesos sin reiniciar. |
| RF-08 | **Lanzar operaciones a mano:** elegir una película y provocar un INSERT, un UPDATE de un tipo concreto, un DELETE o una reinserción. |
| RF-09 | **Seguir el cambio aguas abajo:** indicar, para cada transacción reciente, si su cambio ya llegó a Bronze y cuánto tardó. |
| RF-10 | Funcionar también sin la interfaz abierta: arranca solo, en modo de líneas, y escribe una línea de log por transacción. Con terminal, la interfaz se abre al pulsar una tecla; sin terminal, sigue en modo de líneas. |
| RF-11 | Registrar cada transacción, cada cambio de configuración y cada operación manual en el log, con nivel y marca de tiempo. |
| RF-12 | Ante un dato inconsistente, revertir la transacción de esa película, registrarla con nivel `ERROR` y continuar. |
| RF-13 | Retomar tras un reinicio: al arrancar sobre una base que ya tiene películas, continuar con la primera pendiente de `movie.csv`, sin repetir altas. |

### 9.2 Requisitos no funcionales

- **Sin dependencias en el host.** Corre en su contenedor; la interfaz se usa con `docker compose attach java-simulator`, y se sale de ella sin detener el simulador.
- **Arranque con un único `docker compose up`.** Por defecto empieza a simular en cuanto el pipeline CDC está en marcha, haya o no alguien mirando la interfaz.
- **No bloquea por la interfaz.** La simulación y el refresco de pantalla corren en hilos distintos; un terminal lento o cerrado no detiene las transacciones.
- **El seguimiento aguas abajo es opcional y de solo lectura.** Si Bronze no responde, las transacciones siguen y la columna de seguimiento muestra «sin datos».
- **Memoria acotada:** 0.5 GB (sección 39). Los 20 CSV cargados como texto ocupan unos 100 MB (sección 9.8).
- **Usuario sin privilegios** en el contenedor y cuenta `elastiflix_app` en PostgreSQL (sección 45).
- **Terminal mínima:** 100 columnas por 30 filas, con UTF-8. Por debajo de ese tamaño la interfaz lo avisa en lugar de descomponerse.

### 9.3 Interfaz de consola

La pantalla tiene cinco zonas fijas:

![Boceto de la pantalla de consola del Event Simulator, con cinco zonas fijas: cabecera con estado, semilla, conexiones e intervalo; Avance y Operaciones lado a lado; lista de últimas transacciones; Detalle de la transacción seleccionada; y al pie la barra de teclas](diagrams/simulator-console.svg)

> Versión interactiva: [`diagrams/simulator-console.html`](diagrams/simulator-console.html) · Fuente editable: [`diagrams/simulator-console.json`](diagrams/simulator-console.json).

| Zona | Contenido |
|---|---|
| Cabecera | Estado (`EN MARCHA`, `EN PAUSA`, `TERMINADO`), semilla, conexión a PostgreSQL, conexión a Bronze e intervalo vigente |
| Avance | Películas insertadas sobre el total, barra de progreso, películas vivas en `catalog`, ritmo de transacciones, y películas pendientes y borradas |
| Operaciones | Contadores de INSERT, UPDATE y DELETE con su peso vigente, errores y operaciones manuales |
| Últimas transacciones | Una fila por transacción: hora, operación, `movie_id`, título, filas afectadas, duración y estado en Bronze |
| Detalle | Desglose por tabla de la transacción seleccionada |

Teclas:

| Tecla | Acción |
|---|---|
| `Espacio` | Pausa o reanuda la simulación automática |
| `+` / `-` | Reduce o aumenta el intervalo entre transacciones |
| `P` | Abre el diálogo de pesos de INSERT, UPDATE y DELETE |
| `M` | Abre el diálogo de operación manual |
| `↑` / `↓` | Recorre la lista de transacciones; la seleccionada se muestra en Detalle |
| `Q` | Cierra la interfaz y vuelve al modo de líneas. No detiene el simulador |

Ninguna tecla detiene el simulador. Para detenerlo se usa `docker compose stop java-simulator` y, para volver a arrancarlo, `docker compose start java-simulator`: continúa donde quedó (sección 9.5).

**Operación manual (`M`).** Se elige la película escribiendo su `movie_id` o parte del título, y después la operación:

- INSERT de la siguiente película pendiente, o de una concreta que aún no esté en `catalog`.
- UPDATE descriptivo, de medidas, de relaciones o de catálogo sobre una película viva. El de catálogo solo se ofrece si la película tiene colección o keywords.
- DELETE de una película viva.
- Reinserción de una película borrada.

La operación se ejecuta como una transacción normal, aparece en la lista marcada como manual y queda en el log. Funciona también con la simulación en pausa, que es el modo previsto para una demostración: pausar, lanzar un cambio y seguirlo hasta Bronze, Silver y Superset.

**Seguimiento aguas abajo (RF-09).** La columna `Bronze` de cada transacción pasa de «pendiente» a «✓», con el tiempo transcurrido, cuando el cambio aparece en `bronze.movie`: la fila con ese `movie_id` y un `cdc_op_ts` igual o posterior al instante de referencia de la transacción, o el tombstone si fue un DELETE. El simulador lo comprueba con DuckDB embebido y el mismo SQL de inicialización que usa Superset (sección 34). Reglas, comprobadas en la validación 11:

- **Instante de referencia.** Es `floor(extract(epoch FROM now()) * 1000)`, leído en PostgreSQL dentro de la propia transacción. Nunca un valor redondeado: `cdc_op_ts` es el instante del commit truncado a milisegundos y cae en el mismo milisegundo que el inicio de la transacción en cerca de un 30 % de los casos, de modo que un umbral redondeado hacia arriba deja algunas transacciones pendientes para siempre.
- **Consulta.** Cada 5 segundos, una sola consulta por lote con las transacciones pendientes: `SELECT movie_id, cdc_op_type, cdc_op_ts FROM lake.bronze.movie WHERE movie_id IN (…)`. Cuesta entre 10 y 60 ms, según los deletes acumulados desde la última compactación, y una petición al catálogo.
- **Retraso esperable.** Entre 1 y 35 segundos en la validación 11, según en qué momento del intervalo de checkpoint de Flink caiga el commit. Con el simulador real, en la fase F6, se midieron entre 11 y 50 segundos, tanto a 4 como a 65 transacciones por segundo.
- **Todas las operaciones se siguen en `bronze.movie`.** Por eso el UPDATE de relaciones y el de catálogo actualizan también `updated_at` de la película (sección 9.5): sin eso no tocaría `movie` y nunca saldría de «pendiente».
- **Demora.** Si una transacción no aparece en 120 segundos, cuatro checkpoints, se marca «demorada» y la cabecera avisa de que Bronze no avanza. Se sigue comprobando: si el cambio llega después, pasa a «✓» con su tiempo real.

### 9.4 Modo sin interfaz

El simulador arranca siempre en modo de líneas: no dibuja la pantalla, empieza según su configuración y escribe una línea por transacción con los mismos datos de la lista. Es lo que muestra `docker compose logs java-simulator` y el modo que usa el arranque normal del laboratorio.

El contenedor tiene terminal aunque nadie esté conectado, así que el simulador no puede saber por sí solo si alguien lo mira. Por eso la interfaz no se abre al conectarse, sino con la primera tecla que se pulsa tras `docker compose attach java-simulator`. `Q` la cierra y devuelve el modo de líneas. Si el proceso arranca sin terminal, se queda en modo de líneas.

### 9.5 Reglas de carga

- **Alta perezosa de catálogos y entidades.** Ninguna tabla se precarga. Una fila de `movie_status`, `content_rating`, `original_language`, `enrichment_field`, `genre`, `keyword`, `person`, `production_company`, `production_country`, `spoken_language` o `collection` se inserta la primera vez que una película la necesita, dentro de la transacción de esa película. El simulador recuerda qué claves ya insertó.
- **Identificadores del archivo.** Toda fila se inserta con la clave que trae el CSV, también en las cinco tablas de clave sustituta (sección 8.4).
- **Datos inconsistentes.** Si una película falla por una clave duplicada o una referencia inexistente, el simulador revierte su transacción, lo registra con nivel `ERROR` y continúa con la siguiente. No intenta corregir el dato.
- **Tipos de UPDATE.** Hay cuatro clases, para ejercitar los cuatro caminos de Silver: descriptivo (`title`, `tagline`, `overview`, `homepage`), de medidas (`popularity`, `vote_count`, `vote_average`, `user_score`, `budget_usd`, `revenue_usd`), de relaciones (añadir o quitar un género o una keyword, tomados de los que ya existen en PostgreSQL) y de catálogo (renombrar la colección de la película o una de sus keywords). Todo UPDATE sobre `movie`, `collection` o `keyword` actualiza `updated_at`. El UPDATE de relaciones no cambia ninguna columna de `movie`, pero actualiza igualmente su `updated_at` en la misma transacción, y lo mismo hace el UPDATE de catálogo: así el cambio deja rastro en la película, el seguimiento aguas abajo lo ve y Silver tiene de dónde tomar la fecha del nuevo conteo.
- **Elección del tipo de UPDATE.** La semilla elige la película entre las vivas y, después, el tipo, con la misma probabilidad entre los que esa película admite. El descriptivo, el de medidas y el de relaciones valen para cualquier película; el de catálogo, solo si tiene colección o keywords. Si tiene las dos, la semilla decide entre colección y keyword al 50 % y, entre sus keywords, con la misma probabilidad. No hay pesos por tipo de UPDATE.
- **Renombrado.** El UPDATE de catálogo añade al nombre el sufijo ` (rev 1)`. Si el nombre ya termina en ` (rev N)`, lo sustituye por ` (rev N+1)`: el sufijo no se acumula. El número se lee del nombre que hay en PostgreSQL, así que no depende de la memoria del simulador.
- **DELETE.** Siempre sobre `movie`; las relaciones caen por `ON DELETE CASCADE`.
- **Operación sin candidatas.** Si los pesos piden un UPDATE o un DELETE y no hay ninguna película viva, se ejecuta un INSERT.
- **Modo continuo y reinserción.** Con `SIMULATOR_CONTINUOUS=true`, al agotar `movie.csv` el simulador sigue generando operaciones. Cuando los pesos piden un INSERT y ya no quedan películas pendientes, reinserta una película borrada, elegida con la semilla, con los datos de los archivos; si no hay ninguna borrada, ejecuta un UPDATE. Mientras queden películas pendientes, la reinserción solo se hace a mano. Silver trata la reinserción como una reactivación (sección 31). Con `false`, pasa a `TERMINADO` al agotar `movie.csv`, pero sigue aceptando operaciones manuales.
- **Arranque sobre una base con datos (RF-13).** Al arrancar, el simulador lee de PostgreSQL los `movie_id` de `catalog.movie` y las claves de las once tablas de catálogos y entidades, y las da por insertadas. Continúa con la película siguiente a la última de `movie.csv` que encuentra en la base: las posteriores quedan pendientes, y las anteriores que faltan cuentan como borradas, disponibles para reinsertarse. Así, detener y volver a arrancar el contenedor no repite altas, y sobre una base cargada con el dataset completo (sección 39) el simulador entra directamente en modo continuo. El avance parte de las películas presentes; los contadores de operaciones empiezan en cero en cada arranque. Una película que falló por un dato inconsistente (RF-12) cuenta también como borrada: si se elige para reinsertarla, vuelve a fallar y el simulador continúa. Una consecuencia de la regla, vista en la fase F6: si se inserta a mano una película muy posterior, por ejemplo la última de `movie.csv`, y después se reinicia el contenedor, todas las anteriores que aún no se habían insertado pasan a contar como borradas, no queda ninguna pendiente y el simulador las va reinsertando en el orden que decide la semilla, no en el del archivo.
- **Reproducibilidad.** La semilla gobierna la secuencia automática. Una operación manual o un cambio de pesos la altera a partir de ese punto; ambos quedan en el log para poder reconstruir lo ocurrido. La secuencia se repite cuando se parte de una base vacía y la ejecución es continua: tras un reinicio el simulador sigue con la misma semilla, pero no reproduce la secuencia de la ejecución anterior. Comprobado en la fase F6: dos ejecuciones desde una base vacía con la semilla 42 dieron las mismas 300 primeras transacciones.
- **Contenido de cada UPDATE.** El diseño fija qué columnas toca cada tipo; el valor lo decide la implementación, siempre con la semilla. El descriptivo cambia uno de los cuatro campos por una variante construida sobre el valor del CSV, no sobre el actual, para que los sufijos no se acumulen. El de medidas cambia las seis a la vez, con una variación pequeña; un importe `NULL` sigue `NULL`. El de relaciones decide entre género y keyword, y entre añadir y quitar, al 50 %; si lo elegido no se puede hacer con esa película, hace lo contrario.
- **Velocidad.** Las teclas `+` y `-` recorren estos intervalos: 10, 25, 50, 100, 250, 500, 1000, 2000, 5000 y 10000 ms. A 250 ms el simulador hace unas 3.7 transacciones por segundo; a 10 ms, entre 59 y 65.

### 9.6 Configuración

Valores iniciales, por variables de entorno. Los cuatro primeros se pueden cambiar después desde la interfaz.

| Variable | Significado |
|---|---|
| `SIMULATOR_DELAY_MS` | Intervalo entre transacciones (`250` por defecto) |
| `SIMULATOR_INSERT_WEIGHT` | Peso de INSERT (`70` por defecto) |
| `SIMULATOR_UPDATE_WEIGHT` | Peso de UPDATE (`25` por defecto) |
| `SIMULATOR_DELETE_WEIGHT` | Peso de DELETE (`5` por defecto) |
| `SIMULATOR_RANDOM_SEED` | Semilla de la secuencia automática (`42` por defecto) |
| `SIMULATOR_CONTINUOUS` | Seguir generando cambios al agotar `movie.csv` (`true` por defecto) |
| `SIMULATOR_AUTOSTART` | Empezar a simular al arrancar (`true` por defecto) o esperar en pausa |
| `SIMULATOR_TRACK_BRONZE` | Activar el seguimiento aguas abajo (`true` por defecto) |
| `SIMULATOR_TRACK_INTERVAL_MS` | Intervalo de sondeo de Bronze (5000 por defecto) |
| `SIMULATOR_TRACK_LATE_MS` | Tiempo tras el que una transacción pendiente se marca «demorada» (120000 por defecto) |
| `SIMULATOR_DUCKDB_THREADS` | Hilos de DuckDB (2 por defecto) |
| `SIMULATOR_DUCKDB_MEMORY_LIMIT` | Memoria de DuckDB (`128MB` por defecto) |

Los pesos no forman parte de ninguna restricción del modelo.

Además, el simulador recibe las variables que comparte con otros servicios (sección 45.5): `ELASTIFLIX_APP_PASSWORD` para conectarse a PostgreSQL como `elastiflix_app`, y `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY` para que DuckDB lea Bronze. No recibe `AWS_REGION`: el SQL de inicialización no la usa. El SQL de inicialización lo toma de `duckdb/init/`, montado en solo lectura.

### 9.7 Semántica transaccional

Una película afecta a varias tablas. Su alta se ejecuta en una sola transacción:

```text
BEGIN
  insertar catálogos y entidades que aún no existan
      (status, rating, idioma original, campos de enrichment,
       géneros, keywords, personas, compañías, países, idiomas, colección)
  insertar movie
  insertar movie_collection
  insertar movie_genre
  insertar movie_keyword
  insertar movie_cast
  insertar movie_production_company
  insertar movie_production_country
  insertar movie_spoken_language
  insertar movie_enrichment
COMMIT
```

Flink verá cambios físicos de múltiples tablas originados por las transacciones normales de PostgreSQL.

### 9.8 Tecnología y despliegue

| Pieza | Elección | Motivo |
|---|---|---|
| Interfaz de consola | Lanterna 3.1.5 | Librería Java pura para interfaces de texto a pantalla completa, sin código nativo |
| Seguimiento aguas abajo | DuckDB JDBC 1.5.6.0, con las extensiones `httpfs`, `iceberg` y `avro` instaladas en el build | Misma versión y mismo SQL de inicialización que Superset; evita añadir un cliente de Iceberg propio |
| Lectura de CSV | Apache Commons CSV 1.14.1 | Respeta comillas y saltos de línea dentro de celdas |
| Acceso a PostgreSQL | JDBC 42.7.14 | Transacciones explícitas |
| Pruebas unitarias | JUnit 6.1.3 (`junit-jupiter`), solo en la etapa de build | No va en el JAR: su ámbito en Maven es `test` |

En el Compose, el servicio `java-simulator` declara `tty: true` y `stdin_open: true` para que la interfaz pueda abrirse con `docker compose attach java-simulator`. Cómo se usa, comprobado en la validación 10:

- **Abrir:** tras conectarse se ven pasar las líneas del modo de líneas; cualquier tecla abre la interfaz.
- **Salir:** primero `Q`, que cierra la interfaz, y después la secuencia de desconexión de Docker (`Ctrl-P`, `Ctrl-Q`). Desconectarse con la interfaz abierta no detiene nada, pero deja restos de la pantalla en la terminal; se limpian con `clear`.
- **`Ctrl-C` no detiene el simulador.** Lanterna lo deja pasar por defecto y eso mata el proceso y el contenedor; la terminal se crea con `CtrlCBehaviour.TRAP` para recibirlo como una tecla más.
- **Repintado.** Lanterna solo reescribe las celdas que cambian, así que quien se conecta con la interfaz ya abierta vería la pantalla a medias. La interfaz hace un refresco completo cada 2 segundos y en cada cambio de tamaño.
- **Tamaño.** La interfaz sigue los cambios de tamaño de la ventana. Por debajo del tamaño mínimo muestra un aviso en lugar de la pantalla.
- **Arranque.** Sin nadie conectado, Lanterna tarda unos 5 segundos en inicializar la terminal, porque espera una respuesta de tamaño que no llega, y supone 80×24. Se ajusta sola cuando alguien se conecta. El simulador no paga esa espera al arrancar: crea la pantalla con la primera tecla, no antes, así que el modo de líneas empieza de inmediato. Desde que arranca el proceso hasta la primera transacción pasan unos 4 s, casi todos en cargar los CSV.
- **Logs.** Con la interfaz abierta, `docker compose logs` recibe también las secuencias de dibujo, cerca de 1 KB por segundo, y deja de ser legible. El servicio limita el tamaño de su log en el Compose (`logging`, con `max-size`) y las líneas del RF-11 se escriben además en `/tmp/simulator.log` dentro del contenedor, que se lee con `docker compose exec java-simulator tail -f /tmp/simulator.log`. Se pierde al recrear el contenedor; el laboratorio no lo necesita persistente. Mientras la interfaz está abierta, las líneas de cada transacción solo se escriben en ese archivo, no en la salida del contenedor. El archivo tiene un tope de 20 MB; al llenarse vuelve a empezar.
- **Memoria.** Con los 512 MB del contenedor, la JVM toma por defecto un heap máximo de la cuarta parte, unos 123 MB, y los 20 CSV cargados como texto ocupan 98 MB. La imagen fija el heap de forma explícita con `-XX:MaxRAMPercentage=40` (unos 205 MB), dejando sitio para los 128 MB de DuckDB y el resto de la memoria nativa.
- **SQL de inicialización.** Lee `duckdb/init/attach_lakehouse.sql`, montado en solo lectura; no usa `gold_views.sql`.
- **Detención.** `docker compose stop java-simulator` tarda menos de un segundo y deja el contenedor en `Exited (143)`. Es el código normal de una JVM que recibe la señal de parada, no un error; `docker compose start java-simulator` lo vuelve a arrancar.
- **Log y códigos de error.** El log usa `java.util.logging`, para no añadir una quinta librería. Cada línea lleva la marca de tiempo en UTC y el nivel. Las de transacción empiezan por `TX #n`, las de cambios de configuración por `CONFIG`, las de operaciones manuales por `MANUAL` y las del seguimiento por `BRONZE`. Los errores llevan un código entre corchetes: `SIM-001` configuración, `SIM-010` y `SIM-011` dataset, `SIM-020` a `SIM-024` PostgreSQL y transacciones (`SIM-021` es el dato inconsistente del RF-12), `SIM-030` y `SIM-031` Bronze, y `SIM-040` terminal.
- **Imagen y memoria medidas.** La imagen `elastiflix-simulator:1.0.0` ocupa 661 MB. En marcha, el contenedor usa entre 170 y 240 MiB de sus 512; el máximo visto, tras 10,000 transacciones a 65 por segundo, fue de 336 MiB.
- **Pruebas unitarias.** `java-simulator/src/test/` tiene 71 pruebas en siete clases: lectura de CSV (10), carga del dataset (6), configuración (11), situación de cada película y reanudación (7), selección de la operación con pesos y semilla (19), contenido de los UPDATE (8) y reglas del seguimiento hasta Bronze (10). No cubren la interfaz de consola ni el acceso real a PostgreSQL y a DuckDB, que se comprobaron a mano en la fase F6. Se ejecutan al construir la imagen (`mvn verify` en la etapa de build): si una falla, la imagen no se construye. Dentro de la imagen corren 70 y se salta una, la que carga el dataset real, porque el contexto del build no incluye `raw_data/`; con Maven en el host, desde `java-simulator/`, corren las 71.

Cómo se usa DuckDB dentro del simulador, comprobado en la validación 11:

- **Una conexión de larga vida, con un hilo dueño.** Un hilo dedicado abre la conexión y ejecuta todas las consultas; los demás hilos se las piden a través de un ejecutor de un solo hilo. Esa conexión ve cada snapshot nuevo de Iceberg sin reconectar.
- **Reapertura ante un fallo.** Si una consulta falla, la conexión se cierra y el siguiente sondeo abre otra; inicializarla cuesta unos 40 ms. Cubre el arranque, cuando el simulador puede adjuntar el catálogo antes de que Flink cree las tablas de Bronze. La validación 11 mostró que una conexión adjuntada sin el namespace `bronze` no llega a verlo nunca; con `iceberg-init` el namespace ya existe al arrancar, y el caso de namespace presente sin tablas ocurre en cada arranque desde cero: durante los primeros 15 segundos `bronze.movie` todavía no existe, la consulta falla y la reapertura lo resuelve sola. El simulador lo registra como información, no como aviso (observado en la fase F6).
- **Límites.** La conexión se abre con `threads=2` y `memory_limit=128MB`. Por defecto DuckDB toma todos los núcleos del host y el 80 % de la memoria del contenedor, que sumado al heap de Java supera los 512 MB.
- **Acceso nativo.** La JVM arranca con `--enable-native-access=ALL-UNNAMED`. Sin esa opción, Java 25 avisa en cada arranque y una versión futura bloqueará la carga de la librería.
- **`/tmp` escribible y ejecutable.** El driver extrae ahí su librería nativa, de 60 MB. Si el contenedor fuese de solo lectura, `/tmp` iría en un tmpfs con `exec`. Nada más necesita escritura.
- **Tamaño.** El JAR sin clasificador incluye las librerías de cuatro plataformas (85 MB). El clasificador de la plataforma, `linux_amd64` o `linux_arm64`, pesa 21 MB.

El seguimiento aguas abajo hace que el simulador conozca el catálogo Iceberg y RustFS, cosa que antes no ocurría. Es una dependencia de solo lectura y desactivable; el camino del dato no cambia.

## 10. 🐘 PostgreSQL 19

### Base operacional

```text
Database: elastiflix
Schema:   catalog
```

PostgreSQL representará el estado operacional vigente. El historial analítico será responsabilidad de Silver.

### CDC

PostgreSQL se configurará para logical replication.

Parámetros mínimos a contemplar:

```text
wal_level = logical
max_replication_slots > 0
max_wal_senders > 0
max_slot_wal_keep_size = 2GB
```

El Compose fija `max_replication_slots` y `max_wal_senders` en 10, que es su valor por defecto. `max_slot_wal_keep_size` acota el WAL que el slot puede retener si Flink está detenido; sin él, un Flink caído llena el disco del host. A cambio, si Flink está parado el tiempo suficiente, PostgreSQL invalida el slot y el pipeline ya no puede reanudar desde su checkpoint; ese caso se trata como una pérdida de checkpoints (sección 38).

Objetos de replicación, creados en `postgresql/init/`:

```text
Rol de aplicación:   elastiflix_app   (DML sobre catalog; lo usa el simulador)
Rol de replicación:  elastiflix_cdc   (REPLICATION + SELECT sobre catalog; lo usa Flink)
Publicación:         elastiflix_pub   (FOR TABLES IN SCHEMA catalog)
Slot:                elastiflix_cdc   (plugin pgoutput; lo crea el conector)
```

Las tablas capturadas tendrán primary key y se configurarán con `REPLICA IDENTITY FULL`. No es opcional: el pipeline convierte cada DELETE en un tombstone (sección 14) y necesita la fila completa en el evento de borrado; con la identidad por defecto solo llegaría la clave primaria.

### Imagen y riesgo de versión

- Imagen `postgres:19.0`, con el volumen montado en `/var/lib/postgresql` (ver regla de persistencia, sección 7).
- PostgreSQL 19.0 se publicó el 2026-11-19. Flink CDC 3.7.0 es anterior e incluye Debezium 1.9.8, que no declara soporte para versiones tan nuevas. El protocolo `pgoutput` es estable entre versiones mayores, y la validación 1 del documento de decisiones y validaciones lo confirmó el 2026-11-22: el conector toma el snapshot, lee el WAL y se recupera de una caída contra PostgreSQL 19.0. PostgreSQL 18 deja de ser necesario como respaldo.

## 11. 🔗 Contrato de tipos interoperables

La prioridad es la interoperabilidad, no utilizar indiscriminadamente tipos específicos de PostgreSQL.

### Tipos preferidos

| Tipo de PostgreSQL | Uso |
|---|---|
| `bigint` | Claves |
| `integer` | Conteos y posiciones |
| `numeric(p,s)` | Valores decimales exactos |
| `text` | Texto y códigos |
| `boolean` | Indicadores |
| `date` | Fecha de calendario |
| `timestamp(6) with time zone` | Timestamps operativos |

### Tipos que evitaremos en las tablas CDC

```text
json/jsonb
enum
domain
money
arrays PostgreSQL
range/multirange
citext
inet/cidr
tipos compuestos
tipos vectoriales
```

Las validaciones específicas se implementarán preferentemente con `CHECK`, PK, FK y UNIQUE.

### Decimales

Los decimales siempre declararán precisión y escala explícitas.

```text
budget_usd    numeric(18,2)
revenue_usd   numeric(18,2)
popularity    numeric(10,3)
user_score    numeric(3,1)
vote_average  numeric(5,3)
```

No se utilizará `money`.

## 12. 🧩 Modelo relacional normalizado PostgreSQL

![Diagrama entidad-relación del esquema catalog: 20 tablas agrupadas en catálogos de película, núcleo, procedencia, relaciones N:M y entidades compartidas](diagrams/operational-erd.svg)

> 🔍 **Cómo leerlo:** cada banda de color es un dominio. `movie` es el centro: apunta a tres catálogos (izquierda) y de ella cuelgan ocho tablas de relación. Las seis de la banda «Relaciones N:M» enlazan con su entidad compartida a la derecha.
>
> Versión interactiva: [`diagrams/operational-erd.html`](diagrams/operational-erd.html) · Fuente editable: [`diagrams/operational-erd.json`](diagrams/operational-erd.json).

### 12.1 Inventario

Entidades/catálogos:

```text
movie
collection
genre
keyword
person
production_company
production_country
original_language
spoken_language
movie_status
content_rating
enrichment_field
```

Relaciones:

```text
movie_collection
movie_genre
movie_keyword
movie_cast
movie_production_company
movie_production_country
movie_spoken_language
movie_enrichment
```

### 12.2 `movie`

Clave natural: TMDB `movie_id`.

```text
movie_id                bigint PK
imdb_id                 text NULL
title                   text NOT NULL
original_title          text NOT NULL
original_language_code  text NOT NULL FK
overview                text NULL
plot                    text NOT NULL
tagline                 text NULL
status_code             text NOT NULL FK
rating_code             text NULL FK
release_date            date NOT NULL
runtime_minutes         integer NULL
budget_usd              numeric(18,2) NULL
revenue_usd             numeric(18,2) NULL
popularity              numeric(10,3) NOT NULL
user_score              numeric(3,1) NULL
vote_average            numeric(5,3) NULL
vote_count              integer NULL
adult                   boolean NOT NULL
video                   boolean NOT NULL
homepage                text NULL
poster_path             text NULL
backdrop_path           text NULL
created_at              timestamptz NOT NULL
updated_at              timestamptz NOT NULL
```

Reglas principales:

- `movie_id > 0`.
- `imdb_id`, cuando exista, debe respetar el patrón documentado `tt` + 7/8 dígitos.
- `runtime_minutes > 0` cuando no sea null.
- `budget_usd` y `revenue_usd` mantienen `NULL` como ausencia; no se reemplazan por cero.
- `popularity >= 0`.
- scores entre 0 y 10.
- `vote_count >= 0` cuando exista; una película sin votos es un dato válido.
- `homepage` acepta únicamente valores HTTP/HTTPS cuando está presente.
- `poster_path` y `backdrop_path` son rutas relativas: empiezan por `/` y no llevan servidor.
- `created_at` y `updated_at` tienen `DEFAULT now()`; el simulador actualiza `updated_at` en cada UPDATE.

Índice único parcial previsto para `imdb_id` cuando no es null. `poster_path` no será único: dos películas pueden compartir imagen y un UPDATE puede repetirla.

> ℹ️ **`NOT NULL` confirmados por el perfilado.** `original_title`, `plot`, `release_date` y `popularity` se declaran `NOT NULL`: el perfilado del índice original no encontró ningún nulo en ellas y el dataset las trae siempre pobladas.

### 12.3 `collection`

```text
collection_id   bigint PK
name            text NOT NULL
created_at      timestamptz NOT NULL
updated_at      timestamptz NOT NULL
```

El nombre no será UNIQUE porque existen IDs distintos con el mismo nombre.

Los `poster_path` y `backdrop_path` observados no son atributos estables de la entidad. Se preservarán en `movie_collection`.

### 12.4 `movie_collection`

```text
movie_id                bigint PK/FK
collection_id           bigint NOT NULL FK
observed_poster_path    text NULL
observed_backdrop_path  text NULL
```

Representa la relación película 0..1 colección. No lleva `source_position`: una película pertenece como máximo a una colección, así que no hay orden que preservar.

### 12.5 `genre`

```text
genre_id   bigint PK
name       text UNIQUE NOT NULL
```

`genre_id` es una clave sustituta que asigna el dataset, consecutiva desde 1 (sección 8.4); PostgreSQL no la genera y el simulador inserta el valor del archivo. Lo mismo vale para `person_id`, `company_id`, `country_id` y `spoken_language_id`.

### 12.6 `movie_genre`

```text
movie_id        bigint FK
genre_id        bigint FK
source_position integer NOT NULL
PK(movie_id, genre_id)
UNIQUE(movie_id, source_position)
```

> ℹ️ **Regla común a las tablas de relación con lista ordenada** (`movie_genre`, `movie_keyword`, `movie_production_company`, `movie_production_country`, `movie_spoken_language`): `source_position` es `NOT NULL`, empieza en 1 y es `UNIQUE` junto con `movie_id`. `movie_cast` usa `billing_order` con la misma regla.

### 12.7 `keyword`

```text
keyword_id  bigint PK
name        text NOT NULL
created_at  timestamptz NOT NULL
updated_at  timestamptz NOT NULL
```

No habrá `UNIQUE(name)`: en el dataset hay nombres compartidos por dos `keyword_id` distintos (sección 8.6).

Cada `keyword_id` llega con un único nombre. El índice original traía algunos identificadores con dos nombres; el dataset los entrega ya resueltos (sección 8.6), así que el simulador no tiene nada que arbitrar.

### 12.8 `movie_keyword`

```text
movie_id        bigint FK
keyword_id      bigint FK
source_position integer NOT NULL
PK(movie_id, keyword_id)
UNIQUE(movie_id, source_position)
```

### 12.9 `person`

```text
person_id   bigint PK
name        text UNIQUE NOT NULL
created_at  timestamptz NOT NULL
```

La unicidad es técnica por nombre exacto del dataset. No implica que sea posible resolver homónimos reales.

Solo las tablas que el simulador modifica (`movie`, `collection` y `keyword`) llevan `created_at` y `updated_at`. `person` lleva únicamente `created_at`, que nadie usa aguas abajo; el resto de entidades y catálogos no lleva ninguna de las dos, y Silver toma para ellas `cdc_op_ts` (sección 21).

### 12.10 `movie_cast`

```text
movie_id       bigint FK
person_id      bigint FK
billing_order  integer NOT NULL
PK(movie_id, person_id)
UNIQUE(movie_id, billing_order)
```

Se preservará el orden de facturación. El dataset garantiza que una persona no se repite en el reparto de una película (sección 8.2).

### 12.11 `production_company`

```text
company_id  bigint PK
name        text UNIQUE NOT NULL
```

No se fusionarán automáticamente variantes de nombres de estudios.

### 12.12 `movie_production_company`

```text
movie_id        bigint FK
company_id      bigint FK
source_position integer NOT NULL
PK(movie_id, company_id)
UNIQUE(movie_id, source_position)
```

### 12.13 `production_country`

```text
country_id  bigint PK
name        text UNIQUE NOT NULL
```

PostgreSQL/Bronze preservarán los valores fuente incluso cuando tengan problemas de calidad, por ejemplo `Guadaloupe`. Su estandarización pertenece a Silver.

### 12.14 `movie_production_country`

```text
movie_id        bigint FK
country_id      bigint FK
source_position integer NOT NULL
PK(movie_id, country_id)
UNIQUE(movie_id, source_position)
```

### 12.15 `original_language`

```text
language_code  text PK
description    text NULL
```

La validación permitirá códigos de dos letras usados por el dataset, incluido `cn` como convención TMDB.

### 12.16 `spoken_language`

```text
spoken_language_id  bigint PK
name                text UNIQUE NOT NULL
```

`No Language` es un valor válido, no un null.

### 12.17 `movie_spoken_language`

```text
movie_id            bigint FK
spoken_language_id  bigint FK
source_position     integer NOT NULL
PK(movie_id, spoken_language_id)
UNIQUE(movie_id, source_position)
```

### 12.18 `movie_status`

Inicialmente contiene `Released`, pero se implementa como tabla y no como ENUM para permitir evolución.

```text
status_code text PK
```

### 12.19 `content_rating`

Valores iniciales documentados:

```text
G
PG
PG-13
R
NC-17
NR
TV-PG
```

```text
rating_code text PK
```

### 12.20 `enrichment_field`

Catálogo de los 21 campos documentados de `enrichment`: `backdrop_path`, `belongs_to_collection`, `budget`, `cast`, `genres`, `homepage`, `imdb_id`, `keywords`, `overview`, `plot`, `poster_path`, `production_companies`, `production_countries`, `rating`, `revenue`, `runtime`, `spoken_languages`, `tagline`, `user_score`, `vote_average`, `vote_count`.

```text
field_name text PK
```

### 12.21 `movie_enrichment`

```text
movie_id    bigint FK
field_name  text FK
code        text NOT NULL
PK(movie_id, field_name)
```

Los códigos permanecen abiertos porque existen familias como:

```text
wikipedia_infobox_fx:<MONEDA>:<AÑO>
```

## 13. Política de DELETE en PostgreSQL

Un `DELETE` sobre `movie` eliminará sus relaciones mediante `ON DELETE CASCADE`, pero no eliminará las entidades compartidas.

Se eliminarán las asociaciones:

```text
movie_collection
movie_genre
movie_keyword
movie_cast
movie_production_company
movie_production_country
movie_spoken_language
movie_enrichment
```

No se eliminarán automáticamente:

```text
collection
genre
keyword
person
production_company
production_country
spoken_language
```

No se utilizará `deleted_at` para simular borrados: la aplicación realizará DELETE físicos para que CDC observe eliminaciones reales.

Cada fila borrada por la cascada genera su propio evento de DELETE en el WAL, de modo que Bronze recibe un tombstone por la película y uno por cada relación eliminada.

## 14. 🌊 Flink CDC

Flink CDC será responsable de:

1. Snapshot inicial cuando corresponda.
2. Lectura continua del WAL de PostgreSQL.
3. Captura de INSERT, UPDATE y DELETE.
4. Escritura de tablas Bronze en Iceberg.
5. Mantener el pipeline CDC ejecutándose continuamente.

Bronze reproducirá el modelo PostgreSQL tabla por tabla.

Ejemplos:

| Tabla en PostgreSQL | Tabla en Bronze |
|---|---|
| `catalog.movie` | `bronze.movie` |
| `catalog.collection` | `bronze.collection` |
| `catalog.movie_genre` | `bronze.movie_genre` |
| `catalog.movie_cast` | `bronze.movie_cast` |
| `catalog.movie_enrichment` | `bronze.movie_enrichment` |

Las modificaciones DDL deberán coordinarse deliberadamente entre PostgreSQL y el pipeline; no se asumirán cambios de esquema transparentes desde el WAL. La opción `schema-change.enabled` del conector queda en su valor por defecto (`false`).

### Forma del pipeline

El pipeline se define en un único YAML (`flink/jobs/postgres-to-bronze.yaml`) y lo envía el job one-shot `flink-cdc-submit`. Usa tres capacidades documentadas de Flink CDC 3.7:

| Necesidad | Mecanismo de Flink CDC |
|---|---|
| Saber cuándo ocurrió cada cambio | `metadata.list: op_ts` en la fuente PostgreSQL (milisegundos desde epoch; en filas del snapshot inicial es el instante en que el conector leyó la fila, no `0`) |
| Saber qué operación fue | campo de metadatos `__data_event_type__` en `transform` |
| No perder los DELETE | `converter-after-transform: SOFT_DELETE`, que convierte el borrado en una inserción marcada `-D` |

El pipeline parte de la guía oficial de Flink CDC «Real-time PostgreSQL Ingestion into Iceberg», que cubre snapshot inicial, INSERT, UPDATE y DELETE con PostgreSQL, `pgoutput` y `REPLICA IDENTITY FULL`. Respecto a esa guía, este laboratorio cambia dos cosas: el catálogo (REST sobre RustFS en lugar de Hadoop sobre disco local) y el bloque `transform`. Ambas pasaron las validaciones 2 y 3 del documento de decisiones y validaciones con el borrador de abajo, sin modificarlo.

Borrador:

```yaml
source:
  type: postgres
  hostname: postgresql
  port: 5432
  username: elastiflix_cdc
  password: ${ELASTIFLIX_CDC_PASSWORD}
  tables: elastiflix.catalog.\.*
  slot.name: elastiflix_cdc
  decoding.plugin.name: pgoutput
  scan.startup.mode: initial
  table-id.include-database: false
  metadata.list: op_ts
  debezium.publication.name: elastiflix_pub
  debezium.publication.autocreate.mode: disabled

transform:
  - source-table: catalog.\.*
    projection: \*, __data_event_type__ AS cdc_op_type, op_ts AS cdc_op_ts
    converter-after-transform: SOFT_DELETE

route:
  - source-table: catalog.\.*
    sink-table: bronze.<>
    replace-symbol: <>

sink:
  type: iceberg
  catalog.properties.catalog-impl: org.apache.iceberg.rest.RESTCatalog
  catalog.properties.uri: http://iceberg-rest:8181
  catalog.properties.warehouse: s3://warehouse/
  catalog.properties.io-impl: org.apache.iceberg.aws.s3.S3FileIO
  catalog.properties.s3.endpoint: http://rustfs:9000
  catalog.properties.s3.path-style-access: true
  table.properties.format-version: 2

pipeline:
  name: elastiflix-postgres-to-bronze
  parallelism: 1
  local-time-zone: UTC
```

Puntos que conviene no pasar por alto:

- **Identificador de tabla.** `tables` usa `base.esquema.tabla`, pero con `table-id.include-database: false` (su valor por defecto) el identificador que ven `transform` y `route` es `esquema.tabla`. Por eso ambos bloques usan `catalog.\.*` y no `elastiflix.catalog.\.*`.
- **Publicación.** El conector reutiliza la publicación `elastiflix_pub` creada en `postgresql/init/` (`autocreate.mode: disabled`) y crea él mismo el slot al arrancar.
- **Creación de tablas.** El conector crea automáticamente las tablas de Bronze; no hay DDL de Bronze que mantener. Las crea al arrancar el pipeline, aunque las tablas de PostgreSQL estén vacías (comprobado en la fase F5), pero no en el mismo instante en que el job pasa a `RUNNING`: van apareciendo durante los 15 o 20 segundos siguientes. En el primer arranque el simulador ya está insertando en ese intervalo; no se pierde nada, porque esas filas llegan por streaming en cuanto existe su tabla (observado en la fase F6). El namespace `bronze` lo crea antes `iceberg-init` (sección 16); el conector también lo crearía si faltara.
- **Contraseña.** El YAML versionado lleva el marcador `${ELASTIFLIX_CDC_PASSWORD}`. No consta que `flink-cdc.sh` sustituya variables de entorno, así que `flink-cdc-submit` genera, dentro del contenedor y fuera del repositorio, una copia con el valor de `.env` (por ejemplo con `envsubst`) y envía esa copia.
- **Formato v2.** Se fija `format-version: 2`, que es el que soporta el flujo de UPDATE y DELETE.

### Garantías y requisitos operativos

- **Checkpointing obligatorio.** El sink de Iceberg publica los datos en cada checkpoint de Flink; sin checkpointing Bronze queda vacío. `execution.checkpointing.interval` es de 30 s y los checkpoints se guardan en `flink/data/`.
- **At-least-once.** El sink no ofrece exactly-once: reintenta y se apoya en la clave primaria para escribir de forma idempotente. Por eso todas las tablas capturadas tienen PK.
- **Una sola base.** El conector PostgreSQL captura tablas de una única base de datos; `elastiflix` cumple.
- **Catálogo REST.** La documentación del sink enumera los tipos `hadoop`, `hive` y `glue`, además de `catalog-impl` para una implementación propia. El catálogo REST se configura por esa segunda vía, como muestra el borrador; la validación 2 confirmó que funciona.
- **Credenciales S3.** El borrador no lleva claves. `S3FileIO` las toma de las variables de entorno `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` y `AWS_REGION`, que deben declararse tanto en `flink-jobmanager` como en `flink-taskmanager`. Así las credenciales viven en `.env` y no en el YAML del pipeline.
- **Dependencias en la imagen de Flink.** Las que lista la guía oficial para Flink 2.2.1: la distribución de Flink CDC 3.7.0 para Flink 2.2, los conectores `flink-cdc-pipeline-connector-postgres` y `flink-cdc-pipeline-connector-iceberg` (`3.7.0-2.2`) en `$FLINK_CDC_HOME/lib`, y en `$FLINK_HOME/lib` el `iceberg-flink-runtime-2.0`, Hadoop client API y runtime 3.3.6 y Commons Logging 1.2. La guía usa Iceberg 1.10.1; este laboratorio toma el último parche de esa línea, 1.10.2, y añade `iceberg-aws-bundle` 1.10.2 para `S3FileIO`. Hadoop se mantiene en la 3.3.6 que indica la guía aunque exista la 3.5.0, porque forma parte del conjunto probado con el conector. El conector PostgreSQL ya incluye su driver JDBC.
- **Reinicio.** Si cae el TaskManager, el job se recupera solo desde su último checkpoint. Si se reinicia el JobManager, el job se pierde: el clúster standalone no tiene alta disponibilidad y arranca sin jobs. Hay que reenviar el pipeline con `--from-savepoint` apuntando al último checkpoint retenido; así retoma sin repetir el snapshot y entrega lo que cambió mientras estuvo parado. No ocurre solo: basta con repetir `docker compose up`, que vuelve a ejecutar `flink-cdc-submit`, y este reanuda desde el checkpoint (punto siguiente). El slot de replicación permanece en PostgreSQL entre tanto.
- **Checkpoints retenidos y compartidos.** Para que ese reenvío sea posible, los checkpoints se guardan en `flink/data/`, montado en la misma ruta en el JobManager y en el TaskManager, con `execution.checkpointing.dir: file:///opt/flink/state/checkpoints` y `execution.checkpointing.externalized-checkpoint-retention: RETAIN_ON_CANCELLATION`. Flink corre como usuario `flink`: el directorio debe pertenecerle antes de arrancar.
- **`flink-cdc-submit` idempotente de verdad.** El job one-shot sigue esta regla cada vez que se ejecuta:
  1. Consulta la API REST de Flink. Si ya hay un job en ejecución con el nombre del pipeline, termina sin hacer nada.
  2. Si no lo hay y existe un checkpoint retenido en `flink/data/`, reenvía con `--from-savepoint` hacia el más reciente.
  3. Solo si no hay ni job ni checkpoint hace un envío nuevo, con snapshot inicial. Si en ese momento Bronze ya tiene tablas, se trata de una pérdida de estado: el job no envía nada, termina con error y remite a la reconstrucción de Bronze (punto siguiente).
  4. Tras enviar o reanudar, espera a que la API REST muestre el job en `RUNNING` y solo entonces termina con código 0. Si no llega a ese estado en 2 minutos, termina con error. Así, quien depende de `flink-cdc-submit` arranca con el pipeline ya capturando.

  Sin esta regla, repetir `docker compose up` es dañino. Un segundo envío no falla: Flink lo acepta y arranca otro job que repite el snapshot completo sobre las mismas tablas. Bronze sigue cuadrando en filas, pero todas vuelven a `+I` con el `cdc_op_ts` del nuevo snapshot, se pierde la marca `+U` y la fecha real de cada cambio, y se acumula un delete de igualdad por cada fila reescrita.
- **Perder los checkpoints no es inocuo.** Un envío nuevo repite el snapshot, pero el snapshot solo ve lo que existe: una fila borrada en PostgreSQL mientras no había job no vuelve a leerse y queda en Bronze como viva, sin tombstone. En la prueba del documento de decisiones y validaciones, 3 películas borradas durante la parada y 89 filas de sus relaciones siguieron contando como vivas. Por eso los checkpoints se persisten y, si aun así se pierden, Bronze no se repara: se reconstruye desde cero con el procedimiento de la sección 38, en lugar de repetir el snapshot sobre las tablas existentes.

## 15. 🪣 RustFS

RustFS será el object storage S3-compatible local.

Conceptualmente:

```text
s3://warehouse/
  bronze/
  silver/
  gold/
```

Los archivos físicos Iceberg, incluyendo datos Parquet y metadata asociada, residirán en RustFS.

Persistencia: el volumen con nombre `rustfs-data` de Docker, no un directorio del repositorio (ver más abajo).

Los demás servicios no manipularán directamente ese volumen. Accederán mediante el endpoint S3.

Detalles de operación:

- Imagen `rustfs/rustfs:1.0.6`; API S3 en el puerto 9000 y consola en el 9001. La consola se abre en `/rustfs/console/`; la raíz del 9001 responde 403.
- El contenedor corre como `10001:10001`; su volumen de datos debe ser escribible por ese usuario, y `volumes-init` se lo deja así.
- Credenciales por las variables `RUSTFS_ACCESS_KEY` y `RUSTFS_SECRET_KEY`; healthcheck contra `/health/ready`, que no pide credenciales.
- Logs por la salida estándar, con `RUSTFS_OBS_LOG_STDOUT_ENABLED=true`, como en el quickstart de Iceberg; así se ven con `docker compose logs rustfs`.
- **Aviso de sistema de archivos.** Hasta la fase F9 los datos iban en un directorio del repositorio, `rustfs/data`. En Docker Desktop sobre Windows ese directorio llegaba al contenedor como V9FS, y RustFS avisaba al arrancar de que solo admite sistemas de archivos POSIX locales para producción. Es un aviso, no un error: en la fase F4 arrancó, guardó y devolvió objetos, uno de ellos de 20 MB, y los conservó tras recrear el contenedor. En la fase F5 aguantó el dataset completo bajo la carga de Flink. Es el riesgo R10 del plan.
- **RustFS no aguanta la carga del laboratorio sobre este montaje; observado en las fases F7 y F9.** Bajo carga de escritura y borrado deja de responder a tiempo, registra miles de avisos (`disk_operation_slow`, `disk_health_check_failed`), marca su disco como defectuoso y devuelve 503 por ráfagas. El contenedor sigue figurando sano. Consecuencias medidas: `bronze_to_silver` pasa de unos 90 s a entre 5 y 9 minutos; un 503 termina el TaskManager de Flink con un error fatal, y el pipeline queda parado hasta que se arranca a mano; los borrados por lote de `iceberg_maintenance` agotan la espera del cliente; y una lectura de un archivo de 22 KB llegó a tardar 25 s. En la fase F7 pareció que la causa era el proceso de fondo `scanner`, que arranca a la hora; en la F9 se descartó que sea la única: con `RUSTFS_SCANNER_ENABLED=false` el fallo apareció igual a los 34 minutos, y añadiendo `RUSTFS_DURABILITY_MODE=relaxed`, a los 17. Las dos variables existen en la 1.0.6 (comprobado en su código y en el binario) y ninguna se dejó en el Compose. La explicación más probable, respaldada por una microprueba y no demostrada: sobre el montaje de Windows renombrar y borrar cuesta unas 13 veces más que sobre el disco de Docker, y RustFS guarda cada objeto como un directorio con varios archivos. Por eso los datos pasaron a un volumen con nombre.
- **Datos en el volumen `rustfs-data`, desde la fase F9 (decisión 67).** Es la única excepción a la regla de un directorio por servicio (sección 7). En el volumen los datos viven en el disco de Docker, sin cruzar la capa que comparte directorios con Windows. Medido con la misma carga que antes lo tumbaba, con Flink y el simulador escribiendo a la vez: `iceberg_maintenance` completo en 193 s la primera vez y 123 s la segunda, sin ninguna respuesta 503, sin lotes de borrado fallidos y sin avisos de lentitud; el TaskManager no cayó; contar `bronze.movie_cast` con DuckDB pasó de 87–89 s a 3 s; y borrar las 20 tablas de Bronze, de 49 s a 19 s. Lo que se pierde: los datos no se ven desde Windows ni están dentro del repositorio, y se borran con `docker volume rm elastiflix-cdc-lakehouse_rustfs-data`, no vaciando un directorio. Los 18,447 archivos que había en `rustfs/data/` se copiaron al volumen con todo detenido; tardó 32 minutos. La copia antigua se borró después, y el directorio `rustfs/` se retiró del repositorio (decisión 69).
- **Sustituto evaluado: SeaweedFS 4.55.** En un entorno de Compose aparte, con sus datos en un directorio de la unidad E:, pasó 81 minutos de carga continua sin ninguna respuesta 5xx: borra 250 objetos en 0.6 s, `bronze_to_silver` tardó entre 68 y 82 s en 25 corridas sin degradarse, usó como máximo 750 MiB de 1 GiB y mantuvo entre 91 y 117 archivos en su directorio, porque empaqueta los objetos en pocos archivos que solo crecen. Adoptarlo conservaría la regla de un directorio por servicio. Tres condiciones: apagar su telemetría (`-master.telemetry=false`), vigilar su memoria, que subía despacio, y decidir aparte si `flink-taskmanager` debe reiniciarse solo. No se adoptó: la persona responsable decidió seguir con RustFS sobre el volumen, que ya estaba hecho y probado y es el cambio menor (decisión 67). El entorno de prueba se eliminó una vez tomada la decisión.
- **El montaje de Windows sigue siendo un riesgo para los demás servicios.** Durante la copia de esos 18,447 archivos, con dos laboratorios trabajando a la vez sobre la unidad E:, el PostgreSQL operacional y el del entorno de evaluación se detuvieron en el mismo minuto con «Cannot allocate memory» al escribir y al leer sus archivos. No fue falta de memoria de los contenedores. Los dos se recuperaron solos al arrancar. Es el riesgo R10 del plan.
- El job one-shot `rustfs-init` crea el bucket `warehouse` si no existe, con una petición S3 firmada. Es el mismo patrón que usa el quickstart de Spark del proyecto Iceberg, que ya emplea RustFS como object store: reutiliza la propia imagen `rustfs/rustfs`, que incluye `curl`, y firma con `curl --aws-sigv4`. No hace falta una imagen de cliente S3 aparte.
- Todos los clientes (Flink, Spark, DuckDB y el catálogo) usan el mismo endpoint interno `http://rustfs:9000` con acceso path-style.
- RustFS 1.0 incluye un Iceberg REST Catalog propio («S3 Tables»), pero está marcado como *preview*. No se usa en este laboratorio; el catálogo es un servicio aparte (sección 16).

## 16. 🧭 Iceberg REST Catalog

Existirá como servicio independiente.

Clientes:

```text
Flink CDC
PySpark
DuckDB
```

Será la capa común de descubrimiento y coordinación de las tablas Iceberg almacenadas en RustFS.

DuckDB será cliente del catálogo, no propietario exclusivo de este.

### Implementación

- Imagen `apache/iceberg-rest-fixture:1.10.1`, la implementación de referencia del proyecto Iceberg. Está pensada para pruebas, lo cual es adecuado para un laboratorio local; no es una recomendación para producción.
- **Configuración.** La imagen traduce variables `CATALOG_*` a propiedades del catálogo. Las que usa el quickstart oficial de Iceberg son `CATALOG_WAREHOUSE=s3://warehouse/`, `CATALOG_IO__IMPL=org.apache.iceberg.aws.s3.S3FileIO`, `CATALOG_S3_ENDPOINT=http://rustfs:9000` y `CATALOG_S3_PATH__STYLE__ACCESS=true`, además de las credenciales `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` y `AWS_REGION`.
- **Persistencia.** La imagen trae `CATALOG_URI=jdbc:sqlite:/tmp/iceberg_catalog.db`: el catálogo es un archivo dentro del contenedor. Sobrevive a un reinicio, pero se pierde al recrear el contenedor (`docker compose down` o un cambio en el servicio), y entonces las tablas dejarían de existir para los motores aunque sus archivos siguieran en RustFS. Se fija `CATALOG_URI=jdbc:sqlite:/catalog/iceberg_catalog.db` y se monta `./iceberg/data` en `/catalog`. La validación 4 confirmó que así las tablas sobreviven a la recreación del contenedor, también con el directorio en una unidad NTFS de Windows.
- **Healthcheck.** La imagen ya declara uno (`curl` contra `/v1/config`); el Compose puede usar `condition: service_healthy` sin definirlo.
- **Una sola conexión a SQLite** (`CATALOG_CLIENTS: "1"`). Con las dos que la imagen abre por defecto, cuando el catálogo arranca sobre un archivo que ya existe una de ellas se queda con un bloqueo de lectura permanente, y los commits que le tocan a la otra fallan con «database is locked» tras agotar su espera. Cada commit rechazado reinicia el pipeline de Flink, que entra en un bucle. Observado en la fase F9, la primera vez que el catálogo se reinició con Flink escribiendo; el bloqueo se ve en `/proc/locks` del contenedor. Con una conexión no volvió a ocurrir. No se ha investigado por qué esa conexión conserva el bloqueo.
- El job one-shot `iceberg-init` crea los namespaces `bronze`, `silver` y `gold` con `POST /v1/namespaces` contra el catálogo, desde la imagen de RustFS, que trae `curl`, igual que `rustfs-init`. Si un namespace ya existe, la respuesta `409` cuenta como éxito, así que el job es idempotente.
- Sin autenticación: el catálogo solo es alcanzable dentro de la red del Compose y, desde la propia máquina, en `127.0.0.1`.
- Alternativas si la imagen de referencia se queda corta: Lakekeeper o Apache Polaris. Cambiar de catálogo no altera el resto del diseño porque todos los motores hablan el protocolo REST.

## 17. 🥉 Capa BRONZE

### Objetivo

Réplica relacional `as-is` del sistema operacional PostgreSQL.

No se realiza modelado dimensional en esta capa.

Inventario:

```text
bronze.movie
bronze.collection
bronze.movie_collection
bronze.genre
bronze.movie_genre
bronze.keyword
bronze.movie_keyword
bronze.person
bronze.movie_cast
bronze.production_company
bronze.movie_production_company
bronze.production_country
bronze.movie_production_country
bronze.original_language
bronze.spoken_language
bronze.movie_spoken_language
bronze.movie_status
bronze.content_rating
bronze.enrichment_field
bronze.movie_enrichment
```

Bronze conserva problemas de calidad de la fuente. Las correcciones pertenecen a Silver.

### Semántica de Bronze

Cada tabla Bronze tiene las mismas columnas que su tabla PostgreSQL, más dos columnas técnicas:

```text
cdc_op_type  string   operación del último evento: +I (insert), +U (update), -D (delete)
cdc_op_ts    bigint   instante del cambio en PostgreSQL, en milisegundos; en filas del snapshot inicial, instante de lectura
```

Los tres valores se confirmaron en la validación 3 del documento de decisiones y validaciones. Las filas del snapshot inicial llegan como `+I`.

Reglas:

- **Una fila por clave primaria**, con el último estado conocido. Bronze no es un log de eventos.
- **Un DELETE no borra la fila**: la deja con `cdc_op_type = '-D'` y los valores que tenía al borrarse. Así Silver puede cerrar versiones y marcar hechos como eliminados.
- **Una reinserción** de la misma clave sobrescribe el tombstone con `cdc_op_type = '+I'`.
- **Limitación aceptada:** si una fila cambia varias veces entre dos corridas de `bronze_to_silver`, Silver solo ve el último estado. Los cambios intermedios no generan versiones SCD2. Para un laboratorio demostrativo es suficiente; si se necesitara cada cambio, la extensión natural es una segunda tabla Bronze append-only por entidad.

Formato: Iceberg v2. Flink escribe los cambios como deletes de igualdad más inserciones, lo que acumula archivos pequeños; por eso Bronze requiere compactación periódica desde el inicio (sección 38).

## 18. ⏱️ Apache Airflow

Airflow gobernará el procesamiento analítico por lotes: los jobs PySpark de Silver, Gold, validación y mantenimiento. No toca Superset.

Pipeline lógico (DAG `elastiflix_medallion`):

![DAG de Airflow: validate_bronze, bronze_to_silver, validate_silver, silver_to_gold, validate_gold e iceberg_maintenance, la tarea mark_run_failed que solo corre si alguna falló, y los jobs PySpark y las capas Iceberg que tocan](diagrams/airflow-medallion-dag.svg)

> 🔍 **Cómo leerlo:** la fila superior es el DAG, de izquierda a derecha. La segunda fila es `mark_run_failed`, que solo corre si alguna tarea falló y deja la corrida en error. Cada tarea de transformación lanza un job PySpark (tercera fila) que lee una capa y escribe la siguiente (fila inferior). Cada `validate_*` consulta la capa de su mismo nombre. `iceberg_maintenance` corre siempre al final, aunque falle una validación.
>
> Versión interactiva: [`diagrams/airflow-medallion-dag.html`](diagrams/airflow-medallion-dag.html) · Fuente editable: [`diagrams/airflow-medallion-dag.json`](diagrams/airflow-medallion-dag.json).

Tareas:

| Tarea | Qué hace | Si falla |
|---|---|---|
| `validate_bronze` | Comprueba que existen las 20 tablas y que el job de Flink está en `RUNNING`, consultando la API REST de Flink. No exige actividad reciente: con el simulador en pausa Bronze puede estar quieto | El DAG se detiene; Silver conserva su último estado |
| `bronze_to_silver` | `SparkSubmitOperator` sobre `bronze_to_silver.py` | Se reintenta; el job es idempotente |
| `validate_silver` | Una sola versión vigente por business key, rangos SCD2 sin solapes, sin SK huérfanas | El DAG se detiene; Gold conserva su último estado |
| `silver_to_gold` | `SparkSubmitOperator` sobre `silver_to_gold.py` | Se reintenta; Gold se recarga completo |
| `validate_gold` | Cada producto existe, tiene filas y sus claves no son nulas ni se repiten | El DAG queda en error. Gold ya se recargó y no se revierte: Superset muestra esa carga, que no es fiable, hasta la corrida siguiente |
| `iceberg_maintenance` | Compacta Bronze y expira los snapshots antiguos de Bronze, Silver y Gold, conservando los 5 últimos de cada tabla. Corre siempre al final, aunque falle una tarea anterior (`trigger_rule = all_done`), y omite las tablas que todavía no existen | No bloquea la corrida siguiente |
| `mark_run_failed` | No lanza ningún job. Solo se ejecuta si alguna tarea anterior falló, y entonces falla ella: deja la corrida en error. Airflow decide el estado de una corrida por sus tareas finales, y `iceberg_maintenance` corre siempre y suele terminar bien; sin esta tarea, una corrida con una validación fallida figuraría como correcta | Si todas las tareas van bien se omite y la corrida queda en `success` |

Si una validación falla, las tareas siguientes no corren, salvo `iceberg_maintenance`. Las validaciones son jobs PySpark cortos con aserciones, uno por tarea (`validate_bronze.py`, `validate_silver.py` y `validate_gold.py` en `pyspark/jobs/`), lanzados con `SparkSubmitOperator` como las transformaciones. No se añade un framework de calidad de datos.

Airflow no gobernará cada evento CDC.

### Despliegue de Airflow

- Imagen propia basada en `apache/airflow:3.4.0-python3.12`, con Java 21, PySpark 4.1.4 y `apache-airflow-providers-apache-spark` 6.3.4. La versión de PySpark del cliente debe coincidir con la del clúster Spark.
- El proveedor 6.3.4 depende de `pyspark-client>=4.0.0` sin tope superior, así que por sí solo instalaría la 4.3.0. Se fijan `pyspark==4.1.4` y `pyspark-client==4.1.4` en el mismo `pip install`.
- **Misma versión menor de Python en Airflow y en Spark.** `SparkSubmitOperator` lanza `spark-submit` en modo cliente contra el clúster standalone, que no admite modo clúster para aplicaciones Python. El driver corre entonces dentro del contenedor de Airflow y los ejecutores dentro de `spark-worker`; si sus versiones menores de Python difieren, PySpark aborta el job. La imagen base de Spark trae Python 3.10 (Ubuntu 22.04) y Airflow no publica imagen con 3.10, por lo que `pyspark/Dockerfile` instala Python 3.12 y fija `PYSPARK_PYTHON` a ese intérprete. La validación 8 del documento de decisiones y validaciones reprodujo el fallo y comprobó la solución.
- **Cómo se instala Python 3.12 en la imagen de Spark.** Con `uv`: `pip3 install uv`, `uv python install 3.12` con `UV_PYTHON_INSTALL_DIR=/opt/python` y un enlace `/usr/local/bin/python3.12`. La imagen fija `uv` 0.13.9, comprobando el SHA-256 de su wheel con `pip --require-hashes`, y Python 3.12.16; al terminar retira `uv`, que en ejecución no hace falta. No toca el Python 3.10 del sistema ni añade repositorios de paquetes. La imagen declara `PYSPARK_PYTHON=python3.12`, y la de Airflow también: el driver comunica a los ejecutores el nombre del intérprete y cada lado lo resuelve en su `PATH`.
- **Solo fallan los jobs que ejecutan Python en los ejecutores.** Un job que use únicamente la API de DataFrame corre aunque las versiones no coincidan; una UDF de Python o una operación sobre RDD aborta con `PYTHON_VERSION_MISMATCH`. No conviene apoyarse en esa diferencia: basta una UDF para romper un job que antes funcionaba.
- **Lo que necesita la imagen de Airflow para ser driver.** Java 21 (`openjdk-21-jre-headless`, con `JAVA_HOME`), los JAR `iceberg-spark-runtime-4.1_2.13` e `iceberg-aws-bundle` 1.12.0 dentro del directorio `jars` del paquete `pyspark`, y `SPARK_CONF_DIR` apuntando a la misma configuración de catálogo que usa Spark (`pyspark/conf/`, documento de decisiones y validaciones). El comando `spark-submit` lo aporta el propio paquete `pyspark`.
- **Los jobs se montan también en Airflow.** En modo cliente `spark-submit` lee el archivo de la aplicación en la máquina que lo lanza, así que `pyspark/jobs/` y `pyspark/conf/` se montan en los contenedores de Airflow además de en los de Spark. También `pyspark/reference/`: `bronze_to_silver.py` lee los seis CSV en el driver, y por defecto los busca en `reference/`, junto a `jobs/` (se cambia con `--reference-dir`).
- **El driver debe ser alcanzable desde los ejecutores.** Cada tarea fija `spark.driver.host` al nombre del servicio que ejecuta las tareas (`airflow-scheduler`, con `LocalExecutor`) y `spark.driver.bindAddress=0.0.0.0`.
- **Conexión de Spark.** `AIRFLOW_CONN_SPARK_DEFAULT=spark://spark-master:7077?deploy-mode=client`.
- **Entre servicios de Airflow 3.** Todos comparten `AIRFLOW__API_AUTH__JWT_SECRET`, y el scheduler alcanza la API de ejecución con `AIRFLOW__CORE__EXECUTION_API_SERVER_URL=http://airflow-apiserver:8080/execution/`.
- `LocalExecutor`. Servicios de Airflow 3: `airflow-apiserver`, `airflow-scheduler`, `airflow-dag-processor`, más el job one-shot `airflow-init` (migra la base y crea el usuario administrador).
- **Autenticación.** El gestor basado en Flask AppBuilder, con `AIRFLOW__CORE__AUTH_MANAGER=airflow.providers.fab.auth_manager.fab_auth_manager.FabAuthManager` en todos los servicios de Airflow. Su proveedor ya viene en la imagen oficial; no hay que instalarlo. `airflow db migrate` crea también sus tablas.
- Metadatos en `metadata-db` (base `airflow`).
- **Programación.** El DAG corre cada 10 minutos (`schedule=timedelta(minutes=10)`) y queda activo desde que se crea (`is_paused_upon_creation=False`; por defecto Airflow crea los DAG en pausa). Lleva `catchup=False`, que en Airflow 3 ya es el valor por defecto, y `max_active_runs=1`, para que dos corridas no escriban Silver a la vez. También se puede lanzar a mano en cualquier momento. Una corrida completa tarda entre 4 y 5 minutos (ver «Cómo está implementado», más abajo). Si una corrida se alarga más de 10 minutos, la siguiente espera en lugar de solaparse.
- **Primera corrida.** Con un `schedule` de tipo `timedelta` y sin `catchup`, Airflow crea una corrida en cuanto el DAG queda activo. Si Bronze todavía no tiene sus 20 tablas, esa corrida falla en `validate_bronze` sin consecuencias, y la siguiente llega 10 minutos después. Gold existe desde la primera corrida que termina bien; hasta entonces Superset no tiene nada que mostrar.

### Cómo está implementado

Comprobado en la fase F9.

- **Imagen.** `airflow/Dockerfile` parte de `apache/airflow:3.4.0-python3.12` y añade Java 21, `pyspark` y `pyspark-client` 4.1.4, el proveedor de Spark 6.3.4 y los dos JAR de Iceberg 1.12.0, con su SHA-1 comprobado. Pesa 4.77 GB; la base, 3.25 GB. Monta `pyspark/conf`, `pyspark/jobs` y `pyspark/reference` en las mismas rutas que la imagen de Spark, bajo `/opt/spark`.
- **Servicios.** `airflow-init` migra la base y crea el administrador, y es idempotente; `airflow-apiserver`, `airflow-scheduler` y `airflow-dag-processor` esperan a que termine. Los tres quedan sanos en unos 16 s. El de la API se comprueba con `/api/v2/monitor/health`, que no pide credenciales; los otros dos, con `airflow jobs check`. El laboratorio no despliega el servicio `triggerer`, porque el DAG no usa tareas diferibles; por eso `/api/v2/monitor/health` lo muestra como `unhealthy`, y es lo esperado.
- **DAG.** `airflow/dags/elastiflix_medallion.py`. Cada tarea de Spark es un `SparkSubmitOperator` que lanza el job del mismo nombre que la tarea, con `spark.driver.host=airflow-scheduler` y `spark.driver.bindAddress=0.0.0.0`. Las dos transformaciones llevan dos reintentos, con un minuto de espera; las validaciones y el mantenimiento, ninguno.
- **Timestamp de la corrida.** Las dos transformaciones reciben `--run-ts {{ dag_run.run_after.isoformat() }}`. Las filas nuevas de Silver y todas las de Gold llevan exactamente ese instante.
- **Arranque sin intervención.** El DAG nace activo y el scheduler crea su primera corrida sin que nadie lo active. Un archivo de DAG nuevo tarda hasta 5 minutos en aparecer: es cada cuánto `airflow-dag-processor` busca archivos nuevos. Si el archivo ya está al arrancar, lo lee de inmediato.
- **Duración de una corrida completa.** Entre 4 y 5 minutos con el dataset completo y el simulador en marcha: `validate_bronze` 15–18 s, `bronze_to_silver` 59–70 s, `validate_silver` 34–35 s, `silver_to_gold` 41–42 s, `validate_gold` 28–29 s e `iceberg_maintenance` 63–98 s. Cabe en el intervalo de 10 minutos. Medido con RustFS sobre el volumen de Docker (sección 15) y con Bronze compactado en cada corrida.
- **Validaciones.** `validate_bronze.py` falla con `VBRONZE-001` si falta alguna de las 20 tablas y con `VBRONZE-002` si el pipeline de Flink no está en `RUNNING`. `validate_silver.py` hace 24 comprobaciones y falla con `VSILVER-001`; las referencias en 0 las anota sin fallar. `validate_gold.py` exige que cada producto exista, tenga filas y no traiga claves nulas ni repetidas, y falla con `VGOLD-001`.
- **Cuando una validación falla.** Comprobado con `validate_bronze`, deteniendo el TaskManager de Flink: las cuatro tareas siguientes quedan en `upstream_failed` sin ejecutarse, `iceberg_maintenance` corre, `mark_run_failed` deja la corrida en `failed`, y Silver y Gold no cambian.
- **Memoria.** Con el driver de Spark dentro, `airflow-scheduler` es el servicio de Airflow que más pide: 1.88 GiB en una corrida con el dataset parcial y un pico de unos 2.5 GiB con el completo. Por eso su límite es de 3 GiB (decisión 74; sección 39).
- **Lo que no se probó.** El fallo de `validate_silver` y de `validate_gold`; un reintento real de una transformación; el inicio de sesión en la interfaz web desde un navegador, que se comprobó por la API; y la imagen para `arm64`.
- **Parada en mitad de una corrida.** Comprobado en Linux, dos veces, con `docker compose down` y `docker compose up -d`. Durante `bronze_to_silver`: al volver, Airflow reintentó la tarea y la corrida terminó en `success`. Durante `silver_to_gold`: Gold siguió legible con la carga anterior, Superset respondió nada más arrancar, y la tarea se reintentó y terminó bien. En ninguno de los dos casos quedaron fotos ni versiones duplicadas. El fallo de `validate_gold` sí se vio, en la prueba del riesgo R8 (sección 38): con Gold vacío falla, y `mark_run_failed` deja la corrida en error.

## 19. ⚡ Job PySpark #1: Bronze → Silver

Archivo previsto:

```text
pyspark/jobs/bronze_to_silver.py
```

Responsabilidades:

- leer el estado actual de Bronze, incluidos los tombstones (`cdc_op_type = '-D'`);
- tratar como borrada toda versión vigente cuya clave ya no aparece en Bronze, que es lo que queda tras reconstruir Bronze (sección 38);
- realizar data quality;
- conformar dimensiones, enriqueciéndolas con los datos de referencia de `pyspark/reference/`;
- generar surrogate keys de forma determinística;
- aplicar SCD Type 2 por comparación de estado contra la versión vigente;
- actualizar dimensiones;
- construir tablas FACT;
- construir bridges N:M;
- preservar historial de DELETE;
- reparar referencias que quedaron en `SK = 0` en corridas anteriores;
- escribir tablas Iceberg Silver.

Propiedades que el job debe cumplir:

- **Idempotente.** Ejecutarlo dos veces sobre el mismo estado de Bronze no crea versiones, snapshots ni filas de bridge nuevas.
- **Determinístico.** El resultado depende solo del estado de Bronze y de Silver, no del orden de lectura ni de la hora de ejecución. `effective_from` proviene del dato (regla en la sección 21), no del reloj del job, salvo como último recurso.
- **Tolerante a lecturas no atómicas.** Flink publica cada tabla Bronze por separado, así que el job puede ver una película cuyas relaciones aún no llegaron. En ese caso usa `SK = 0` y lo corrige en la corrida siguiente.

No hay «eventos tardíos» que ordenar: Bronze entrega el último estado por clave, no una secuencia de eventos.

Restricción comprobada en el documento de decisiones y validaciones: el origen de un `MERGE INTO` no puede ser un DataFrame en caché. Con Spark 4.1.4 e Iceberg 1.12.0 falla en la planificación con un error interno («No plan for TableReference»). Funciona con una vista temporal sin materializar o con una tabla Iceberg de trabajo.

### Cómo está implementado

Comprobado en la fase F7.

- **Forma.** Un solo archivo, sin UDF de Python: todo son expresiones de DataFrame y SQL. Crea las tablas que falten, en formato Iceberg v2 y sin archivos de borrado, y después recorre las diez dimensiones Tipo 1, las tres SCD2, los seis bridges y los dos hechos, en ese orden, porque bridges y hechos resuelven sus claves contra las dimensiones.
- **Cómo se lanza a mano.** Fuera del DAG, por ejemplo con el DAG en pausa, desde la raíz del repositorio: `docker compose run --rm --no-deps spark-worker spark-submit /opt/spark/jobs/bronze_to_silver.py`. Crea un contenedor temporal del servicio `spark-worker`, que hace de driver en modo cliente; el ejecutor corre en el `spark-worker` permanente. No se lanza con `docker compose exec` dentro del master ni del worker: el driver no cabe en su límite de memoria junto a lo que ya corre ahí. En Git Bash hay que anteponer `MSYS_NO_PATHCONV=1`.
- **Argumentos.** `--run-ts 2026-11-23T10:00:00+00:00` es el timestamp lógico de la corrida, el que el DAG toma de `dag_run.run_after`; sin él vale la hora actual, y sin zona se toma como UTC. Es el valor de `silver_processed_at` y la fecha de los cierres por ausencia. `--reference-dir` cambia el directorio de los archivos de referencia.
- **Códigos de salida.** `0` si terminó bien; `2` si `--run-ts` no es una fecha ISO 8601 (`SILVER-001`); `1` en cualquier otro error, entre ellos `SILVER-002`, falta una tabla Bronze, y `SILVER-003`, un archivo de referencia falta o está mal formado. Si falta una tabla Bronze no se escribe nada.
- **Lectura de Bronze.** Primero fija el snapshot vigente de las 20 tablas, que son llamadas rápidas al catálogo, y después lee cada una en ese snapshot con `versionAsOf`. Así todos los pasos ven el mismo estado de cada tabla y sus deletes de igualdad se aplican una sola vez.
- **Origen del `MERGE`.** Los resultados intermedios se fijan con `localCheckpoint()`, que sí sirve como origen de un `MERGE INTO`. La contrapartida: esos resultados viven en el ejecutor, así que si el ejecutor se pierde a mitad de una corrida, el job termina con error (`CHECKPOINT_RDD_BLOCK_ID_NOT_FOUND`) y hay que repetirlo. Pasó una vez en la fase F7, cuando el motor de Docker se congeló cerca de un minuto: la corrida no dejó ninguna escritura y su repetición terminó bien. En Airflow lo cubren los reintentos de la tarea.
- **Idempotencia.** Un `MERGE` sin filas de origen crea igualmente un snapshot de Iceberg, así que el job cuenta los cambios de cada tabla y no ejecuta el `MERGE` si son cero. Con Bronze quieto, una segunda corrida deja las 22 tablas con el mismo snapshot vigente, el mismo número de snapshots y las mismas filas.
- **Bridges.** Una fila vigente se identifica por película y posición; es lo que permite reparar una fila que quedó con clave 0. `effective_from` es el `cdc_op_ts` de la fila de relación y el cierre lleva el del tombstone de esa relación. `allocation_weight` es `decimal(12,10)`; cuando cambia el número de miembros se actualiza en las filas vigentes, y las cerradas conservan el que tenían.
- **`fact_movie_snapshot`.** `record_hash` cubre las claves de negocio (`movie_id`, `collection_id`, idioma original, estado, rating y `release_date`), las siete medidas y los seis conteos; no cubre los indicadores `has_*`. El snapshot de borrado copia los valores del último snapshot. Solo se repara el último snapshot de cada película: el hecho no guarda las claves de negocio con las que volver a resolver uno más antiguo. Un rating nulo queda con clave 0, y no es una referencia pendiente.
- **`movie_sk` del hecho.** Apunta a la versión de `dim_movie` vigente al crear el snapshot. Tras un UPDATE descriptivo, que crea versión y no crea snapshot, el último snapshot de la película apunta a una versión ya cerrada: es lo esperado (sección 31). Gold debe obtener el título vigente uniendo por `movie_id` con la versión `is_current`, no por el `movie_sk` del snapshot; lo mismo vale para `collection_sk` tras renombrar una colección.
- **`fact_movie_enrichment`.** Una fila con clave 0 no se puede identificar, así que no se actualiza en el sitio: se borra y se inserta la resuelta en el mismo `MERGE`.
- **Dimensiones.** Las filas 0 y -1 llevan `Unknown` y `Not Applicable` en las columnas de texto que nombran al miembro y nulo en el resto; en las SCD2 figuran como vigentes; `dim_date` también las tiene. Una dimensión Tipo 1 solo se reescribe si cambia un atributo: un `cdc_op_ts` distinto, como el que deja reconstruir Bronze, no la toca.
- **Datos de referencia.** `Soviet Union` y `Czechoslovakia` quedan como `unmapped`, porque no tienen código ISO 3166-1 vigente; `No Language` lleva el código `xx` y el cantonés `cn`, que son los de TMDB.
- **Registro.** `pyspark/conf/log4j2.properties` silencia el aviso de Spark sobre ventanas sin partición, que salía más de cien veces por corrida por el `max(SK) + row_number()` de las claves sustitutas.
- **Duración.** Con el dataset completo (6,899 películas) y RustFS recién arrancado, la primera corrida tarda unos 110 s, una incremental unos 97 s y una sin cambios unos 85 s; de ellos, unos 50 s son leer las 20 tablas Bronze. Con RustFS degradado (sección 15) son entre 330 y 540 s. Las cifras con RustFS sano son de una versión del job anterior a dos retoques menores; el código final solo se midió entonces con RustFS degradado. Con RustFS sobre el volumen, en la fase F9, el job tarda entre 59 y 70 s dentro de una corrida del DAG (sección 18). La duración crece también con Bronze: sin compactar, tras un día de simulador sus 20 tablas sumaban 2,088 archivos de datos y 3,447 de borrado, y leerlas costó 340 s con RustFS recién arrancado (515 s la corrida). Compactar Bronze es trabajo de `iceberg_maintenance` (sección 38).
- **Memoria.** Máximos medidos: 0.29 GiB en `spark-master`, 2.18 GiB en `spark-worker` y 1.76 GiB en el contenedor del driver, con 1 GB de heap.
- **Lo que no se probó.** La rama que actualiza un atributo de una dimensión Tipo 1; la adopción tardía de una ruta canónica en `dim_collection`; dos corridas simultáneas; y la imagen para `arm64`. Dos puntos que en la fase F7 quedaron sin probar se cubrieron en la F9: el job lanzado desde Airflow (actividades F9-11 y F9-16) y una reconstrucción real de Bronze (F9-18), tras la cual Silver conservó sus 22 tablas sin cambios.

## 20. 🥈 Modelo dimensional SILVER

Silver será un esquema estrella extendido con bridge tables.

### 20.1 Dimensiones

| Dimensión | Tipo | Motivo |
|---|---|---|
| `silver.dim_date` | Estática | Calendario generado |
| `silver.dim_movie` | SCD2 | Título, sinopsis, tagline y rutas cambian en la fuente |
| `silver.dim_collection` | SCD2 | El nombre y las rutas canónicas pueden cambiar |
| `silver.dim_keyword` | SCD2 | El nombre puede cambiar para un mismo `keyword_id` |
| `silver.dim_original_language` | Tipo 1 | Catálogo de códigos |
| `silver.dim_status` | Tipo 1 | Catálogo de códigos |
| `silver.dim_rating` | Tipo 1 | Catálogo de códigos |
| `silver.dim_genre` | Tipo 1 | El nombre es la identidad |
| `silver.dim_person` | Tipo 1 | El nombre es la identidad |
| `silver.dim_production_company` | Tipo 1 | El nombre es la identidad |
| `silver.dim_production_country` | Tipo 1 | El nombre es la identidad |
| `silver.dim_spoken_language` | Tipo 1 | El nombre es la identidad |
| `silver.dim_enrichment_field` | Tipo 1 | Catálogo de campos |
| `silver.dim_enrichment_code` | Tipo 1 | Derivada del código |

En las dimensiones cuyo único atributo de negocio es su propia clave o nombre, SCD2 no tendría nada que versionar: un nombre distinto es una entidad distinta. Esas dimensiones son Tipo 1 y llevan las columnas de auditoría `source_updated_at` y `silver_processed_at` en lugar de las columnas SCD2.

### 20.2 Hechos

```text
silver.fact_movie_snapshot
silver.fact_movie_enrichment
```

### 20.3 Bridges

```text
silver.bridge_movie_genre
silver.bridge_movie_keyword
silver.bridge_movie_cast
silver.bridge_movie_production_company
silver.bridge_movie_production_country
silver.bridge_movie_spoken_language
```

En total, 14 dimensiones, 2 hechos y 6 bridges.

## 21. 🕰️ SCD Type 2

Aplica a `dim_movie`, `dim_collection` y `dim_keyword` (sección 20.1).

Patrón técnico:

```text
<entity>_sk
<business_key>
<attributes>
effective_from
effective_to
is_current
version_number
attribute_hash
source_updated_at
silver_processed_at
```

Convención temporal:

```text
[effective_from, effective_to)
```

La versión vigente tendrá `is_current = true`.

`dim_date` será estática y no requiere SCD2.

El procedimiento conceptual será:

1. Leer el estado actual de la entidad en Bronze (una fila por business key).
2. Calcular `attribute_hash` sobre los atributos descriptivos.
3. Comparar contra la versión vigente.
4. Cerrar la versión previa si cambió o si la fila llegó como tombstone.
5. Insertar una nueva versión cuando el hash cambió o la entidad se reactivó.
6. Resolver surrogate keys.
7. Cargar hechos y bridges.

### Origen de `effective_from`

Para que el resultado no dependa de la hora en que corre el job, `effective_from` (y `source_updated_at`) se toma en este orden:

1. `updated_at` de la fila Bronze, cuando la fila está viva y la tabla tiene esa columna;
2. `cdc_op_ts`, para los tombstones (`cdc_op_type = '-D'`) y para las tablas sin `updated_at`;
3. el timestamp lógico de la corrida de Airflow, solo si no hay ninguno de los anteriores. Es el caso de una versión que se cierra porque su clave ya no aparece en Bronze (sección 38). En Airflow 3 una corrida lanzada a mano no tiene `logical_date`; el DAG pasa al job `dag_run.run_after`, que existe siempre.

Un tombstone usa `cdc_op_ts` porque lleva la fila tal como estaba antes del borrado: su `updated_at` es la fecha del último cambio, no la del borrado.

> ℹ️ Este orden sustituye al original, que ponía `cdc_op_ts` primero porque suponía que valía `0` en las filas del snapshot inicial. La validación 1 mostró que el conector pone ahí la hora en que leyó la fila, así que toda fila anterior al pipeline habría recibido como inicio de vigencia la hora del snapshot. Es la decisión 26 del [documento de decisiones y validaciones](DECISIONS-AND-VALIDATIONS.md).

La versión que se cierra recibe como `effective_to` el `effective_from` de la que la reemplaza.

### Generación de surrogate keys

- `nueva SK = max(SK existente) + row_number()`, ordenando las filas nuevas por business key y `effective_from`. Es estable entre reejecuciones.
- No se usa `monotonically_increasing_id()`: sus valores dependen del particionado y cambian de una corrida a otra.
- Las claves `0` y `-1` están reservadas (sección 30); la numeración real empieza en `1`.

## 22. `dim_movie`

Grain: una versión histórica de una película.

Atributos:

```text
movie_sk
movie_id
imdb_id
title
original_title
overview
plot
tagline
release_date
release_year
release_month
release_decade
homepage
poster_path
backdrop_path
adult
video
effective_from
effective_to
is_current
version_number
attribute_hash
source_updated_at
silver_processed_at
```

Las medidas variables no se almacenarán aquí.

## 23. `dim_collection`

```text
collection_sk
collection_id
collection_name
canonical_poster_path
canonical_backdrop_path
effective_from
effective_to
is_current
version_number
attribute_hash
source_updated_at
silver_processed_at
```

La ruta canónica de cada imagen es el primer valor no nulo observado para la colección. En la primera carga, donde llegan varias películas a la vez, es el de la película con menor `movie_id`; después se conserva, aunque otra película de la colección traiga una ruta distinta. Las cuatro colecciones del dataset con rutas divergentes (sección 8.6) ejercitan esta regla.

## 24. Dimensiones de catálogo

Las tres son Tipo 1. «Columnas de auditoría» significa `source_updated_at` y `silver_processed_at`.

### Datos de referencia

Varios atributos de estas dimensiones no existen en PostgreSQL (el nombre de un idioma, el sistema al que pertenece un rating, el código ISO de un país). Provienen de archivos CSV versionados en `pyspark/reference/`, mantenidos a mano como parte del laboratorio:

| Archivo | Columna clave | Atributos que aporta |
|---|---|---|
| `pyspark/reference/languages.csv` | `language_code` | `language_name`, `is_tmdb_specific` |
| `pyspark/reference/statuses.csv` | `status_code` | `status_description` |
| `pyspark/reference/ratings.csv` | `rating_code` | `rating_system`, `rating_description` |
| `pyspark/reference/countries.csv` | `source_name` | `standard_country_name`, `country_code` |
| `pyspark/reference/spoken.csv` | `source_name` | `standard_language_name`, `language_code` |
| `pyspark/reference/enrichment.csv` | `field_name` | `field_description` |

Cuando un valor fuente no aparece en su archivo de referencia, los atributos derivados quedan en `NULL` y `quality_status = 'unmapped'`. No se inventan equivalencias.

### `dim_original_language`

```text
original_language_sk
language_code
language_name
is_tmdb_specific
quality_status
columnas de auditoría
```

### `dim_status`

```text
status_sk
status_code
status_description
quality_status
columnas de auditoría
```

### `dim_rating`

```text
rating_sk
rating_code
rating_system
rating_description
quality_status
columnas de auditoría
```

No se asignarán significados no respaldados por reglas explícitas del laboratorio.

## 25. Dimensiones multivalor

### `dim_genre`

```text
genre_sk
genre_id
genre_name
columnas de auditoría
```

### `dim_keyword`

```text
keyword_sk
keyword_id
keyword_name
SCD2 columns
```

### `dim_person`

```text
person_sk
person_id
person_name
columnas de auditoría
```

### `dim_production_company`

```text
company_sk
company_id
company_name
columnas de auditoría
```

### `dim_production_country`

```text
country_sk
country_id
source_country_name
standard_country_name
country_code
quality_status
columnas de auditoría
```

Silver podrá corregir/estandarizar valores sin destruir el valor fuente. `quality_status` toma los valores `ok`, `standardized` (el nombre fuente difiere del estándar) o `unmapped`.

### `dim_spoken_language`

```text
spoken_language_sk
spoken_language_id
source_language_name
standard_language_name
language_code
quality_status
columnas de auditoría
```

`No Language` será una fila real distinta de Unknown.

## 26. `dim_date`

Grain: una fecha de calendario.

```text
date_sk
calendar_date
day_number
day_name
day_of_week
week_of_year
month_number
month_name
quarter_number
year_number
decade_number
is_weekend
```

`date_sk` podrá expresarse como `YYYYMMDD`.

## 27. `fact_movie_snapshot`

Grain acordado:

> Una fila por película y versión de métricas observada por el procesamiento Silver.

Precisiones del grain:

- `record_hash` se calcula sobre las medidas, los conteos y las claves de negocio de las dimensiones relacionadas (`movie_id`, el `collection_id` de la colección y los códigos de las dimensiones Tipo 1), no sobre las claves sustitutas: `movie_sk` y `collection_sk` cambian con cada versión de su dimensión SCD2. Solo se inserta una fila nueva cuando ese hash difiere del último snapshot de la película. Reejecutar el job sin cambios en Bronze no añade filas.
- Un cambio en las relaciones de la película (por ejemplo, un género menos) altera un conteo y por tanto genera snapshot.
- Un cambio solo descriptivo (título, tagline) crea una versión nueva en `dim_movie` pero no un snapshot.
- `movie_sk` apunta a la versión de `dim_movie` vigente en `snapshot_at`. `snapshot_at` es el `source_updated_at` del estado observado, no la hora del job. La excepción es el snapshot de un borrado detectado por ausencia, que toma el timestamp lógico de la corrida (sección 31).
- Como Bronze entrega el último estado, entre dos corridas se registra como máximo un snapshot por película (sección 17).

Campos:

```text
movie_snapshot_sk
movie_sk
collection_sk
original_language_sk
status_sk
rating_sk
release_date_sk
snapshot_date_sk
movie_id
snapshot_at
runtime_minutes
budget_usd
revenue_usd
profit_usd
roi_percentage
popularity
user_score
vote_average
vote_count
genre_count
keyword_count
cast_count
company_count
country_count
spoken_language_count
has_collection
has_budget
has_revenue
has_homepage
is_deleted
source_updated_at
silver_processed_at
record_hash
```

### Medidas derivadas

```text
profit_usd = revenue_usd - budget_usd
```

Solo cuando ambos existen.

```text
roi_percentage = ((revenue_usd - budget_usd) / budget_usd) * 100
```

Solo cuando el presupuesto existe y es mayor que cero y existe revenue.

Los valores ausentes no se convierten en cero.

## 28. Bridges

Los bridges se anclan a la película por su clave durable `movie_id`, no por `movie_sk`. Si usaran `movie_sk`, cada cambio de título obligaría a reescribir todas las filas de género, reparto y keywords de esa película sin que ninguna relación hubiera cambiado. Con `movie_id`, una fila de bridge solo cambia cuando cambia la relación. Para obtener la versión de la película en una fecha, se une por `movie_id` y por el rango `[effective_from, effective_to)` de `dim_movie`.

### `bridge_movie_genre`

```text
movie_id
genre_sk
source_position
allocation_weight
effective_from
effective_to
is_current
```

### `bridge_movie_keyword`

```text
movie_id
keyword_sk
source_position
allocation_weight
effective_from
effective_to
is_current
```

### `bridge_movie_cast`

```text
movie_id
person_sk
billing_order
allocation_weight
effective_from
effective_to
is_current
```

No hay columna `is_lead_cast`: se añadirá, con su regla, cuando exista un requisito analítico concreto. Hasta entonces, `billing_order` permite filtrar el reparto principal.

### `bridge_movie_production_company`

```text
movie_id
company_sk
source_position
allocation_weight
effective_from
effective_to
is_current
```

### `bridge_movie_production_country`

```text
movie_id
country_sk
source_position
allocation_weight
effective_from
effective_to
is_current
```

### `bridge_movie_spoken_language`

```text
movie_id
spoken_language_sk
source_position
allocation_weight
effective_from
effective_to
is_current
```

`allocation_weight` permitirá análisis sin doble conteo cuando sea apropiado. Vale `1 / n`, siendo `n` el número de miembros vigentes de esa relación para la película.

`keyword_sk` apunta a una dimensión SCD2: se guarda la versión de la keyword vigente al crear la fila del bridge. Un cambio de nombre de la keyword no reescribe el bridge; Gold resuelve el nombre vigente por `keyword_id`.

## 29. Procedencia en Silver

### `dim_enrichment_field`

```text
enrichment_field_sk
field_name
field_description
quality_status
columnas de auditoría
```

### `dim_enrichment_code`

```text
enrichment_code_sk
code
source_system
source_family
source_date_text
currency_code
currency_year
qualifier
quality_status
columnas de auditoría
```

Tipo 1, con una fila por cada valor distinto de `movie_enrichment.code`. El código original se conserva en `code`; las demás columnas se derivan de él con estas reglas, en orden:

1. El código se separa en el primer `:`. Lo que va antes es la base; lo que va después, el sufijo, que puede no existir.
2. Si la base termina en `_AAAA-MM-DD`, esa fecha pasa a `source_date_text` y se quita de la base.
3. `source_family` es la base resultante, y `source_system`, su texto hasta el primer `_`, o la base entera si no tiene ninguno.
4. Si `source_family` es `wikipedia_infobox_fx`, el sufijo tiene la forma `<MONEDA>:<AÑO>`: las tres letras mayúsculas van a `currency_code` y los cuatro dígitos a `currency_year`.
5. En cualquier otra familia, el sufijo va tal cual a `qualifier`.
6. `quality_status` es `ok`. Es `unmapped` si `source_system` no es uno de los cuatro conocidos (`tmdb`, `wikipedia`, `wikidata` y `unverified`) o si el sufijo de `wikipedia_infobox_fx` no tiene la forma esperada.

Las columnas que no aplican a un código, o que no se pudieron derivar, quedan en `NULL`. No hace falta archivo de referencia. El dataset trae 77 códigos distintos, de 11 familias:

| Código en el dataset | `source_system` | `source_family` | Otras columnas |
|---|---|---|---|
| `tmdb_api_2026-10-22` | `tmdb` | `tmdb_api` | `source_date_text = 2026-10-22` |
| `tmdb_api_fallback_doc_vote_average` | `tmdb` | `tmdb_api_fallback_doc_vote_average` | — |
| `tmdb_metadata_summary` | `tmdb` | `tmdb_metadata_summary` | — |
| `tmdb_overview` | `tmdb` | `tmdb_overview` | — |
| `tmdb_overview_translated:zh-CN` | `tmdb` | `tmdb_overview_translated` | `qualifier = zh-CN` |
| `unverified` | `unverified` | `unverified` | — |
| `wikidata` | `wikidata` | `wikidata` | — |
| `wikipedia_infobox` | `wikipedia` | `wikipedia_infobox` | — |
| `wikipedia_infobox_fx:<MONEDA>:<AÑO>` (66 códigos, 12 monedas) | `wikipedia` | `wikipedia_infobox_fx` | `currency_code` y `currency_year` |
| `wikipedia_infobox_range_midpoint` | `wikipedia` | `wikipedia_infobox_range_midpoint` | — |
| `wikipedia_plot_2026-11-12` y `wikipedia_plot_2026-11-13` | `wikipedia` | `wikipedia_plot` | `source_date_text` con su fecha |

### `fact_movie_enrichment`

Factless fact.

Grain:

> Una relación entre una película, un campo y su código de procedencia.

```text
movie_id
enrichment_field_sk
enrichment_code_sk
observed_at
is_current
silver_processed_at
```

Igual que los bridges, se ancla a `movie_id` para no reescribirse cuando `dim_movie` cambia de versión.

## 30. Filas dimensionales especiales

Se reservarán claves para casos técnicos:

```text
SK = 0   Unknown
SK = -1  Not Applicable
```

Ejemplos:

| Caso | Clave sustituta |
|---|---|
| Película sin colección | `collection_sk = -1` |
| Rating desconocido o nulo | `rating_sk = 0` |
| Dimensión aún no disponible | `SK = 0`, temporalmente |

«Temporalmente» tiene un mecanismo concreto: en cada corrida, `bronze_to_silver` vuelve a resolver las filas de hechos y bridges que quedaron con `SK = 0` y las actualiza si la dimensión ya existe. `validate_silver` informa cuántas siguen pendientes.

Cada dimensión se crea con sus dos filas especiales ya insertadas.

## 31. Semántica Silver para INSERT/UPDATE/DELETE

### INSERT

1. Resolver/crear dimensiones.
2. Insertar `dim_movie`.
3. Insertar `fact_movie_snapshot`.
4. Insertar bridges.
5. Insertar procedencia.

### UPDATE descriptivo

1. Localizar versión vigente por business key.
2. Comparar `attribute_hash`.
3. Cerrar la versión vigente.
4. Insertar nueva versión SCD2.
5. Resolver nueva surrogate key.
6. No insertar snapshot: un cambio solo descriptivo no altera el `record_hash` del hecho (sección 27).

### UPDATE de medidas

Cambios únicamente en medidas como:

```text
popularity
vote_count
vote_average
user_score
budget_usd
revenue_usd
```

no necesitan crear una nueva versión de `dim_movie`; generan un nuevo snapshot cuando cambia el `record_hash` del hecho (sección 27).

### UPDATE de relaciones

Añadir o quitar un género o una keyword; el reparto no cambia. El simulador actualiza también `updated_at` de la película (sección 9.5), y de ahí sale la fecha del snapshot:

1. cerrar la fila de bridge que desapareció (`effective_to`, `is_current = false`);
2. insertar la fila de bridge nueva;
3. recalcular `allocation_weight` de las filas vigentes de esa relación;
4. generar snapshot, porque cambia un conteo.

### UPDATE de catálogo

Renombrar la colección de una película o una de sus keywords:

1. cerrar la versión vigente de `dim_collection` o `dim_keyword` e insertar la nueva, con el nombre cambiado;
2. no reescribir los bridges: conservan la versión vigente al crearse, y Gold resuelve el nombre actual por la clave de negocio (sección 28);
3. no crear versión en `dim_movie` ni snapshot: la película cambia su `updated_at`, pero no sus atributos ni su `record_hash` (sección 27).

### DELETE

Silver detecta el borrado por el tombstone de Bronze (`cdc_op_type = '-D'`) o, tras una reconstrucción de Bronze, porque la clave ya no aparece (sección 38). En ningún caso elimina físicamente el historial:

1. cerrar la versión vigente de `dim_movie`;
2. cerrar bridges activos de esa película;
3. insertar un snapshot con `is_deleted = true`, cuyo `snapshot_at` es el `cdc_op_ts` del tombstone o, si el borrado se detectó por ausencia, el timestamp lógico de la corrida (`dag_run.run_after`), el mismo que recibe `effective_to` (sección 21);
4. conservar el historial.

Las entidades compartidas (`dim_person`, `dim_genre`, etc.) no se cierran: siguen existiendo en PostgreSQL.

Si llega el tombstone de una película que no tiene versión vigente en Silver, porque se insertó y se borró entre dos corridas, no se crea versión ni snapshot: para Silver esa película no llegó a existir. El job no falla (validación 3).

### Reinserción tras DELETE

Si una película borrada vuelve a insertarse, Bronze reemplaza el tombstone por una fila `+I`. Silver lo trata como reactivación: nueva versión en `dim_movie` con `version_number` consecutivo al último, nuevas filas de bridge y un snapshot con `is_deleted = false`. El intervalo sin versión vigente queda como evidencia del periodo en que la película no existió.

## 32. ⚡ Job PySpark #2: Silver → Gold

Archivo previsto:

```text
pyspark/jobs/silver_to_gold.py
```

Responsabilidades:

- leer DIM/FACT/bridges de Silver;
- seleccionar versiones vigentes o snapshots apropiados;
- realizar joins;
- filtrar;
- agregar;
- calcular KPIs;
- materializar productos analíticos como tablas Iceberg Gold;
- generar estructuras simples para DuckDB/Superset.

Gold no obligará a Superset a resolver directamente la complejidad SCD2 o de bridges.

Estrategia de escritura: **recarga completa en cada corrida**. Con unos miles de películas, recalcular cada producto y reemplazar la tabla es más simple y más seguro que un MERGE incremental, y deja archivos sin deletes, que es lo que mejor lee DuckDB. Cada reemplazo se publica como un snapshot Iceberg atómico, así que una consulta debería ver la carga anterior o la nueva, nunca una mezcla. No se ha probado con consultas concurrentes durante una recarga.

### Cómo está implementado

Comprobado en la fase F8.

- **Forma.** Un solo archivo, sin UDF de Python. Primero calcula las películas vivas, que es la base de todos los productos, una sola vez y la guarda en caché; aquí sí vale `cache()`, porque el job no usa `MERGE`. Después calcula y escribe los siete productos, uno tras otro.
- **Película viva.** La que tiene versión vigente en `dim_movie` y cuyo último snapshot no es de borrado. Los atributos descriptivos salen de la versión vigente y las medidas y los conteos, del último snapshot. El título, el nombre de la colección y los géneros son los vigentes, buscados por la clave de negocio (sección 19).
- **Escritura.** La primera corrida crea cada tabla, en formato Iceberg v2. Las siguientes sobrescriben todas sus filas en un solo snapshot, de operación `overwrite`: borra las filas anteriores y escribe las nuevas, sin archivos de borrado y en un único archivo de datos por tabla. Cada corrida añade un snapshot aunque Silver no haya cambiado; los expira `iceberg_maintenance` (sección 38).
- **Cómo se lanza a mano.** Fuera del DAG, por ejemplo con el DAG en pausa, desde la raíz del repositorio: `docker compose run --rm --no-deps spark-worker spark-submit /opt/spark/jobs/silver_to_gold.py`. Va después de `bronze_to_silver.py`.
- **Argumentos y códigos de salida.** `--run-ts` es el timestamp lógico de la corrida y el valor de `gold_processed_at`. Sale con `0` si terminó bien, con `2` si `--run-ts` no es una fecha ISO 8601 (`GOLD-001`) y con `1` en cualquier otro error, entre ellos `GOLD-002`: falta una tabla de Silver, y entonces no se escribe nada.
- **Duración.** En la fase F8, antes de pasar los datos de RustFS al volumen: 238 s la primera corrida y 125 s la segunda, con el dataset completo. En la fase F9, con RustFS sobre el volumen: entre 41 y 42 s dentro de una corrida del DAG (sección 18). La mayor parte es leer Silver.
- **Lo que no se probó.** Consultas concurrentes durante una recarga; y un cambio en las columnas de un producto, que obligaría a borrar su tabla antes de la corrida, porque el job no altera esquemas. El job lanzado desde Airflow, que en la fase F8 quedó sin probar, se comprobó en la F9 (actividades F9-13 y F9-16).

## 33. 🥇 Capa GOLD

Gold contendrá resultados materializados mediante PySpark. Aunque conceptualmente operen como vistas materializadas del negocio, la implementación local será mediante tablas Iceberg materializadas por el job PySpark.

Productos:

```text
gold.movie_current_overview
gold.genre_performance
gold.collection_performance
gold.financial_performance
gold.release_trends
gold.cast_analysis
gold.data_quality_coverage
```


Gold deberá exponer tipos simples y amigables para BI:

```text
bigint
integer
decimal(p,s)
string
boolean
date
timestamp
```

### Qué contiene cada producto

Definidos en la fase F8. Todos describen el catálogo tal como está ahora: solo las películas vivas, con sus nombres vigentes (sección 32). Todas las tablas terminan con `gold_processed_at`, el timestamp lógico de la corrida que las cargó.

| Producto | Una fila por | Para qué sirve |
|---|---|---|
| `movie_current_overview` | película viva | Explorar el catálogo: la ficha completa de cada película |
| `genre_performance` | género | Comparar géneros por volumen, dinero y valoración |
| `collection_performance` | colección con alguna película viva | Comparar sagas |
| `financial_performance` | película viva con presupuesto y recaudación | Rankings y distribución de ganancia y ROI |
| `release_trends` | mes de estreno | Series temporales de estrenos |
| `cast_analysis` | persona con alguna película viva | Trayectoria y peso de cada intérprete |
| `data_quality_coverage` | conjunto de datos y métrica | Qué tan completos están los datos |

Reglas comunes de los agregados:

- **El dinero ausente no cuenta como cero.** Cada total suma solo las películas que traen el dato; `movies_with_financials` dice cuántas traen presupuesto y recaudación.
- **`roi_percentage` de un grupo** se calcula sobre las películas con presupuesto mayor que cero y recaudación: suma de sus ganancias entre suma de sus presupuestos, por cien. Es la misma regla que la de cada película (sección 27).
- **Relaciones N:M.** Una película con tres géneros cuenta en los tres, así que los `total_*` de dos géneros no se pueden sumar. Las columnas `weighted_*` reparten cada película con `allocation_weight` y sí se pueden sumar; coinciden con el total salvo el redondeo del peso a diez decimales (12.53 USD sobre 954 mil millones en la fase F8).

#### `gold.movie_current_overview`

```text
movie_id
imdb_id
title
original_title
release_date
release_year
release_month
release_decade
original_language_code
original_language_name
status_code
rating_code
collection_id
collection_name
primary_genre
genres
runtime_minutes
budget_usd
revenue_usd
profit_usd
roi_percentage
popularity
user_score
vote_average
vote_count
genre_count
keyword_count
cast_count
company_count
country_count
spoken_language_count
has_collection
has_budget
has_revenue
has_homepage
adult
version_number
last_changed_at
gold_processed_at
```

- `genres` es la lista de géneros vigentes, en el orden de `source_position`, como texto separado por comas; `primary_genre` es el primero.
- Una película sin colección lleva `collection_id` nulo y `Not Applicable` en `collection_name`; una sin rating, `Unknown` en `rating_code` (sección 30).
- `has_homepage` sale del `homepage` vigente de `dim_movie`, no del snapshot: un cambio de `homepage` crea versión y no crea snapshot (sección 31).
- `version_number` es el número de la versión vigente y `last_changed_at`, la fecha más reciente entre el inicio de esa versión y el último snapshot.

#### `gold.genre_performance`

```text
genre_id
genre_name
movie_count
weighted_movie_count
total_budget_usd
total_revenue_usd
total_profit_usd
weighted_revenue_usd
weighted_profit_usd
roi_percentage
movies_with_financials
avg_popularity
avg_vote_average
avg_user_score
avg_runtime_minutes
gold_processed_at
```

#### `gold.collection_performance`

```text
collection_id
collection_name
movie_count
first_release_date
last_release_date
total_budget_usd
total_revenue_usd
total_profit_usd
roi_percentage
movies_with_financials
avg_popularity
avg_vote_average
avg_user_score
avg_runtime_minutes
total_vote_count
gold_processed_at
```

#### `gold.financial_performance`

```text
movie_id
title
release_date
release_year
release_decade
primary_genre
original_language_name
rating_code
collection_name
budget_usd
revenue_usd
profit_usd
roi_percentage
is_profitable
budget_band
budget_band_order
profit_rank
gold_processed_at
```

- `budget_band` agrupa el presupuesto en cinco tramos (`< 1M`, `1M - 10M`, `10M - 50M`, `50M - 100M` y `>= 100M`) y `budget_band_order` los ordena del 1 al 5.
- `profit_rank` ordena por ganancia, de mayor a menor; el `movie_id` desempata para que el orden no cambie entre corridas.

#### `gold.release_trends`

```text
period_start
release_year
release_month
release_decade
movie_count
total_budget_usd
total_revenue_usd
total_profit_usd
roi_percentage
movies_with_financials
avg_popularity
avg_vote_average
avg_user_score
avg_runtime_minutes
gold_processed_at
```

`period_start` es el primer día del mes de estreno, una fecha que Superset puede usar como eje de tiempo.

#### `gold.cast_analysis`

```text
person_id
person_name
movie_count
top_billed_count
avg_billing_order
first_release_date
last_release_date
career_span_years
total_revenue_usd
weighted_revenue_usd
avg_popularity
avg_vote_average
avg_user_score
gold_processed_at
```

`top_billed_count` cuenta las películas en las que la persona encabeza el reparto, es decir, tiene el menor `billing_order` de la película. No hay otra regla de «reparto principal» (sección 28).

#### `gold.data_quality_coverage`

```text
dataset
metric
total_count
covered_count
coverage_percentage
gold_processed_at
```

Tres grupos de filas:

- `dataset = movie`: una fila por atributo opcional de la película (`imdb_id`, `overview`, `tagline`, `homepage`, `poster_path`, `backdrop_path`, `runtime_minutes`, `budget_usd`, `revenue_usd`, `user_score`, `vote_average`, `rating_code` y `collection`), con cuántas películas vivas lo traen.
- `dataset` igual al nombre de una dimensión con `quality_status` y `metric = reference_mapped`. Son siete: las cinco con datos de referencia de la sección 24, más `dim_enrichment_field` y `dim_enrichment_code`. Dice cuántos de sus valores tienen equivalencia, es decir, `quality_status` distinto de `unmapped`.
- `dataset = movie_enrichment`: una fila por campo de procedencia (sección 29), con cuántas películas vivas tienen procedencia registrada para ese campo.

## 34. 🦆 DuckDB

DuckDB funcionará como SQL/query engine, no como almacenamiento primario ni como Iceberg Catalog.

Responsabilidades:

- conectarse al Iceberg REST Catalog;
- leer las tablas Gold en RustFS;
- exponer una interfaz SQL para consumo;
- servir como backend SQL de Apache Superset.

### Dónde corre

DuckDB es una librería embebida: no escucha en un puerto ni acepta conexiones de otros contenedores. Por eso no existe un «servidor DuckDB» al que Superset se conecte. En este laboratorio corre en tres lugares, con la misma versión y el mismo SQL de inicialización:

| Lugar | Para qué |
|---|---|
| Dentro del contenedor de Superset | Es el camino real de los dashboards, vía `duckdb-engine` |
| Contenedor `duckdb` (perfil `tools` del Compose), con el binario de `duckdb/duckdb:1.5.6` sobre una Debian mínima | Línea de comandos para explorar Gold a mano; no forma parte del flujo |
| Dentro del simulador, vía DuckDB JDBC | Seguir cada cambio hasta Bronze (sección 9.3); usa solo `attach_lakehouse.sql` |

### Inicialización de cada conexión

DuckDB se usa en memoria; no guarda datos propios. Cada conexión nueva debe cargar las extensiones, declarar el acceso a RustFS, adjuntar el catálogo y, en Superset, crear las vistas de consumo. Ese SQL vive en dos archivos de `duckdb/init/`: `attach_lakehouse.sql`, con todo menos las vistas, y `gold_views.sql`, con una vista por producto Gold. Es el que pasó las validaciones 6 y 7 del documento de decisiones y validaciones:

```sql
SET extension_directory = '/opt/duckdb_extensions';
SET autoinstall_known_extensions = false;
LOAD httpfs;
LOAD iceberg;

CREATE OR REPLACE SECRET rustfs (
    TYPE s3,
    KEY_ID '${AWS_ACCESS_KEY_ID}',
    SECRET '${AWS_SECRET_ACCESS_KEY}',
    ENDPOINT 'rustfs:9000',
    URL_STYLE 'path',
    USE_SSL false
);

ATTACH 'warehouse' AS lake (
    TYPE iceberg,
    ENDPOINT 'http://iceberg-rest:8181',
    AUTHORIZATION_TYPE 'none'
);
```

`gold_views.sql` repite esta sentencia para cada producto Gold:

```sql
CREATE OR REPLACE VIEW memory.main.<producto> AS SELECT * FROM lake.gold.<producto>;
```

Reglas:

- **Tres extensiones, no dos.** `httpfs`, `iceberg` y `avro` se instalan durante el build de la imagen. `iceberg` necesita `avro` y, si no la encuentra, intenta descargarla al cargarse; sin acceso a Internet esa descarga hace fallar todas las consultas. En runtime solo se cargan (`LOAD`), y `autoinstall_known_extensions = false` convierte cualquier extensión ausente en un error visible en lugar de una descarga silenciosa.
- **Directorio de extensiones propio.** Se instalan en `/opt/duckdb_extensions`, la misma ruta en la imagen de Superset, en la del contenedor de línea de comandos y en la del simulador, y `extension_directory` apunta ahí. El directorio por defecto queda bajo el `HOME` del usuario, que en Superset es `/app/superset_home`: el volumen montado en esa ruta taparía lo instalado en el build.
- **Credenciales por variables de entorno.** `${AWS_ACCESS_KEY_ID}` y `${AWS_SECRET_ACCESS_KEY}` se sustituyen justo antes de ejecutar el archivo; no hay claves escritas en él.
- **Vistas en la base en memoria, una por producto Gold.** Son las que usan los datasets de Superset (sección 35). Se crean en cada conexión porque una base en memoria no conserva nada entre conexiones. Superset solo crea las de los productos cuya tabla Gold ya existe: antes de la primera corrida del DAG no hay ninguna, y una vista sobre una tabla inexistente haría fallar la conexión.
- **Limitación conocida de DuckDB 1.5.6 con tablas que tienen borrados.** Combinar con `UNION ALL`, o con subconsultas escalares, dos tablas Iceberg que tienen archivos de borrado, como las de Bronze tras un UPDATE o un DELETE, termina en un error interno de DuckDB (`Information loss on integer cast`). Una tabla sola, los filtros, los agregados y los `JOIN` entre esas mismas tablas funcionan. Se evita con `SET disabled_optimizers = 'statistics_propagation'`. No afecta al simulador, que consulta una sola tabla, ni a Gold, cuyas tablas se recargan completas y no tienen borrados. Observado en la fase F5.
- DuckDB nunca escribe en el lakehouse. Superset rechaza cualquier DDL o DML sobre esta base, que es su comportamiento por defecto.
- **El simulador usa solo `attach_lakehouse.sql`.** En su imagen las extensiones se instalan durante el build con el propio driver JDBC, en la misma ruta. No se usa la opción `MAX_TABLE_STALENESS` del `ATTACH`: ahorra la petición al catálogo de cada consulta, pero retrasa la visibilidad de un cambio hasta ese intervalo.
- **Nadie copia estos archivos en su imagen.** `duckdb/init/` se monta en solo lectura en cada contenedor que lo usa; así hay una sola copia.
- **En el contenedor de línea de comandos**, `gold_views.sql` se ejecuta a mano y solo cuando Gold ya existe; al abrirse, ese contenedor ejecuta únicamente `attach_lakehouse.sql`. Dentro de la consola se crean con `.read /duckdb/init/gold_views.sql`.
- Los datasets de Superset y su guía usan solo el namespace `gold`. Es una convención, no una restricción: el SQL adjunta el catálogo completo, así que `lake.silver` y `lake.bronze` también se pueden consultar desde SQL Lab.
- Los archivos no llevan `;` dentro de comentarios: quien los ejecuta descarta las líneas de comentario y parte el resto por `;`.

### Cómo está implementado

Comprobado en la fase F10.

- **Imagen de la línea de comandos.** `duckdb/Dockerfile`. La imagen oficial `duckdb/duckdb:1.5.6` solo contiene el binario y no trae shell, así que el binario se copia a `debian:trixie-20261104-slim`. Corre como el usuario `duckdb` (10003:10003) y lleva las tres extensiones instaladas en `/opt/duckdb_extensions`. Pesa 316 MB.
- **Arranque.** `duckdb/entrypoint.sh` quita los comentarios de `attach_lakehouse.sql`, sustituye los dos marcadores por las variables de entorno y abre DuckDB con ese SQL ya ejecutado. Si falta una variable o el montaje, termina con un mensaje que dice cuál. La clave no aparece en su salida.
- **Uso.** `docker compose --profile tools run --rm duckdb` abre la consola; con `-c "SQL"` ejecuta una consulta y termina. Sin el perfil, el servicio no existe para `docker compose up`. Límite de memoria: 1 GB.
- **Lectura de Gold.** DuckDB lee los siete productos con las mismas filas que el snapshot vigente del catálogo: 6,899, 19, 1,039, 4,067, 531, 95,050 y 41. Las 124 columnas se leen completas y ninguna viene toda nula. Ve también las 20 tablas de Bronze y las 22 de Silver.
- **Lo que no se probó.** La consola tecleando en una terminal: las órdenes se le pasaron por la entrada estándar. Tampoco la imagen para `arm64`.

## 35. 📊 Apache Superset

Superset será la capa de visualización.

No consultará PostgreSQL ni Flink. Sus datasets usan solo Gold; Silver y Bronze quedan al alcance de SQL Lab, porque el catálogo se adjunta entero, pero no forman parte del consumo previsto.

Ruta de consumo:

![Ruta de consumo en cuatro pasos: Superset consulta por SQL a DuckDB mediante duckdb-engine, DuckDB adjunta el catálogo y lee Iceberg Gold, y los archivos Parquet y la metadata de Gold residen en RustFS](diagrams/superset-serving-path.svg)

> Versión interactiva: [`diagrams/superset-serving-path.html`](diagrams/superset-serving-path.html) · Fuente editable: [`diagrams/superset-serving-path.json`](diagrams/superset-serving-path.json).

Gold será la fuente de verdad para las visualizaciones.

### Configuración

- Imagen propia basada en `apache/superset:6.1.0-py312`, con `duckdb` 1.5.6, `duckdb-engine` 0.17.0, `psycopg2-binary` y las extensiones de DuckDB preinstaladas. Se usa la variante `-py312` porque la etiqueta `6.1.0` a secas trae Python 3.10, ya sin soporte.
- La imagen base de la serie 6.1 es mínima: no trae ningún driver, tampoco el de PostgreSQL que Superset necesita para sus propios metadatos. Por eso `psycopg2-binary` forma parte de la imagen. Los paquetes se instalan en el entorno virtual `/app/.venv` con `uv pip install`.
- Superset 6.1.0 limita DuckDB a `duckdb<2,>=1.4.2`. Subir a DuckDB 2.x requiere antes una versión de Superset que lo admita.
- **La base de datos no viene registrada.** La conecta quien usa el laboratorio, desde la interfaz, con la URI SQLAlchemy `duckdb:///:memory:` (guía al final de esta sección). `superset-init` no la registra.
- Un hook de conexión definido en `superset/config/superset_config.py` ejecuta `duckdb/init/attach_lakehouse.sql` cada vez que SQLAlchemy abre una conexión DuckDB y, de `gold_views.sql`, solo las vistas cuya tabla existe en `lake.gold` según `information_schema.tables`. DuckDB 1.5.6 sí lista ahí las tablas de un catálogo Iceberg adjunto y, con `lake.gold` vacío, la conexión abre sin vistas y sin errores (actividades F10-01 y F10-16 del plan). Sin ese hook, las conexiones nuevas no verían el catálogo. Es un listener del evento `connect` de SQLAlchemy registrado sobre la clase `Engine`, que actúa solo cuando la conexión es de DuckDB. Superset ofrece además `DB_CONNECTION_MUTATOR` para ajustar la URI y los parámetros del motor antes de `create_engine`; no hizo falta.
- **Datasets sobre vistas, en el esquema `memory.main`.** Cada dataset se define como tabla física sobre la vista `<producto>` que el hook crea en la base en memoria (sección 34). La interfaz nombra cada esquema con su catálogo delante: el de las vistas aparece como `memory.main` y los del lakehouse como `lake.gold`, `lake.silver` y `lake.bronze`. En SQL basta con escribir `main.<producto>`.
- **Por qué vistas, y qué se sabe hoy.** La validación 7 encontró que Superset no leía las columnas de una tabla Iceberg adjunta, porque el inspector de SQLAlchemy devolvía una sola columna sin tipo, y de ahí salieron las vistas. En el laboratorio ya construido eso no se reprodujo: en la actividad F10-20 un dataset físico sobre `lake.gold.financial_performance` trajo sus 18 columnas con tipo y su consulta de gráfico funcionó. Tampoco se reprodujo el fallo que la validación 7 atribuía al nombre `memory.main`. Las vistas se mantienen porque son el camino que se siguió de principio a fin en la interfaz (decisión 68). Queda además el dataset virtual con `SELECT * FROM lake.gold.<producto>`: la validación 7 vio que ahí Superset no reconoce el tipo de las columnas `DECIMAL`, y no se volvió a probar. SQL Lab puede consultar `lake.gold.<producto>` directamente.
- **Coste por consulta.** Superset abre las conexiones a las bases analíticas sin pool (`NullPool`), de modo que cada consulta crea un DuckDB en memoria nuevo y repite la inicialización. La validación 7 lo midió: la inicialización cuesta unos 40 ms y cada vista añade entre 5 y 9 ms, frente a los 7 ms de la consulta en sí. De extremo a extremo, una consulta por la API de Superset tarda unos 150 ms en secuencia y hasta 440 ms en el percentil 95 con ocho consultas simultáneas y cuatro workers. Es aceptable para el laboratorio; no hace falta el archivo DuckDB de solo lectura que se había previsto como alternativa.
- Cada worker de Superset tiene su propio DuckDB en memoria. No comparten archivo, así que no hay bloqueos entre procesos.
- Metadatos de Superset en `metadata-db` (base `superset`).
- El job one-shot `superset-init` migra la base (`superset db upgrade`), crea el usuario administrador (`superset fab create-admin`) y carga los roles y permisos (`superset init`), como en la validación 7. Puede repetirse sin fallar: antes de crear al administrador comprueba con `superset fab list-users` si ya existe y, en ese caso, no lo vuelve a crear (actividad F10-06 del plan).
- **Sin datasets ni dashboards de fábrica.** El laboratorio entrega Superset listo para usar, pero vacío: los datasets, los gráficos y los dashboards los diseña quien lo usa. No se versiona ni se importa ningún paquete, y el DAG de Airflow no toca Superset. Conectar la base y crear gráficos es uso del laboratorio, no preparación: `docker compose up` deja todo lo necesario en marcha.

### Guía: conectar Gold y crear una visualización

Los pasos se siguieron en el laboratorio, en un navegador, con Superset 6.1.0 y la interfaz en inglés (actividades F10-20 y F10-21 del plan). Los nombres de menús y botones son los que se vieron en pantalla. El punto de partida fue la guía oficial de Superset «Creating Your First Dashboard» (Context7).

**Antes de empezar**

- El laboratorio está levantado y al menos una corrida del DAG `elastiflix_medallion` terminó bien; se ve en Airflow, `http://127.0.0.1:8080`. Hasta entonces Gold no existe y Superset no tiene nada que ofrecer.
- Se entra a Superset en `http://127.0.0.1:8088` con el administrador definido en `.env` (`SUPERSET_ADMIN_USER` y `SUPERSET_ADMIN_PASSWORD`, sección 45.4).

**1. Conectar la fuente de datos**

1. En el menú **+** de arriba a la derecha, elegir **Data** y después **Connect database**.
2. En la ventana **Connect a database**, abrir la lista **Supported databases** y elegir **DuckDB**. Los dos botones grandes de arriba son solo para PostgreSQL y SQLite.
3. Se abre un formulario pensado para MotherDuck, con **Database name** y **Access token**. No hay que rellenarlo: pulsar debajo el enlace **Connect this database with a SQLAlchemy URI string instead**.
4. En **Display Name** escribir un nombre, por ejemplo `ElastiFlix Gold`, y en **SQLAlchemy URI**: `duckdb:///:memory:`.
5. Pulsar **Test connection**. Cuando aparezca el aviso «Connection looks good!», pulsar **Connect**. El aviso «Database connected» confirma que la base quedó registrada.

La URI no lleva servidor, usuario ni contraseña: DuckDB corre dentro de Superset. El acceso al catálogo Iceberg y a RustFS lo pone el hook de conexión, que en cada conexión adjunta el lakehouse y crea una vista por cada producto Gold existente (sección 34).

**2. Registrar un producto Gold como dataset**

1. Ir a **Datasets** y pulsar **+ Dataset**.
2. Elegir en **Database** la base recién conectada, en **Schema** `memory.main` y en **Table** uno de los productos de la sección 33, por ejemplo `genre_performance`. A la derecha aparecen sus columnas, cada una con su tipo.
3. Pulsar **Create and explore dataset**.

El esquema es `memory.main`: ahí están las vistas que crea el hook. La lista ofrece también `system.main` y `temp.main`, que no tienen nada que usar, y `lake.gold`, `lake.silver` y `lake.bronze`, que son las tablas Iceberg tal cual. Si `memory.main` no trae ninguna tabla, todavía no ha terminado bien ninguna corrida del DAG.

**3. Crear una visualización**

1. Al crear el dataset se abre **Create a new chart**, con el dataset ya elegido. Elegir el tipo de gráfico, por ejemplo **Bar Chart**, y pulsar **Create new chart**: se abre la pantalla de exploración. A esa misma pantalla se llega, para un dataset que ya existe, pulsando su nombre en la lista **Datasets**.
2. En **X-axis**, pulsar el recuadro, elegir en la pestaña **Simple** una columna descriptiva, por ejemplo `genre_name`, y pulsar **Save**.
3. En **Metrics**, pulsar el recuadro, pasar a la pestaña **Simple**, elegir una columna numérica y un agregado, por ejemplo `movie_count` y `SUM`, y pulsar **Save**.
4. Pulsar **Create chart**: el gráfico aparece a la derecha, con el número de filas y el tiempo de la consulta. Después de cada cambio, el mismo botón se llama **Update chart**. El filtro de tiempo viene en **No filter** sobre `gold_processed_at`, y así debe quedar.
5. Pulsar **Save** y escribir el nombre en **Chart name**. Para llevarlo a un dashboard, escribir en **Add to dashboard** el nombre de uno nuevo, o elegir uno que ya exista. **Save** guarda el gráfico; **Save & go to dashboard** lo guarda y abre el dashboard.

Solo se probó el gráfico de barras. Otros tipos cambian el nombre de algunos campos, pero se rellenan igual.

**Qué esperar después**

- **Los datos se actualizan solos.** Gold se recarga completo en cada corrida del DAG, cada 10 minutos, y cada consulta de Superset lee el estado vigente. Basta con recargar la página del dashboard, o elegir **Refresh dashboard** en su menú **⋯**; el mismo menú tiene **Set auto-refresh** para que se refresque solo. Cada gráfico tiene además **Force refresh** en su menú **⋮**. Superset no guarda resultados: el laboratorio no configura ninguna caché.
- **Lo creado se conserva.** La conexión, los datasets, los gráficos y los dashboards quedan en `metadata-db` (base `superset`) y sobreviven a detener y volver a levantar el laboratorio. Se pierden con la vuelta a cero (sección 39).
- **SQL Lab** permite consultar con SQL tanto `main.<producto>` como `lake.gold.<producto>`.
- **Solo lectura.** Superset rechaza cualquier sentencia que modifique datos sobre esta base (sección 34): un `CREATE TABLE` o un `DELETE` en SQL Lab devuelve `DML_NOT_ALLOWED_ERROR`.

### Cómo está implementado

Comprobado en la fase F10.

- **Imagen.** `superset/Dockerfile` añade a `apache/superset:6.1.0-py312` los paquetes `duckdb` 1.5.6, `duckdb-engine` 0.17.0 y `psycopg2-binary` 2.9.13, e instala las tres extensiones de DuckDB en `/opt/duckdb_extensions`. Pesa 1.48 GB; la base, 1.26 GB. Corre como `superset` (1000).
- **Configuración.** `superset/config/superset_config.py`, montado en `/app/pythonpath`. La clave de sesión y la URI de los metadatos llegan por el entorno; si falta una, Superset no arranca y el error dice cuál (`SUPERSET-CFG-001`). El hook lee los dos archivos de `duckdb/init/`, montados en solo lectura. Fija además `RATELIMIT_STORAGE_URI = "memory://"`: los límites de peticiones de Superset guardan sus contadores en memoria, que basta con un solo contenedor y evita un aviso al arrancar.
- **Servicios.** `superset-init` aplica las 344 migraciones en 17 s, crea al administrador y carga los roles; repetido, no cambia nada y termina con código 0. `superset` queda sano a los 9 s, con cuatro procesos, en `http://127.0.0.1:8088`. Se comprueba con `/health`, que no pide credenciales.
- **El hook, dentro de Superset.** Un motor creado por el propio modelo de base de datos de Superset usa `NullPool` y ve las siete vistas. Contra un catálogo con el namespace `gold` vacío, la conexión abre sin errores y sin vistas. Una conexión nueva con las siete vistas tarda entre 126 y 196 ms.
- **La guía, de principio a fin.** Seguida en un navegador con el administrador de `.env`: base conectada, dataset sobre `genre_performance`, gráfico de barras de 19 géneros en 0.29 s y dashboard nuevo.
- **El gráfico sigue al dato.** Se renombró un género en PostgreSQL: a los 45 s estaba en Bronze, la corrida siguiente del DAG lo llevó a Gold, y al recargar el dashboard el gráfico mostró el nombre nuevo y los cambios del simulador en otros 17 géneros. Entre el cambio y el gráfico pasaron 10 minutos, lo que tarda en llegar la corrida siguiente.
- **Memoria.** 824 MiB en reposo y 967 MiB después de la sesión en el navegador, de un límite de 2 GB.
- **Ruido conocido en el log.** Cada página pide `/favicon.ico`, que esta imagen no sirve, y deja un 404 con su traza. No afecta al uso.
- **Lo que no se probó.** Otros tipos de gráfico, los filtros de un dashboard, varias personas a la vez y la imagen para `arm64`. La validación 7 midió la concurrencia por la API.

## 36. Calidad de datos

La filosofía acordada es:

![Responsabilidad de cada capa, en secuencia: PostgreSQL conserva semántica fuente; Bronze es una réplica as-is; Silver limpia, conforma e historiza; Gold sirve métricas y productos analíticos](diagrams/quality-by-layer.svg)

> Versión interactiva: [`diagrams/quality-by-layer.html`](diagrams/quality-by-layer.html) · Fuente editable: [`diagrams/quality-by-layer.json`](diagrams/quality-by-layer.json).

Ejemplos documentados que podrán resolverse en Silver:

| Caso | Tratamiento en Silver |
|---|---|
| `Guadaloupe` | Posible estandarización a `Guadeloupe`, conservando el valor fuente |
| Variantes del nombre de una compañía | No se fusionan sin una regla explícita |
| Variantes del nombre de una persona | No se fusionan automáticamente |
| `cn` | Se conserva como código TMDB |
| `No Language` | Sigue siendo un valor real |
| Un nombre de keyword compartido por dos identificadores | Se conservan como dos keywords distintas |
| `budget` y `revenue` nulos | Se mantienen nulos como ausencia, nunca como cero |
| `user_score` y `vote_average` | Siguen siendo medidas distintas |
| `plot` truncado alrededor de 3,000 caracteres | Se conserva tal cual; no se inventa el contenido que falta |

## 37. Particionamiento Iceberg

No se particionarán inicialmente dimensiones pequeñas.

`fact_movie_snapshot` se crea sin partición: con el volumen del laboratorio no hace falta. Si el historial creciera mucho, la alternativa es particionar por `months(snapshot_at)`.

Se evitará una granularidad excesiva que genere demasiados archivos pequeños.

## 38. Consideraciones de mantenimiento Iceberg

Los cambios fila a fila, SCD2 y MERGE pueden generar archivos adicionales. El mantenimiento se reparte por capa:

| Capa | Qué se acumula | Mantenimiento |
|---|---|---|
| 🥉 Bronze | Un commit por checkpoint de Flink y por tabla, con deletes de igualdad | **Desde el inicio**: compactación (`rewrite_data_files`) y expiración de snapshots en la tarea `iceberg_maintenance` |
| 🥈 Silver | Archivos reescritos por cada MERGE | Expiración de snapshots; compactación solo si se observa degradación |
| 🥇 Gold | Un snapshot por recarga completa | Expiración de snapshots, conservando los 5 últimos |

Las tres capas las trata la tarea `iceberg_maintenance` (sección 18); `silver_to_gold.py` no expira snapshots por su cuenta.

Bronze no puede esperar: con un checkpoint cada 30 s y 20 tablas, en una hora de demostración se generan miles de archivos pequeños, y cada lectura de Spark debe aplicar los deletes acumulados.

Quedan para cuando haga falta demostrar operación del lakehouse:

- limpieza de archivos huérfanos;
- validación del número/tamaño de archivos.

Estas tareas no deben oscurecer el flujo principal.

Procedimientos de Iceberg que usa `iceberg_maintenance`, comprobados en la validación 5 del documento de decisiones y validaciones:

```sql
CALL lake.system.rewrite_data_files(
    table => 'lake.bronze.movie',
    options => map('rewrite-all', 'true', 'remove-dangling-deletes', 'true'));
CALL lake.system.rewrite_position_delete_files(
    table => 'lake.bronze.movie', options => map('rewrite-all', 'true'));
CALL lake.system.expire_snapshots(
    table => 'lake.bronze.movie', older_than => TIMESTAMP '2026-11-23 19:45:00', retain_last => 5);
```

- **La tabla se nombra con el catálogo delante**, `lake.bronze.movie`. Con `bronze.movie` el procedimiento funciona igual, pero Iceberg prueba antes si `bronze` es un catálogo y deja en el log un aviso con su traza por cada llamada: tres por tabla y corrida. Visto y corregido en la fase F11.
- **`older_than` es obligatorio.** Por defecto `expire_snapshots` solo expira snapshots de más de cinco días, así que en un laboratorio que lleva horas en marcha `retain_last` por sí solo no expira ninguno. El job pasa la hora en que arranca.
- **La compactación corre con Flink escribiendo, pero a veces se cruzan.** Si Flink confirma un checkpoint entre la reescritura y la retirada de los deletes sobrantes, Iceberg rechaza esta última («Cannot remove dangling deletes: current snapshot changed»). No se pierde nada. `iceberg_maintenance.py` repite la compactación de esa tabla hasta tres veces y, si no lo consigue, la deja para la corrida siguiente. Pasó una vez en 49 tablas en la fase F9.
- **Si una tabla falla por otra causa**, el job lo anota, sigue con las demás y termina con código 1 y el error `MAINT-001`, que nombra las tablas que fallaron.
- **Efecto medido en la fase F9.** Tras un día de simulador sin mantenimiento, Bronze tenía 2,088 archivos de datos y 3,447 de borrado; una corrida los dejó en 67 y 82. Con el mantenimiento en cada corrida del DAG, leer las 20 tablas Bronze cuesta unos 20 s.
- `rewrite-all` tiene sentido mientras las tablas sean pequeñas, como en este laboratorio; con tablas grandes se sustituye por `delete-file-threshold`.
- Los archivos de deletes que la compactación deja sin uso se borran físicamente al expirar los snapshots que los referencian. `retain_last` decide cuánto historial queda: se conservan los 5 últimos snapshots.

### Reconstrucción de Bronze

Cuando se pierden los checkpoints de Flink, repetir el snapshot sobre las tablas existentes deja vivas en Bronze las filas borradas durante la parada (sección 14). Por eso Bronze se reconstruye:

1. Pausar el DAG de Airflow, para que `bronze_to_silver` no lea un Bronze a medio cargar.
2. Eliminar las tablas del namespace `bronze`, con sus archivos. Basta la API del catálogo: `DELETE /v1/namespaces/bronze/tables/<tabla>?purgeRequested=true` por cada tabla que devuelve `GET /v1/namespaces/bronze/tables`. Lo hace `flink/jobs/drop-bronze-tables.sh`, que se lanza con `docker compose run --rm --no-deps flink-cdc-submit bash /opt/flink/jobs/drop-bronze-tables.sh --confirm`. Sin `--confirm` solo lista lo que borraría, y se niega si el pipeline está en ejecución.
3. Ejecutar `flink-cdc-submit`. Sin job, sin checkpoint y sin tablas, hace un envío nuevo con snapshot inicial.
4. Esperar a que el snapshot termine: cada tabla Bronze tiene las mismas filas que su tabla de PostgreSQL.
5. Reanudar el DAG.

Qué implica:

- **Se pierden los tombstones acumulados en Bronze.** El historial de Silver no se toca.
- **Los borrados ocurridos durante la parada llegan a Silver por ausencia.** En la corrida siguiente, `bronze_to_silver` cierra toda versión vigente cuya clave ya no está en Bronze, igual que con un tombstone. Como la fecha real del borrado ya no se conoce, `effective_to` y el `snapshot_at` del snapshot de borrado son el timestamp lógico de esa corrida (secciones 21 y 31).
- **No aparecen versiones nuevas por la recarga.** Todas las filas vuelven con `cdc_op_type = '+I'` y un `cdc_op_ts` nuevo, pero su contenido y su `updated_at` no cambian, así que el hash de atributos coincide con el de la versión vigente.
- **El paso 1 no es opcional.** Con el DAG activo, una corrida que encuentre Bronze vacío o incompleto cerraría versiones de filas que siguen existiendo.
- **Qué pasa si se salta el paso 1, comprobado.** Se reconstruyó Bronze con el DAG activo, a propósito, en un laboratorio desechable con el dataset completo. Mientras faltaban tablas, la corrida quedó protegida: `validate_bronze` falló y Silver no se tocó. Pero la corrida lanzada cuando las 20 tablas ya existían y la de películas seguía vacía pasó esa validación, y `bronze_to_silver` dio por borradas las 6,899 películas: cerró todas sus versiones vigentes, escribió 6,899 fotos de borrado y Gold quedó con 0 filas. `validate_silver` no lo detecta, porque el resultado es coherente; lo delata `validate_gold`, al encontrar Gold vacío. La validación de Bronze comprueba que las tablas existen, no que estén completas.
- **Cómo se repara, comprobado.** Con el DAG en pausa y Bronze ya completo, cada tabla de Silver se devuelve a su último snapshot anterior a la corrida dañina: `CALL lake.system.rollback_to_timestamp(table => 'lake.silver.<tabla>', timestamp => TIMESTAMP '<instante>')`. Sobre las 22 tablas tardó 7 s; retrocedieron las 6 que la corrida había tocado y Silver quedó exactamente como antes: 6,899 versiones vigentes y ninguna foto de borrado. Al reanudar el DAG, la corrida siguiente devolvió a Gold sus 6,899 películas. Funciona mientras ese snapshot siga existiendo: el mantenimiento conserva los cinco últimos de cada tabla.

Comprobado con las 20 tablas y el dataset completo, en el [documento de decisiones y validaciones](DECISIONS-AND-VALIDATIONS.md): los pasos 2 a 4 tardan cerca de un minuto. Repetido en la fase F5 con el laboratorio ya construido: 49 s el borrado y 110 s desde el envío hasta que Bronze volvió a coincidir con PostgreSQL en las 20 tablas. Repetido en la fase F9 con el DAG, pausándolo antes y reanudándolo después: 19 s el borrado y 187 s hasta que Bronze coincidió (439,937 filas); la corrida siguiente del DAG no escribió nada en Silver, cuyas 22 tablas conservaron su snapshot y sus filas.

**Slot de replicación invalidado.** Si PostgreSQL invalida el slot `elastiflix_cdc` porque Flink estuvo parado más de lo que permite `max_slot_wal_keep_size` (sección 10), el pipeline no puede reanudar desde su checkpoint. Se aplica el mismo procedimiento, con dos pasos más antes del paso 3: borrar el slot (`pg_drop_replication_slot`) y borrar los checkpoints retenidos de `flink/data/`, para que `flink-cdc-submit` haga un envío nuevo. No se ha probado. Mientras las tablas no existen, `bronze_to_silver` falla con «tabla no encontrada» en lugar de cerrar versiones; eso no sustituye al paso 1, porque no cubre el intervalo en que unas tablas ya se recrearon y otras no.

## 39. 🐳 Docker Compose

Un único comando deberá levantar el laboratorio completo:

```bash
docker compose up -d --build
```

Servicios de larga duración:

```text
postgresql
metadata-db
java-simulator
flink-jobmanager
flink-taskmanager
iceberg-rest
rustfs
spark-master
spark-worker
airflow-apiserver
airflow-scheduler
airflow-dag-processor
superset
```

Jobs one-shot (terminan con código 0 y no se reinician):

```text
volumes-init       asigna a cada directorio de datos el usuario de su servicio
rustfs-init        crea el bucket warehouse
iceberg-init       crea los namespaces bronze, silver y gold
flink-cdc-submit   envía el pipeline PostgreSQL -> Bronze
airflow-init       migra la base de Airflow y crea el administrador
superset-init      migra la base de Superset y crea el administrador
```

Opcional, bajo el perfil `tools`:

```text
duckdb             línea de comandos para explorar Gold
```

Todos se declaran en el mismo `docker-compose.yml`. Las credenciales del laboratorio se leen de `.env`; el repositorio versiona `.env.example`. El inventario de cuentas y variables está en la sección 45.

`java-simulator` declara `tty: true` y `stdin_open: true`, para poder abrir su interfaz con `docker compose attach java-simulator`.

**Ningún servicio declara `restart`.** Tras reiniciar el equipo o Docker Desktop, los contenedores quedan detenidos y el laboratorio se vuelve a levantar con `docker compose up -d`: los jobs one-shot se repiten sin efecto, `flink-cdc-submit` reanuda el pipeline desde su último checkpoint (sección 14) y el simulador continúa con la primera película pendiente (sección 9.5). Con reinicio automático, Flink volvería sin su job y nadie lo reenviaría: la captura quedaría parada sin aviso.

### Aislamiento frente a otros proyectos del host

Quien revise el laboratorio puede tener otros entornos Docker en la misma máquina, incluso otro laboratorio de ElastiFlix. Para que no se pisen:

- **Nombre de proyecto explícito.** El archivo empieza con `name: elastiflix-cdc-lakehouse`. Sin él, Compose deriva el nombre del directorio donde se clonó el repositorio, y dos clones o un directorio renombrado producirían proyectos distintos sobre los mismos datos.
- **Sin `container_name`.** Los contenedores toman el nombre que genera Compose (`elastiflix-cdc-lakehouse-postgresql-1`). Un nombre fijo como `elastiflix-postgres` choca con cualquier otro proyecto que use el mismo.
- **Red propia.** Los servicios se hablan por la red por defecto del proyecto y por nombre de servicio (`postgresql`, `rustfs`, `iceberg-rest`); no se usan redes externas ni `network_mode: host`.
- **Puertos del host configurables.** Cada puerto publicado se declara como `127.0.0.1:${VAR:-valor}:puerto`, con la variable en `.env.example`. Si el `5432` u otro ya está ocupado, se cambia en `.env` sin tocar el Compose. Las conexiones entre servicios no dependen de esos puertos. Los ocho están juntos en el campo de extensión `x-host-ports` del Compose, con un ancla YAML por servicio: cada servicio los toma con `ports: *ports-<servicio>`.

| Variable | Valor por defecto | Servicio |
|---|---:|---|
| `POSTGRES_HOST_PORT` | 5432 | PostgreSQL operacional |
| `FLINK_UI_HOST_PORT` | 8081 | Flink UI |
| `SPARK_UI_HOST_PORT` | 8082 | Spark master UI |
| `AIRFLOW_HOST_PORT` | 8080 | Airflow UI y API |
| `SUPERSET_HOST_PORT` | 8088 | Superset |
| `RUSTFS_API_HOST_PORT` | 9000 | RustFS, API S3 |
| `RUSTFS_CONSOLE_HOST_PORT` | 9001 | RustFS, consola |
| `ICEBERG_REST_HOST_PORT` | 8181 | Iceberg REST Catalog |

`metadata-db` no publica puerto: solo lo usan Airflow y Superset dentro de la red del proyecto. La UI del master de Spark escucha en el 8080 dentro de su contenedor, igual que Airflow; por eso se publica en el 8082 del host.

### Zona horaria

Todo el laboratorio trabaja en UTC (decisión 75). El Compose no define `TZ` en ningún servicio y las imágenes traen UTC como zona.

- **Fijado de forma explícita.** El pipeline de Flink (`local-time-zone: UTC`), la sesión de Spark (`spark.sql.session.timeZone`), la fecha de inicio del DAG y la bitácora del simulador, que escribe cada marca con la `Z` al final.
- **Por omisión.** PostgreSQL, `metadata-db`, Airflow, Superset, DuckDB y el reloj de la consola del simulador toman la zona de su contenedor. Comprobado en las siete imágenes del laboratorio: todas responden UTC.
- **Los datos no dependen de la zona.** Las columnas `created_at` y `updated_at` son `timestamp with time zone` y las asigna PostgreSQL con `now()`: guardan el instante. La zona solo decide cómo se muestra.
- **Qué ve quien lo usa.** Las horas de la consola del simulador, de su bitácora, de Airflow, de Superset y de DuckDB van en UTC. En Ciudad de México son seis horas más que el reloj local, todo el año.
- **Por qué no se cambia.** Una sola zona en todas las piezas permite comparar las marcas de tiempo de una capa con las de otra sin convertir nada. Se valoró mostrar la hora de Ciudad de México solo en las pantallas, sin tocar Flink ni Spark, y la persona responsable prefirió dejar todo en UTC.

### Presupuesto de memoria

Con 16 GB en el host, cada servicio declara un límite. La columna de la derecha es el máximo medido para cada servicio, y no todas las cifras salen de la misma prueba. La mayoría son de la medición con todo el stack en marcha y bajo carga del [documento de decisiones y validaciones](DECISIONS-AND-VALIDATIONS.md). Las de Spark se midieron con el job real en la fase F7; la de RustFS, en la F9; la de `airflow-dag-processor`, en la F11; y la de `airflow-scheduler`, con el dataset completo, en las pruebas en Linux:

| Servicio | Límite | Máximo medido |
|---|---:|---:|
| PostgreSQL operacional | 1 GB | 0.15 GB |
| `metadata-db` | 0.5 GB | 0.16 GB |
| Flink JobManager | 1 GB | 0.56 GB |
| Flink TaskManager | 2 GB | 1.10 GB |
| Spark master | 0.5 GB | 0.29 GB |
| Spark worker | 3 GB | 2.18 GB |
| `airflow-apiserver` | 0.5 GB | 0.33 GB |
| `airflow-scheduler` | 3 GB | 2.47 GB |
| `airflow-dag-processor` | 0.5 GB | 0.46 GB |
| Superset | 2 GB | 1.15 GB |
| RustFS | 1 GB | 0.73 GB |
| Iceberg REST | 0.5 GB | 0.24 GB |
| Event Simulator | 0.5 GB | 0.12 GB, medido con una sonda que no carga el dataset; el simulador real suma unos 100 MB |

Los límites suman 16 GB, tanto como la memoria recomendada para el equipo, pero son topes, no reservas: el uso real fue de 3.4 GB en reposo y de 7.9 GB en el momento de mayor carga.

- **Medido con el laboratorio construido (fase F11).** Durante una corrida completa del DAG, con Flink y el simulador escribiendo y unas 2,600 películas cargadas, el laboratorio usó entre 4.7 y 7.4 GiB. Ningún contenedor se detuvo por memoria. Dos quedaron a menos de un 10 % de su límite: `airflow-scheduler`, con 1.87 GiB de los 2 que tenía entonces, y `airflow-dag-processor`, con 0.46 de 0.5. Era el riesgo R12 del plan.
- **Medido con el dataset completo cargado, en Linux.** Con las 6,899 películas y todos los servicios, la primera corrida del DAG llevó el laboratorio a 7.42 GiB, lo mismo que con el dataset parcial. La diferencia estuvo en `airflow-scheduler`: llegó al 100 % de los 2 GiB que tenía entonces. No fue detenido, porque el equipo tenía memoria de intercambio. Repetida la corrida con un límite de 4 GiB, para ver cuánto pide de verdad: 2.06 GiB de memoria propia y un pico de 2.47 GiB. Es decir, el límite de 2 GiB quedaba por debajo de lo que necesita con el dataset completo. `airflow-dag-processor` usó 0.40 GiB de memoria propia, con un pico de 0.51 cuando se le dio 1 GiB; con sus 0.5 GiB llegó a 0.41 y no se detuvo, así que su límite no cambia.
- **El límite de `airflow-scheduler` sube de 2 a 3 GiB (decisión 74).** Lo decidió la persona responsable a la vista de esa medición. Comprobado en Linux con el límite nuevo y sin memoria de intercambio para el contenedor, desde cero y con el dataset completo: dos corridas seguidas del DAG terminaron bien, en 2 min 37 s y 2 min 26 s, con 2.09 GiB de memoria propia como máximo, un pico de 2.31 GiB y ningún proceso detenido por memoria. Con ello se cierra el riesgo R12 del plan.
- **El scheduler de Airflow es el que más necesita de los tres.** En modo cliente el driver de Spark corre dentro de él: con un driver de 1 GB llegó a 1.41 GB. Por eso los 4 GB de Airflow se reparten 0.5, 3 y 0.5.
- **El worker de Spark** aloja un ejecutor de 1.5 GB además de su propio proceso. Ofrece al clúster 1500 MB y 4 núcleos (`SPARK_WORKER_MEMORY`, `SPARK_WORKER_CORES`), lo justo para un ejecutor, así que corre una aplicación a la vez. El master y el worker limitan su propio proceso con `SPARK_DAEMON_MEMORY=256m`; sin ese valor cada uno pediría 1 GB.
- **El driver del job real pide más que el del prototipo.** Con `bronze_to_silver.py` y el dataset completo, el contenedor que hizo de driver llegó a 1.76 GiB con 1 GB de heap (fase F7). El prototipo de la validación midió 1.41 GB en `airflow-scheduler`, cuyo límite era entonces de 2 GB. En la fase F9, con el driver del job real dentro del scheduler, llegó a 1.88 GiB en una corrida completa del DAG, a un 6 % de ese límite. Era el riesgo R12 del plan.
- Si el host tiene menos de 16 GB, se puede detener el simulador o Superset mientras corre el DAG.

### Datos de desarrollo

Las fases F3 a F5 y F7 a F10 del plan se construyen antes de que exista el simulador, o en paralelo con él. Para trabajar con el volumen real, el dataset completo se carga de una vez:

- `postgresql/scripts/load_dev_data.sql` carga los 20 CSV con `\copy` de `psql`, en el orden de sus claves foráneas, con una transacción por archivo y con la cuenta `elastiflix_app`. Solo carga sobre una base vacía: si `catalog` ya tiene datos, se detiene sin tocar nada. Al terminar muestra las filas de cada tabla, que deben sumar 438,925.
- Se ejecuta a mano, con el servicio `postgresql` en marcha, desde un contenedor temporal de la imagen de PostgreSQL que monta `raw_data/` y `postgresql/scripts/` en solo lectura. El servicio `postgresql` no monta ninguno de los dos, y ningún servicio ni job del Compose ejecuta el script. En Git Bash hay que anteponer `MSYS_NO_PATHCONV=1`: sin ello las rutas se convierten y `psql` no encuentra el script. El comando, desde la raíz del repositorio:

  ```bash
  docker compose run --rm --no-deps -v ./raw_data:/raw_data:ro -v ./postgresql/scripts:/scripts:ro postgresql bash -c 'PGPASSWORD="$ELASTIFLIX_APP_PASSWORD" psql -h postgresql -U elastiflix_app -d elastiflix -v ON_ERROR_STOP=1 -f /scripts/load_dev_data.sql'
  ```

- Flink CDC lleva esas filas a Bronze: en el snapshot inicial si se cargan antes de enviar el pipeline, que es lo que se probó en la validación de volumen, o como cambios en streaming si el pipeline ya corre. Los dos caminos están comprobados: en la fase F5, con el pipeline ya en marcha, Flink leyó la carga completa en unos 40 s y Bronze quedó igual que PostgreSQL.
- **Por qué una transacción por archivo y no una sola.** PostgreSQL decodifica cada transacción entera antes de entregarla al CDC y, cuando pasa de 64 MB (`logical_decoding_work_mem`), la vuelca a disco cambio a cambio. Con los datos en un directorio compartido desde Windows, ese volcado avanzó a unos 15 MB por minuto y Bronze no recibió nada mientras tanto. Con una transacción por archivo ninguna llega a ese tamaño. Las transacciones del simulador, de una película cada una, quedan muy por debajo.
- Es solo para desarrollar. El laboratorio terminado arranca con las tablas vacías y es el simulador quien las llena (sección 9.5).
- Las comprobaciones del simulador (fase F6) se hacen sobre una base vacía: antes se vuelve a cero, y desde ese momento los datos los pone el simulador, también para lo que quede de F7 a F10.
- **Con el simulador ya en el Compose**, un `docker compose up -d` lo arranca y empieza a insertar, de modo que la base deja de estar vacía en segundos. Para usar la carga de desarrollo se levanta solo la cadena que llega hasta el pipeline, sin el simulador ni Spark, Airflow o Superset, nombrando su último job: `docker compose up -d flink-cdc-submit`. Después se lanza la carga y, al terminar, `docker compose up -d`. El simulador encuentra las 6,899 películas y entra directamente en modo continuo (sección 9.5). Las dos mitades están comprobadas por separado, la carga con el pipeline en marcha en F5 y el arranque del simulador sobre la base completa en F6; la secuencia entera no.

### Reconstruir la imagen de un servicio

`docker compose up -d --build <servicio>` reconstruye también las imágenes de los servicios de los que depende y recrea sus contenedores. En la fase F6, reconstruir así el simulador recreó el JobManager y el TaskManager de Flink; el pipeline se reanudó solo desde su último checkpoint, pero no hacía falta pararlo. Para tocar un solo servicio:

```bash
docker compose build java-simulator
docker compose up -d --no-deps java-simulator
```

### Vuelta a cero

Para dejar el laboratorio como recién clonado, sin perder las imágenes construidas ni el `.env`:

1. `docker compose down`, que detiene y elimina los contenedores y la red.
2. Vaciar los directorios de datos, conservando su `.gitkeep`: `postgresql/data/`, `metadata-db/data/`, `flink/data/`, `iceberg/data/`, `superset/data/` y `airflow/logs/`. Los datos de RustFS están en un volumen (sección 15): se borra con `docker volume rm elastiflix-cdc-lakehouse_rustfs-data`.
3. `docker compose up -d`.

Los directorios se vacían todos a la vez. Vaciar solo algunos deja el laboratorio incoherente: un catálogo que apunta a archivos que ya no están en RustFS, o checkpoints de Flink que remiten a un slot de replicación que ya no existe. Se usa antes de la prueba de extremo a extremo (fase F11) y cada vez que haga falta repetir la demostración desde el principio. Comprobado en la fase F11: `docker compose down` tarda 8 s, vaciar los seis directorios 1 s, y el laboratorio vuelve a arrancar desde vacío, con 0 películas, el catálogo sin tablas y Superset sin bases conectadas.

**En Linux el paso 2 no se puede hacer borrando desde el equipo.** Los archivos pertenecen a los usuarios de los contenedores (999, 9999 y 50000), y `rm` falla con «Permission denied» en `postgresql/data`, `metadata-db/data`, `flink/data` y `airflow/logs`. Comprobado en Ubuntu 24.04. El mismo borrado se hace dentro de un contenedor, que corre como `root`, sin `sudo`:

```bash
docker run --rm -v "$PWD":/lab -w /lab postgres:19.0 bash -c 'for d in postgresql/data metadata-db/data flink/data iceberg/data superset/data airflow/logs; do find "$d" -mindepth 1 -maxdepth 1 ! -name .gitkeep -exec rm -rf {} +; done'
```

Tarda menos de un segundo, conserva los `.gitkeep` y deja el clon sin cambios para Git.

**Volúmenes anónimos.** `volumes-init`, `rustfs-init` e `iceberg-init` reutilizan la imagen de RustFS, que declara `/data` como volumen. Hasta la versión `v1.0.1`, cada arranque dejaba tres volúmenes anónimos vacíos que `docker compose down` no borra. Desde entonces los tres jobs montan `/data` en memoria (`tmpfs`) y no dejan ninguno; comprobado en Linux con dos ciclos completos de arranque y parada. Los que ya existan de arranques anteriores no estorban; se pueden retirar con `docker volume prune`, que borra todos los volúmenes sin uso del equipo, no solo los del laboratorio.

## 40. Orden de dependencias esperado

![Orden de arranque de los servicios de Docker Compose en cuatro carriles: operacional y CDC, almacenamiento y catálogo, batch y orquestación, y consumo](diagrams/compose-startup-order.svg)

> 🔍 **Cómo leerlo:** cada flecha es un `depends_on`. La etiqueta indica la condición: `healthy` espera al healthcheck del servicio y `completó` espera a que un job one-shot termine bien. `volumes-init` es el primero: de él dependen `rustfs`, Flink, `airflow-init` y `superset-init`, que necesitan sus directorios de datos ya preparados; `iceberg-rest` queda detrás de él a través de `rustfs`. El camino verde es el crítico: sin bucket no hay catálogo, sin namespaces no se envía el pipeline, y el simulador no emite hasta que el pipeline está corriendo.
>
> Versión interactiva: [`diagrams/compose-startup-order.html`](diagrams/compose-startup-order.html) · Fuente editable: [`diagrams/compose-startup-order.json`](diagrams/compose-startup-order.json).

Reglas:

- Los servicios con estado (`postgresql`, `metadata-db`, `rustfs`, `iceberg-rest`, Flink, Spark) exponen healthcheck. Los dos PostgreSQL usan `pg_isready` por TCP y no por el socket: mientras la imagen ejecuta sus archivos de inicialización solo escucha en el socket, así que por TCP el servicio no aparece sano hasta que la inicialización ha terminado. El JobManager de Flink está sano cuando responde su API REST, y el TaskManager, cuando el JobManager lo ve registrado.
- Las dependencias sobre jobs one-shot usan `condition: service_completed_successfully`.
- Los jobs one-shot son idempotentes: `docker compose up` puede repetirse sin romper nada.
- `docker compose up --wait` sin nombrar servicios no sirve para esperar al laboratorio: devuelve error en cuanto termina un job one-shot, aunque termine con código 0. Para esperar a un servicio se nombra: `docker compose up -d --wait metadata-db`. Comprobado con Compose 5.5.1 en la fase F2.
- El simulador arranca cuando `flink-cdc-submit` ha terminado, es decir, con el pipeline en `RUNNING` (sección 14). En el primer arranque las tablas de PostgreSQL están vacías (sección 9.5), así que el snapshot inicial es inmediato y las primeras inserciones ya llegan por streaming. Medido en la fase F6, desde cero: `docker compose up -d` deja el simulador arrancado a los 51 o 55 segundos, y su primera transacción llega unos 4 segundos después. Repetido en la fase F11 con todos los servicios: el simulador arrancó a los 58 s.
- Spark arranca después de `iceberg-init`, para que sus jobs encuentren los namespaces.
- Airflow y Superset no esperan a Spark ni a que Gold tenga datos; solo las corridas del DAG y los datasets los necesitan.
- Ningún servicio se reinicia solo (sección 39): tras un reinicio del equipo, este orden se recorre de nuevo con `docker compose up -d`.
- **Flink espera a `postgresql`.** `flink-jobmanager` declara esa dependencia porque así lo dibuja el diagrama. Flink no la necesita para arrancar, solo el pipeline; le cuesta empezar unos 40 s más tarde, sin retrasar el envío del pipeline, que ya esperaba a PostgreSQL.
- **Arranque completo, medido en la fase F11.** Desde un laboratorio vuelto a cero y con las imágenes ya construidas, `docker compose up -d --build` termina con código 0 en 97 s. En segundos desde el primer contenedor: `postgresql`, `metadata-db` y `rustfs` a 0; el catálogo a 7; Spark a 9; Flink a 41; el pipeline enviado a 57; el simulador a 58; Airflow a 67 y Superset a 90. La primera corrida del DAG empieza sola y termina en 4 min 37 s, con Silver y Gold creados.
- **Repetir el comando no cambia nada.** Con todo en marcha, `docker compose up -d` tarda 23 s y no recrea ningún contenedor. Los seis jobs one-shot vuelven a ejecutarse y terminan con código 0: el bucket, los namespaces, el pipeline y los dos administradores ya existen. Sigue habiendo un solo job de Flink, un slot de replicación y un usuario en cada base de metadatos.
- **Detener y volver a levantar.** `docker compose down` (7 s) y `docker compose up -d` (40 s): el pipeline se reanuda desde su último checkpoint con un job nuevo, el simulador sigue con la película pendiente siguiente sin repetir altas, el DAG lanza su corrida a su hora y Superset conserva lo creado. Con el simulador en pausa para poder comparar, PostgreSQL y Bronze coincidieron en las 20 tablas. Se detuvo entre dos corridas del DAG; pararlo en mitad de una no se probó.

## 41. Separación de responsabilidades

| Componente | Responsabilidad |
|---|---|
| CSV de `raw_data/` | Fuente inicial: un archivo por tabla |
| Java 25 simulator | Generación de actividad transaccional |
| PostgreSQL 19 | Sistema operacional normalizado |
| Flink CDC | Captura continua de cambios |
| Iceberg Bronze | Réplica relacional as-is con columnas CDC y tombstones |
| PySpark #1 | Construcción dimensional + calidad + SCD2 |
| Iceberg Silver | Warehouse dimensional histórico |
| PySpark #2 | Construcción de productos analíticos |
| Iceberg Gold | Serving layer materializada |
| Airflow | Orquestación de los jobs PySpark |
| Iceberg REST Catalog | Catálogo lakehouse compartido |
| RustFS | Object storage S3-compatible |
| DuckDB | Motor SQL analítico, embebido en Superset y en el simulador |
| Superset | Visualización: gráficos y dashboards que crea quien usa el laboratorio |
| `metadata-db` | Metadatos de Airflow y Superset |
| Jobs one-shot | Preparación de bucket, namespaces, pipeline CDC y metadatos |
| Docker Compose | Runtime reproducible del laboratorio |

## 42. Flujo demostrativo esperado

Una demostración completa deberá poder mostrar:

1. Arranque de todo el stack con Docker Compose.
2. PostgreSQL inicialmente preparado con esquema pero sin la carga completa de películas.
3. Arranque de Flink CDC.
4. Java comienza a emitir las películas desde los CSV mediante INSERT.
5. El observador ve llegar las filas a PostgreSQL.
6. Flink captura los cambios.
7. Bronze se actualiza en Iceberg/RustFS.
8. Java genera UPDATE y DELETE posteriores.
9. Los cambios se reflejan mediante CDC.
10. Airflow, que lanza el DAG cada 10 minutos, ejecuta `bronze_to_silver`.
11. Silver crea/actualiza dimensiones SCD2, hechos y bridges.
12. Airflow ejecuta `silver_to_gold`.
13. Gold materializa datasets analíticos.
14. DuckDB consulta Gold.
15. En Superset se conecta la base DuckDB y se crea un gráfico sobre un producto Gold (guía de la sección 35); el gráfico refleja los cambios tras la siguiente corrida.

### Guía de la demostración

Recorre los quince pasos de arriba con el laboratorio en marcha. Lleva unos 25 minutos, casi todos de espera a dos corridas del DAG. Los comandos se lanzan desde la raíz del repositorio; en Git Bash hay que anteponer `MSYS_NO_PATHCONV=1` a los que empiezan por `docker compose exec` o `docker compose --profile`. Las direcciones y las cuentas están en la sección 45.4.

**Antes de empezar.** Para enseñarlo desde el principio, el laboratorio se vuelve a cero (sección 39) y se levanta con `docker compose up -d --build`. Si ya lleva tiempo en marcha, la guía vale igual: solo cambian las cifras.

**1. El arranque (pasos 1 a 3)**

```bash
docker compose ps -a
```

Se ven 13 servicios en `Up` y seis jobs de preparación en `Exited (0)`. En Flink, `http://127.0.0.1:8081`, el job `elastiflix-postgres-to-bronze` está en `RUNNING`: es el pipeline de CDC, y nadie lo lanzó a mano.

**2. El simulador escribe en PostgreSQL (pasos 4 y 5)**

```bash
docker compose logs -f --tail 5 java-simulator
```

Cada línea `TX` es una transacción real: un `INSERT` de una película con todas sus relaciones, un `UPDATE` o un `DELETE`. Se sale con `Ctrl-C`. El número de películas crece si se repite esta consulta:

```bash
docker compose exec postgresql psql -U postgres -d elastiflix -c "SELECT count(*) FROM catalog.movie"
```

La misma actividad se ve y se maneja desde la consola del simulador, con `docker compose attach java-simulator` y cualquier tecla (sección 9.3).

**3. Los cambios llegan a Bronze (pasos 6 a 9)**

```bash
docker compose --profile tools run --rm duckdb -c "SELECT cdc_op_type, count(*) AS filas FROM lake.bronze.movie GROUP BY ALL ORDER BY 1"
```

Bronze guarda el último estado de cada fila y la operación que lo dejó así: `+I` para las insertadas, `+U` para las modificadas y `-D` para las borradas, que no desaparecen: quedan como tombstones. Las cifras cambian de una ejecución a la siguiente, porque Flink escribe cada pocos segundos.

**4. Airflow construye Silver y Gold (pasos 10 a 13)**

En Airflow, `http://127.0.0.1:8080`, el DAG `elastiflix_medallion` está activo y tiene una corrida cada 10 minutos. Cada una tarda entre 4 y 5 minutos; sus siete tareas se ven en la vista de cuadrícula; la última, `mark_run_failed`, queda omitida cuando todo va bien. Cuando una termina en `success`:

```bash
docker compose --profile tools run --rm duckdb -c "SELECT count(*) FILTER (WHERE is_current) AS vigentes, count(*) FILTER (WHERE NOT is_current) AS cerradas, max(version_number) AS version_mas_alta FROM lake.silver.dim_movie"
```

Silver guarda el historial: las versiones vigentes, las cerradas por un cambio o un borrado, y películas que ya van por su segunda o tercera versión.

```bash
docker compose --profile tools run --rm duckdb -c "SELECT count(*) AS peliculas, max(gold_processed_at) AS carga FROM lake.gold.movie_current_overview"
```

Gold tiene solo las películas vivas, y `carga` es el instante de la corrida que lo dejó así.

**5. Superset consulta Gold (pasos 14 y 15)**

Se sigue la guía de la sección 35: conectar la base, registrar `movie_current_overview` como dataset y crear un gráfico de barras, por ejemplo con `primary_genre` en el eje y `COUNT` de `movie_id` como métrica. Conviene añadirlo a un dashboard.

**6. Seguir un cambio de punta a punta**

Se elige un cambio reciente del simulador que se vea bien, por ejemplo un cambio de título:

```bash
docker compose logs --tail 500 java-simulator | grep "title:" | tail -3
```

Cada línea dice el `movie_id` y el título antes y después. Con ese identificador, aquí `174288`, se mira cada capa:

```bash
docker compose exec postgresql psql -U postgres -d elastiflix -c "SELECT movie_id, title FROM catalog.movie WHERE movie_id = 174288"
docker compose --profile tools run --rm duckdb -c "SELECT title, cdc_op_type FROM lake.bronze.movie WHERE movie_id = 174288"
docker compose --profile tools run --rm duckdb -c "SELECT title, version_number, is_current, effective_from, effective_to FROM lake.silver.dim_movie WHERE movie_id = 174288 ORDER BY version_number"
docker compose --profile tools run --rm duckdb -c "SELECT title, gold_processed_at FROM lake.gold.movie_current_overview WHERE movie_id = 174288"
```

PostgreSQL y Bronze ya tienen el título nuevo. Silver y Gold conservan el antiguo hasta la corrida siguiente del DAG. Cuando esa corrida termina, las dos últimas consultas cambian: Silver tiene dos versiones, la antigua cerrada en el instante del cambio y la nueva vigente, y Gold muestra el título nuevo. En Superset basta con recargar el dashboard; la misma película se consulta en SQL Lab con `SELECT title FROM main.movie_current_overview WHERE movie_id = 174288`.

Para provocar el cambio en vez de esperarlo, la consola del simulador tiene la tecla `M`, que lanza una operación a mano sobre la película que se elija.

**7. Cerrar**

`docker compose down` detiene el laboratorio sin perder nada; `docker compose up -d` lo deja donde estaba.

### Comprobado en la fase F11

Los quince pasos se recorrieron con el laboratorio vuelto a cero, y tres cambios del simulador se siguieron por todas las capas. En cada uno se miró el estado antes y después de la corrida del DAG de las 21:36:49 UTC:

| Operación | PostgreSQL | Bronze | Silver, tras la corrida | Gold y Superset, tras la corrida |
|---|---|---|---|---|
| INSERT de la película 71001, a las 21:35:54 | La fila existe | Llega con `+I` en segundos | Versión 1 vigente en `dim_movie` y su foto en `fact_movie_snapshot` | Aparece; antes no estaba |
| UPDATE de medidas de la película 746, a las 21:33:57 | Popularidad 76.012 | La fila pasa a `+U` con el valor nuevo | Una foto nueva en `fact_movie_snapshot`; se conserva la anterior, con 83.513 | Pasa de 83.513 a 76.012 |
| DELETE de la película 1282, a las 21:31:29 | La fila ya no existe | Queda como tombstone, con `-D` | Su versión de `dim_movie` se cierra a las 21:31:29 y se añade una foto con `is_deleted` | Desaparece |

El gráfico creado con la guía de la sección 35 pasó de 111 a 1,528 películas al recargar el dashboard. Entre un cambio y su aparición en Superset pasan como mucho 15 minutos: hasta 10 de espera a la corrida siguiente y 5 de la corrida.

El UPDATE descriptivo, que abre una versión nueva en `dim_movie`, se siguió en la fase F12 al probar la guía de arriba: el cambio de título de la película 174288, a las 22:05:25, dejó en Silver la versión 1 cerrada en ese instante y la versión 2 vigente, y el título nuevo en Gold y en Superset tras la corrida de las 22:06:50. Un cambio intermedio que se deshace o se borra antes de la corrida siguiente no deja versión propia en Silver, porque cada corrida lee el último estado de Bronze.

## 43. 🚀 Trabajo siguiente

El orden de trabajo, las actividades de cada fase y el avance están en el plan: **[planning/PLAN.md](../planning/PLAN.md)**.

Este documento no lleva lista de tareas. Lo que falta por validar o decidir tampoco se planifica aquí: su ejecución es una actividad del plan.

## 44. ✅ Criterio de éxito

El laboratorio se considerará exitoso cuando un revisor externo pueda clonar/copiar el proyecto, levantarlo con Docker Compose y observar un cambio real generado por Java recorrer de extremo a extremo:

![Recorrido de un cambio de extremo a extremo en once pasos: CSV, Java transaction, PostgreSQL WAL, Flink CDC, Iceberg Bronze, Airflow/PySpark, Silver dimensional/SCD2, Airflow/PySpark, Gold materializado, DuckDB y Apache Superset](diagrams/end-to-end-change-path.svg)

> Versión interactiva: [`diagrams/end-to-end-change-path.html`](diagrams/end-to-end-change-path.html) · Fuente editable: [`diagrams/end-to-end-change-path.json`](diagrams/end-to-end-change-path.json).

Comprobado tres veces. En la fase F11, sobre un laboratorio vuelto a cero en el equipo de desarrollo (sección 42). Y en la actividad F12-06 del plan, desde un clon limpio del repositorio en otra carpeta y otra unidad, siguiendo solo el README: copiar `.env.example`, construir las cinco imágenes sin caché (2 min 37 s) y `docker compose up -d --build` (102 s, código 0). La primera corrida del DAG terminó bien a los 6 minutos, y un INSERT, un UPDATE y un DELETE del simulador llegaron a Superset tras la segunda. El clon se extrajo con finales de línea LF aunque el equipo tiene `core.autocrlf=true`, y el laboratorio no dejó en él ningún archivo sin ignorar. Límites de esa prueba: se hizo en el mismo equipo, con las imágenes base ya descargadas, y la base y el dataset de Superset se registraron por su API, no por la interfaz.

**En un segundo equipo, con Linux.** Después de la versión `v1.0.1`, el repositorio se clonó desde GitHub en un equipo con Ubuntu 24.04, Docker Engine 29.10 y Compose v5.8, sin ninguna imagen del laboratorio, y se siguió el README:

| Qué se probó | Resultado |
|---|---|
| Clon y finales de línea | 5 s; los 236 archivos en LF |
| Primer arranque, con todas las descargas | 3 min 54 s para descargar y construir. Falló solo al publicar el puerto 8080, que ese equipo ya usaba |
| Puerto ocupado | Cambiar `AIRFLOW_HOST_PORT` en `.env` y repetir el comando: 21 s, código 0, 13 servicios en marcha |
| Permisos | `volumes-init` dejó `airflow/logs` en 50000:0 y `flink/data` en 9999:9999; nada falló al escribir. Los scripts `.sh` llegan sin permiso de ejecución y no hace falta: se lanzan con `bash` |
| Primera corrida del DAG | 2 min 27 s, frente a los 4 min 37 s del equipo con Windows |
| Un alta, un cambio y una baja | Seguidos hasta Superset, igual que en la fase F11 |
| Repetir el comando | 19 s, ningún contenedor recreado |
| Detener y levantar | `down` 10 s y `up` 29 s; el pipeline retomó desde su checkpoint, y PostgreSQL y Bronze coincidieron en las 20 tablas |
| Vuelta a cero | El bloque de Bash falla por permisos; la variante en contenedor funciona (sección 39) |
| Carga de desarrollo, de principio a fin | 438,925 filas en 2 s; Bronze igual que PostgreSQL en un minuto; el simulador entra en modo continuo; la primera corrida deja 6,899 películas en Gold en 2 min 38 s |
| Directorios de datos sobre disco local | Ningún error 503 del almacén, ningún fallo del TaskManager y ningún checkpoint fallido: lo que describe el riesgo R10 no apareció |

Lo que esa prueba no cubre: la arquitectura `arm64`, macOS, y la guía de Superset en el navegador, que allí se sustituyó por su API.

### Qué se puede volver a comprobar

Las comprobaciones de las fases se hicieron de dos maneras, y solo una queda en el repositorio (decisión 73):

| Se puede repetir con lo que hay en el repositorio | Se midió con scripts que no están versionados |
|---|---|
| Las 71 pruebas unitarias del simulador, que corren al construir su imagen (sección 9.8) | Tiempos de arranque, de cada job y de cada corrida del DAG |
| `python3 raw_data/generate_raw_data.py --validate`, con las 18 validaciones del dataset (sección 8) | Memoria de cada contenedor (sección 39) |
| Las tareas `validate_bronze`, `validate_silver` y `validate_gold`, en cada corrida del DAG (sección 18) | La comparación de PostgreSQL con Bronze, tabla por tabla |
| Los comandos de la guía de la demostración (sección 42) y la guía de Superset (sección 35) | Las comprobaciones de calidad de Silver (117, fase F7), las de Gold contra Silver (38, fase F8) y las del hook de Superset (fase F10) |
| `docker compose config` y `docker compose ps -a`, para la configuración y el estado | El seguimiento de cada INSERT, UPDATE y DELETE capa por capa (fases F11 y F12) |

Las cifras de la columna derecha son las que da la bitácora del plan, con su fecha. No hay forma de reproducirlas con un solo comando.

### Estructura y responsabilidades

El diseño debe ser comprensible desde la estructura de directorios y mantener una separación clara de responsabilidades entre ingestión, CDC, almacenamiento, catálogo, transformación, orquestación, serving y visualización.

## 45. 🔐 Cuentas y credenciales

El laboratorio usa tres clases de cuentas: los usuarios del sistema con los que corre cada contenedor, las cuentas técnicas con las que los servicios se autentican entre sí y las cuentas con las que una persona entra a las herramientas. Ninguna es una cuenta real: todas son credenciales de laboratorio, definidas en `.env`.

### 45.1 Qué necesita la máquina anfitriona

- Un usuario que pueda ejecutar Docker: miembro del grupo `docker` en Linux, o sesión iniciada con Docker Desktop en Windows y macOS. No hacen falta privilegios de administrador para levantar el laboratorio.
- Ninguna cuenta en servicios de nube. Las imágenes se descargan de Docker Hub de forma anónima; iniciar sesión con `docker login` solo ayuda si se alcanza el límite de descargas anónimas.
- Ninguna cuenta de GitHub para ejecutar; solo para clonar si el repositorio fuera privado.

### 45.2 Usuarios del sistema dentro de los contenedores

Ningún servicio de larga duración corre como `root`. Comprobado sobre las imágenes de la sección 3.2:

| Servicio | Usuario | UID:GID | Directorio del host que debe poder escribir |
|---|---|---|---|
| `postgresql`, `metadata-db` | `postgres` | 999:999 | `postgresql/data`, `metadata-db/data`; los prepara la propia imagen, no `volumes-init` |
| `flink-jobmanager`, `flink-taskmanager` | `flink` | 9999:9999 | `flink/data` |
| `spark-master`, `spark-worker` | `spark` | 185:185 | Ninguno |
| `airflow-*` | `airflow` | 50000:0 | `airflow/logs` |
| `superset` | `superset` | 1000:1000 | `superset/data` |
| `rustfs` | `rustfs` | 10001:10001 | El volumen `rustfs-data` |
| `iceberg-rest` | `iceberg` | 1000:1000 | `iceberg/data` |
| `java-simulator` | `simulator` | 10002:10002 | Ninguno; lee `raw_data/` en solo lectura |
| `duckdb` (perfil `tools`) | `duckdb` | 10003:10003 | Ninguno; lee `duckdb/init/` en solo lectura |

- La imagen de PostgreSQL arranca como `root`, ajusta ella misma la propiedad de su directorio de datos y baja a `postgres`. No necesita preparación.
- El resto no puede cambiar la propiedad de su directorio. En Linux, un directorio recién clonado pertenece al usuario del host y el servicio fallaría al escribir; comprobado en Ubuntu 24.04 que `volumes-init` lo resuelve. En Docker Desktop sobre Windows los directorios montados aparecen escribibles para todos y el problema no se manifiesta.
- **Job `volumes-init`.** Un job one-shot que corre como `root`, antes que los servicios con estado, y asigna a cada directorio de la tabla el UID:GID de su servicio. Reutiliza la imagen de RustFS, ya presente en el laboratorio, que trae `sh` y `chown`. Cambia el dueño del directorio, no el de su contenido, y tiene un límite de 64 MB. `iceberg-rest` no depende directamente de él, pero arranca después a través de `rustfs` y `rustfs-init` (sección 40), así que `iceberg/data` ya está preparado.
- `java-simulator` y `duckdb` son las dos imágenes propias sin usuario heredado: sus Dockerfile crean los usuarios `simulator` y `duckdb`.

### 45.3 Cuentas técnicas entre servicios

Cada servicio usa una cuenta propia con el mínimo privilegio que necesita.

| Cuenta | Dónde existe | Quién la usa | Privilegios |
|---|---|---|---|
| `postgres` | PostgreSQL operacional | Scripts de `postgresql/init/` | Superusuario. No la usa ningún servicio en ejecución |
| `elastiflix_app` | PostgreSQL operacional | Event Simulator | `SELECT`, `INSERT`, `UPDATE` y `DELETE` sobre el esquema `catalog` |
| `elastiflix_cdc` | PostgreSQL operacional | Flink CDC | `REPLICATION` y `SELECT` sobre `catalog`. Sin superusuario: comprobado en la validación 1 |
| `postgres` | `metadata-db` | Scripts de `metadata-db/init/` | Superusuario |
| `airflow` | `metadata-db` | Servicios de Airflow | Dueña de la base `airflow`, sin acceso a la base `superset` |
| `superset` | `metadata-db` | Superset | Dueña de la base `superset`, sin acceso a la base `airflow` |
| Clave de acceso de RustFS | RustFS | `rustfs-init`, `iceberg-rest`, Flink, Spark, los servicios de Airflow (driver de Spark), Superset (DuckDB), el simulador (DuckDB) y la línea de comandos de DuckDB | Lectura y escritura sobre el bucket `warehouse` |

- **Una sola clave de RustFS.** Todos los clientes comparten la misma clave de acceso, que llega a cada contenedor en las variables `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY`. Se descartó dar a DuckDB, que nunca escribe, una segunda clave de solo lectura: en un laboratorio local añade un paso de inicialización y dos variables sin reducir un riesgo real. No se llegó a comprobar si RustFS 1.0.6 permite claves con permisos distintos.
- **Sin autenticación:** el Iceberg REST Catalog, el master de Spark y el clúster de Flink no piden credenciales. Solo son alcanzables dentro de la red del Compose o, sus interfaces web, desde `127.0.0.1`.
- **`metadata-db` exige contraseña desde la red.** La imagen oficial de PostgreSQL acepta sin contraseña las conexiones que nacen dentro del propio contenedor (el socket y `127.0.0.1`) y pide `scram-sha-256` a cualquier otra. `metadata-db/init/01-create-databases.sh` crea las cuentas `airflow` y `superset`, cada una dueña de su base, y retira a `PUBLIC` el permiso de conexión en las dos: cada cuenta solo entra en la suya. Comprobado en la fase F2 desde otro contenedor de la red.
- **Secretos internos**, que no son cuentas pero viven junto a ellas: la `SECRET_KEY` de Superset, y en Airflow el secreto JWT que comparten sus servicios, la clave de la API y la clave Fernet.

### 45.4 Cuentas de acceso para personas

Una cuenta administradora por herramienta. No hay cuentas de solo lectura.

| Herramienta | Dirección | Cuenta | Cómo se crea |
|---|---|---|---|
| Superset | `http://127.0.0.1:8088` | Administrador | `superset-init`, con `superset fab create-admin`. Comprobado en la validación 7 |
| Airflow | `http://127.0.0.1:8080` | Administrador | `airflow-init`, con `airflow users create`. Comprobado en la validación 12 |
| Consola de RustFS | `http://127.0.0.1:9001/rustfs/console/` | La clave de acceso de RustFS | No se crea: es la misma clave del servicio, que se escribe en «Cuenta» y «Clave» de la pestaña de inicio de sesión por clave. Comprobado en la fase F4 |
| PostgreSQL operacional | `127.0.0.1:5432` | `postgres` para administrar; `elastiflix_app` para consultar como la aplicación | `postgresql/init/` |
| Flink UI, Spark UI | `http://127.0.0.1:8081`, `:8082` | Ninguna | No tienen inicio de sesión |
| Event Simulator | `docker compose attach java-simulator` | Ninguna | Quien puede ejecutar Docker puede abrir la interfaz |

- **El administrador de Airflow.** Airflow 3 trae por defecto un gestor de autenticación simple, que toma los usuarios de la configuración y guarda las contraseñas en texto plano en un archivo. El laboratorio usa en su lugar el gestor de Flask AppBuilder (sección 18): `airflow-init` crea el administrador con `airflow users create --role Admin`, a partir de `AIRFLOW_ADMIN_USER` y `AIRFLOW_ADMIN_PASSWORD`, y la contraseña queda cifrada en `metadata-db`.
- **`airflow users create` no es idempotente.** `airflow-init` comprueba antes con `airflow users list` si el usuario ya existe, para que repetir `docker compose up` no falle.

### 45.5 Dónde se definen

Todas las credenciales salen de `.env`, que no se versiona. El repositorio incluye `.env.example` con valores de laboratorio, suficientes para levantar el entorno tal cual. Además de las credenciales de esta tabla, `.env.example` lleva las variables que no son secretas: los puertos del host (sección 39), `AWS_REGION` (secciones 14 y 16) y la configuración del simulador (sección 9.6).

| Variable | Para qué |
|---|---|
| `POSTGRES_PASSWORD` | Superusuario del PostgreSQL operacional |
| `ELASTIFLIX_APP_PASSWORD` | Cuenta `elastiflix_app` |
| `ELASTIFLIX_CDC_PASSWORD` | Cuenta `elastiflix_cdc` |
| `METADATA_DB_PASSWORD` | Superusuario de `metadata-db` |
| `AIRFLOW_DB_PASSWORD` | Cuenta `airflow` en `metadata-db` |
| `SUPERSET_DB_PASSWORD` | Cuenta `superset` en `metadata-db` |
| `RUSTFS_ACCESS_KEY`, `RUSTFS_SECRET_KEY` | Clave de RustFS; se exponen a los clientes como `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY` |
| `AIRFLOW_ADMIN_USER`, `AIRFLOW_ADMIN_PASSWORD` | Administrador de Airflow |
| `SUPERSET_ADMIN_USER`, `SUPERSET_ADMIN_PASSWORD` | Administrador de Superset |
| `AIRFLOW_JWT_SECRET`, `AIRFLOW_API_SECRET_KEY`, `AIRFLOW_FERNET_KEY` | Secretos internos de Airflow |
| `SUPERSET_SECRET_KEY` | Secreto interno de Superset |

Reglas:

- Ninguna contraseña se escribe en el `docker-compose.yml`, en un Dockerfile, en el YAML del pipeline ni en el SQL de DuckDB. Todos leen de variables de entorno.
- Los valores de `.env.example` son de laboratorio y están pensados para una máquina local con los puertos ligados a `127.0.0.1`. Quien exponga el laboratorio fuera de su máquina debe cambiarlos. Es el único archivo versionado que lleva credenciales (decisión 66); las contraseñas y los secretos se generaron al azar una sola vez.
- Las contraseñas de `elastiflix_app` y `elastiflix_cdc` las aplica el script de inicialización de PostgreSQL leyendo las variables; no se versionan dentro del SQL. `06-roles.sql` crea las cuentas sin contraseña y `07-role-passwords.sh` se la pone a partir de `ELASTIFLIX_APP_PASSWORD` y `ELASTIFLIX_CDC_PASSWORD`; si falta alguna, la inicialización se detiene.

## 46. 📚 Decisiones y validaciones

Las decisiones tomadas durante el diseño, las que siguen abiertas, las descartadas, las validaciones ejecutadas con sus resultados y el registro de cambios de cada revisión viven en un documento propio: **[DECISIONS-AND-VALIDATIONS.md](DECISIONS-AND-VALIDATIONS.md)**.

Este documento describe el diseño vigente. Aquel explica por qué es así y qué se probó para sostenerlo.

| Qué | Estado |
|---|---|
| Validaciones 1 a 9, de compatibilidad entre componentes | Superadas |
| Validación de volumen con las 20 tablas y el dataset completo | Superada |
| `MERGE` SCD2 de Silver y mantenimiento a volumen | Superadas |
| Pérdida de checkpoints | Falla si se repite el snapshot sobre Bronze. Se resuelve reconstruyendo Bronze (sección 38): comprobado |
| Validación 12, inicio de sesión en Airflow | Superada |
| Validación 10, consola Lanterna con `docker compose attach` | Superada, con ajustes al diseño |
| Validación 11, DuckDB JDBC desde Java 25 | Superada, con ajustes al diseño |
| Decisiones abiertas | Ninguna |
