# 🎬 ElastiFlix PostgreSQL CDC Lakehouse Lab

> 🟦 **CDC** · 🟪 **Lakehouse** · 🟩 **Medallion Architecture** · 🟨 **SCD Type 2** · 🟥 **BI**
>
> **Laboratorio local, reproducible y orientado a demostración técnica**, construido completamente con contenedores y un único `docker compose up`.

## 1. Propósito

Este documento consolida las decisiones acordadas para diseñar e implementar un laboratorio reproducible de ingeniería de datos end-to-end para **ElastiFlix**.

El laboratorio simulará actividad transaccional sobre PostgreSQL 19, capturará cambios mediante Apache Flink CDC, persistirá las capas de datos con Apache Iceberg sobre almacenamiento S3-compatible local, construirá un modelo dimensional mediante PySpark, materializará productos analíticos para consumo y los expondrá mediante DuckDB y Apache Superset.

Todo el entorno deberá levantarse desde un único `docker-compose.yml`.

> 📝 **Revisión 5 (2026-11-22):** el simulador pasa a tener una interfaz de consola enriquecida (sección 9), se añade la sección de cuentas y credenciales (sección 45), y las decisiones, las validaciones y el registro de cambios se trasladan a un documento propio. Ver [DECISIONS-AND-VALIDATIONS.md](DECISIONS-AND-VALIDATIONS.md).

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
- 📊 Consumir Gold desde Apache Superset a través de DuckDB.
- ⏱️ Orquestar `bronze_to_silver.py` y `silver_to_gold.py` mediante Apache Airflow.
- 🧰 Inicializar bucket, namespaces, pipeline CDC, metadatos de Airflow y Superset mediante jobs one-shot declarados en el mismo Docker Compose.

### 2.2 Requisitos técnicos

- 🐳 Docker Engine con Docker Compose v2 o posterior. En Windows, Docker Desktop con el backend WSL 2; el repositorio puede vivir en una unidad NTFS (los bind mounts y el cambio de propietario de los directorios `data/` se comprobaron ahí).
- CPU x86_64/amd64 o ARM64 con imágenes compatibles para todos los componentes seleccionados.
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
| Apache Superset | **6.1.0** | `apache/superset:6.1.0-py312` | BI y dashboards | Presentar el resultado final: dashboards construidos sobre Gold |
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

Todas las imágenes base del laboratorio están publicadas en Docker Hub para `linux/amd64` y `linux/arm64`. Comprobado el 2026-11-22 con `docker manifest inspect` y la API de etiquetas de Docker Hub.

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
| `duckdb` (perfil `tools`) | `duckdb/duckdb:1.5.6` | 2026-09-29 |

Los componentes que son librerías no tienen imagen propia: se instalan durante el build de la imagen que los aloja.

| Componente | Dónde se instala | Origen |
|---|---|---|
| Flink CDC 3.7.0 (distribución y conectores `3.7.0-2.2`) | Imagen de Flink | Descargas de Apache y Maven Central |
| Iceberg 1.10.2 (`iceberg-flink-runtime-2.0`, `iceberg-aws-bundle`) | Imagen de Flink | Maven Central |
| Iceberg 1.12.0 (`iceberg-spark-runtime-4.1_2.13`, `iceberg-aws-bundle`) | Imágenes de Spark y Airflow | Maven Central |
| JDBC 42.7.14, Commons CSV 1.14.1, Lanterna 3.1.5 y DuckDB JDBC 1.5.6.0 | JAR del simulador | Maven Central |
| Extensiones `httpfs`, `iceberg` y `avro` de DuckDB | Imagen del simulador | Repositorio de extensiones de DuckDB |
| PySpark 4.1.4, `pyspark-client` 4.1.4 y proveedor Spark 6.3.4 | Imagen de Airflow | PyPI |
| Java 21 (`openjdk-21-jre-headless`) | Imagen de Airflow | Repositorio de paquetes de Debian |
| Python 3.12, instalado con `uv` | Imagen de Spark | PyPI (`uv`) y builds de CPython que descarga `uv` desde GitHub |
| DuckDB 1.5.6, `duckdb-engine` 0.17.0, `psycopg2-binary` y extensiones `httpfs`, `iceberg` y `avro` | Imagen de Superset | PyPI y repositorio de extensiones de DuckDB |

Los jobs one-shot (`volumes-init`, `rustfs-init`, `iceberg-init` y `airflow-init`) reutilizan alguna de las imágenes anteriores; no añaden imágenes nuevas al laboratorio.

## 4. 🗺️ Diagrama de Arquitectura

![Arquitectura end-to-end del laboratorio ElastiFlix: de los CSV a Superset pasando por PostgreSQL, Flink CDC, las tres capas Iceberg, PySpark, Airflow y DuckDB](diagrams/lab-architecture.svg)

> 🔍 **Cómo leerlo:** la columna central es el camino del dato, de arriba abajo. Airflow (izquierda) solo lanza los dos jobs PySpark. Las tres capas quedan registradas en el Iceberg REST Catalog y sus archivos viven en RustFS (derecha). Por legibilidad no se dibuja una flecha de cada motor hacia el catálogo: Flink, Spark y DuckDB resuelven las tablas ahí.
>
> Versión interactiva: [`diagrams/lab-architecture.html`](diagrams/lab-architecture.html) · Fuente editable: [`diagrams/lab-architecture.json`](diagrams/lab-architecture.json). Los diagramas de este documento se generan con [Archify](https://github.com/tt-a1i/archify); ver [sección 7](#7--estructura-propuesta-del-repositorio).

### Flujo principal

**📄 CSV → ☕ Java → 🐘 PostgreSQL → 🌊 Flink CDC → 🥉 Bronze → ⚡ PySpark → 🥈 Silver → ⚡ PySpark → 🥇 Gold → 🦆 DuckDB → 📊 Superset**

### Plano de control y almacenamiento

- 🧭 **Iceberg REST Catalog**: catálogo compartido para las tablas Iceberg.
- 🪣 **RustFS**: almacenamiento físico S3-compatible de Bronze, Silver y Gold.
- ⏱️ **Airflow**: controla únicamente los jobs PySpark del pipeline analítico.
- 🌊 **Flink CDC**: permanece ejecutándose continuamente y no depende del scheduler batch.
- 🦆 **DuckDB**: no es un servicio de red. Es una librería que corre dentro del contenedor de Superset y, opcionalmente, en un contenedor de línea de comandos para exploración.

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
20. Cada volumen persistente de Docker deberá vivir dentro del directorio del servicio al que pertenece, para facilitar la revisión externa.
21. Todo paso de preparación (bucket, namespaces, envío del pipeline CDC, migraciones de metadatos) será un job one-shot del mismo Docker Compose. No habrá pasos manuales entre `docker compose up` y el primer dato en Bronze.
22. Los metadatos de Airflow y Superset vivirán en una base PostgreSQL separada (`metadata-db`), no en la base operacional que se captura por CDC.

## 6. 🏗️ Arquitectura end-to-end

El diagrama de la sección 4 muestra los componentes. Este muestra qué datos pasan de una capa a la siguiente y quién los mueve.

![Linaje de datos por capa: CSV, tablas operacionales de PostgreSQL, tablas espejo de Bronze, dimensiones, hechos y bridges de Silver, productos Gold y consumo en Superset](diagrams/medallion-dataflow.svg)

> 🔍 **Cómo leerlo:** de izquierda a derecha. Las flechas verdes son captura continua de Flink CDC; las grises, el resto de movimientos (la carga transaccional del simulador, los jobs batch de PySpark y la consulta de Superset); las punteadas, resolución de claves dentro de Silver. Los bridges también alimentan Gold (pesos N:M), aunque esa flecha no se dibuja.
>
> Versión interactiva: [`diagrams/medallion-dataflow.html`](diagrams/medallion-dataflow.html) · Fuente editable: [`diagrams/medallion-dataflow.json`](diagrams/medallion-dataflow.json).

Resumen de quién escribe y quién lee cada capa:

| Capa | Escribe | Lee | Contenido |
|---|---|---|---|
| PostgreSQL `catalog` | Event Simulator | Flink CDC | 20 tablas normalizadas |
| 🥉 Bronze | Flink CDC | `bronze_to_silver.py` | 20 tablas espejo + `cdc_op_type`, `cdc_op_ts` |
| 🥈 Silver | `bronze_to_silver.py` | `silver_to_gold.py` | 14 dimensiones, 2 hechos, 6 bridges |
| 🥇 Gold | `silver_to_gold.py` | DuckDB (Superset) | 7 productos analíticos |

Las tres capas comparten catálogo (Iceberg REST Catalog) y almacenamiento (RustFS, `s3://warehouse/`).

## 7. 📁 Estructura propuesta del repositorio

El directorio raíz coincide con el nombre del repositorio:

```text
postgresql-19-cdc-duckdb/
```

```text
postgresql-19-cdc-duckdb/
|
|-- docker-compose.yml
|-- .env.example
|-- .gitattributes
|-- .gitignore
|-- CLAUDE.md
|-- README.md
|
|-- lab-design/
|   |-- LAB-DESIGN.md
|   `-- diagrams/
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
|-- rustfs/
|   `-- data/
|
|-- pyspark/
|   |-- Dockerfile
|   |-- jobs/
|   |   |-- bronze_to_silver.py
|   |   `-- silver_to_gold.py
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
|   `-- init/
|
`-- superset/
    |-- Dockerfile
    |-- data/
    `-- config/
```

Notas sobre la estructura:

- `.env.example` se versiona; `.env` es local y queda en `.gitignore`, igual que el contenido de todos los directorios `data/` y `logs/`.
- Cada directorio vacío lleva un archivo `.gitkeep` para que Git lo conserve y la estructura sea visible al clonar. En los directorios `data/` y `logs/` ese marcador es lo único que se versiona.
- `.gitattributes` fuerza finales de línea LF en todo archivo de texto. Los scripts, SQL, YAML y jobs de este repositorio se ejecutan dentro de contenedores Linux, y un clon en Windows con `core.autocrlf=true` los dejaría con CRLF, que rompe la ejecución. El dataset `*.csv` queda excluido de cualquier conversión.
- `lab-design/diagrams/` guarda, por cada diagrama, la fuente `.json`, la página interactiva `.html` y el `.svg` que se incrusta en la documentación. Se regeneran con Archify: `archify finalize <tipo> <fuente>.json <salida>.html` y `export-svg.mjs <salida>.html <salida>.svg auto`.
- `raw_data/` contiene el dataset de entrada descrito en la sección 8: un CSV por tabla, el script que los genera y su README.
- `postgresql/` usa la imagen oficial sin Dockerfile propio; `postgresql/init/` contiene el DDL, los roles y la publicación.
- `metadata-db/` es el PostgreSQL de metadatos de Airflow y Superset.
- `flink/jobs/` contiene el YAML del pipeline CDC y `flink/data/` los checkpoints. Los JAR se descargan en el build, por eso no hay `flink/lib/`.
- `pyspark/reference/` contiene los datos de referencia versionados que Silver usa para enriquecer catálogos (nombres de idioma, códigos de país, descripción de ratings).
- `duckdb/init/` contiene el SQL que adjunta el lakehouse; lo comparten Superset y el contenedor de línea de comandos. DuckDB no guarda datos propios, por eso no hay `duckdb/data/`.

### Regla de persistencia

Cada bind mount o volumen persistente deberá residir dentro del directorio del servicio propietario.

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
    - ./rustfs/data:/data

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

> ⚠️ **Permisos de los bind mounts:** varias imágenes corren con un usuario no root y necesitan que el directorio del host sea escribible por ese UID. RustFS usa `10001:10001` y Airflow `50000:0`. El job one-shot `volumes-init` ajusta la propiedad de esos directorios antes de arrancar los servicios (sección 45.2).

No se utilizará un directorio raíz genérico `volumes/`.

## 8. 🎞️ Dataset fuente ElastiFlix

El dataset de entrada son **20 archivos CSV, uno por cada tabla del esquema `catalog`**, en `raw_data/`. El simulador los lee ya normalizados y con sus claves.

### 8.1 Naturaleza de los datos

- **Los datos son sintéticos.** Títulos, sinopsis, personas y compañías son inventados; no reproducen películas, personas ni textos reales.
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
- RFC 4180: separador coma, comillas dobles solo cuando hacen falta y comilla doble escapada duplicándola. `plot` y `overview` contienen saltos de línea y comillas dentro de la celda.
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
| RF-05 | Ser reproducible: con la misma semilla y sin intervención manual, la secuencia de operaciones es la misma. |
| RF-06 | **Ver la actividad en vivo:** estado de la simulación, avance sobre las 6,899 películas, contadores por tipo de operación, ritmo de transacciones y las últimas transacciones con su detalle. |
| RF-07 | **Controlar la simulación en caliente:** iniciar, pausar y reanudar, y cambiar la velocidad y los pesos sin reiniciar. |
| RF-08 | **Lanzar operaciones a mano:** elegir una película y provocar un INSERT, un UPDATE de un tipo concreto, un DELETE o una reinserción. |
| RF-09 | **Seguir el cambio aguas abajo:** indicar, para cada transacción reciente, si su cambio ya llegó a Bronze y cuánto tardó. |
| RF-10 | Funcionar también sin terminal interactiva: si no hay TTY, arranca solo y escribe una línea de log por transacción. |
| RF-11 | Registrar cada transacción, cada cambio de configuración y cada operación manual en el log, con nivel y marca de tiempo. |
| RF-12 | Ante un dato inconsistente, revertir la transacción de esa película, registrarla con nivel `ERROR` y continuar. |

### 9.2 Requisitos no funcionales

- **Sin dependencias en el host.** Corre en su contenedor; la interfaz se usa con `docker compose attach java-simulator`, y se sale de ella sin detener el simulador.
- **Arranque con un único `docker compose up`.** Por defecto empieza a simular en cuanto el pipeline CDC está en marcha, haya o no alguien mirando la interfaz.
- **No bloquea por la interfaz.** La simulación y el refresco de pantalla corren en hilos distintos; un terminal lento o cerrado no detiene las transacciones.
- **El seguimiento aguas abajo es opcional y de solo lectura.** Si Bronze no responde, las transacciones siguen y la columna de seguimiento muestra «sin datos».
- **Memoria acotada:** 0.5 GB (sección 39). El dataset completo ocupa unas decenas de MB en memoria.
- **Usuario sin privilegios** en el contenedor y cuenta `elastiflix_app` en PostgreSQL (sección 45).
- **Terminal mínima:** 100 columnas por 30 filas, con UTF-8. Por debajo de ese tamaño la interfaz lo avisa en lugar de descomponerse.

### 9.3 Interfaz de consola

La pantalla tiene cinco zonas fijas:

```text
┌ ElastiFlix Event Simulator ───────────────────────────── ▶ EN MARCHA ─ semilla 42 ┐
│ PostgreSQL: conectado (elastiflix_app)     Bronze: conectado     Intervalo: 250 ms │
├ Avance ─────────────────────────────────────┬ Operaciones ─────────────────────────┤
│ Películas insertadas   1,284 / 6,899  18.6% │ INSERT   1,284   peso 70             │
│ ███████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │ UPDATE     391   peso 25             │
│ Vivas en catalog       1,251                │ DELETE      33   peso  5             │
│ Ritmo                  3.9 tx/s             │ Errores      0   Manuales  2         │
├ Últimas transacciones ─────────────────────────────────────────────────────────────┤
│ Hora      Op      movie_id  Título                    Filas   ms   Bronze          │
│ 14:02:11  INSERT    313951  The Silent Harbor            61   18   ✓ 31 s          │
│ 14:02:11  UPDATE     27205  Ashes of Winter (medidas)     1    4   ✓ 29 s          │
│ 14:02:10  DELETE       550  Northfall                    44    9   … pendiente     │
│ 14:02:10  INSERT    316393  Paper Lanterns               38   15   … pendiente     │
├ Detalle ───────────────────────────────────────────────────────────────────────────┤
│ INSERT 313951: movie 1 · movie_genre 3 · movie_keyword 16 · movie_cast 38 · …      │
├────────────────────────────────────────────────────────────────────────────────────┤
│ [Espacio] pausar  [+/-] velocidad  [P] pesos  [M] manual  [↑↓] recorrer  [Q] salir │
└────────────────────────────────────────────────────────────────────────────────────┘
```

| Zona | Contenido |
|---|---|
| Cabecera | Estado (`EN MARCHA`, `EN PAUSA`, `TERMINADO`), semilla, conexión a PostgreSQL, conexión a Bronze e intervalo vigente |
| Avance | Películas insertadas sobre el total, barra de progreso, películas vivas en `catalog` y ritmo de transacciones |
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
| `Q` | Sale de la interfaz. Pregunta si además debe detenerse el simulador |

**Operación manual (`M`).** Se elige la película escribiendo su `movie_id` o parte del título, y después la operación:

- INSERT de la siguiente película pendiente, o de una concreta que aún no esté en `catalog`.
- UPDATE descriptivo, de medidas o de relaciones sobre una película viva.
- DELETE de una película viva.
- Reinserción de una película borrada.

La operación se ejecuta como una transacción normal, aparece en la lista marcada como manual y queda en el log. Funciona también con la simulación en pausa, que es el modo previsto para una demostración: pausar, lanzar un cambio y seguirlo hasta Bronze, Silver y Superset.

**Seguimiento aguas abajo (RF-09).** La columna `Bronze` de cada transacción pasa de «pendiente» a «✓» con el tiempo transcurrido cuando el cambio aparece en `bronze.movie`: la fila con ese `movie_id` y un `cdc_op_ts` igual o posterior al de la transacción, o el tombstone si fue un DELETE. El simulador lo comprueba con DuckDB embebido y el mismo SQL de inicialización que usa Superset (sección 34), consultando por lotes las transacciones pendientes cada pocos segundos. El retraso esperable es del orden del intervalo de checkpoint de Flink, 30 s.

### 9.4 Modo sin interfaz

Sin TTY, por ejemplo al ver `docker compose logs java-simulator`, el simulador no dibuja la pantalla. Arranca según su configuración y escribe una línea por transacción con los mismos datos de la lista. Es el modo que usa el arranque normal del laboratorio; la interfaz se abre después con `docker compose attach`.

### 9.5 Reglas de carga

- **Alta perezosa de catálogos y entidades.** Ninguna tabla se precarga. Una fila de `movie_status`, `content_rating`, `original_language`, `enrichment_field`, `genre`, `keyword`, `person`, `production_company`, `production_country`, `spoken_language` o `collection` se inserta la primera vez que una película la necesita, dentro de la transacción de esa película. El simulador recuerda qué claves ya insertó.
- **Identificadores del archivo.** Toda fila se inserta con la clave que trae el CSV, también en las cinco tablas de clave sustituta (sección 8.4).
- **Datos inconsistentes.** Si una película falla por una clave duplicada o una referencia inexistente, el simulador revierte su transacción, lo registra con nivel `ERROR` y continúa con la siguiente. No intenta corregir el dato.
- **Tipos de UPDATE.** El simulador alterna tres clases, para ejercitar los tres caminos de Silver: descriptivo (`title`, `tagline`, `overview`, `homepage`), de medidas (`popularity`, `vote_count`, `vote_average`, `user_score`, `budget_usd`, `revenue_usd`) y de relaciones (añadir o quitar un género o una keyword, tomados de los que ya existen en PostgreSQL). Todo UPDATE sobre `movie`, `collection` o `keyword` actualiza `updated_at`.
- **DELETE.** Siempre sobre `movie`; las relaciones caen por `ON DELETE CASCADE`.
- **Modo continuo.** Con `SIMULATOR_CONTINUOUS=true`, al agotar `movie.csv` el simulador sigue generando UPDATE y DELETE, y puede volver a insertar una película borrada con los datos de los archivos. Silver trata esa reinserción como una reactivación (sección 31). Con `false`, pasa a `TERMINADO` al agotar `movie.csv`, pero sigue aceptando operaciones manuales.
- **Reproducibilidad.** La semilla gobierna la secuencia automática. Una operación manual o un cambio de pesos la altera a partir de ese punto; ambos quedan en el log para poder reconstruir lo ocurrido.

### 9.6 Configuración

Valores iniciales, por variables de entorno. Los cuatro primeros se pueden cambiar después desde la interfaz.

| Variable | Significado |
|---|---|
| `SIMULATOR_DELAY_MS` | Intervalo entre transacciones |
| `SIMULATOR_INSERT_WEIGHT` | Peso de INSERT |
| `SIMULATOR_UPDATE_WEIGHT` | Peso de UPDATE |
| `SIMULATOR_DELETE_WEIGHT` | Peso de DELETE |
| `SIMULATOR_RANDOM_SEED` | Semilla de la secuencia automática |
| `SIMULATOR_CONTINUOUS` | Seguir generando cambios al agotar `movie.csv` |
| `SIMULATOR_AUTOSTART` | Empezar a simular al arrancar (`true` por defecto) o esperar en pausa |
| `SIMULATOR_TRACK_BRONZE` | Activar el seguimiento aguas abajo (`true` por defecto) |

Los pesos no forman parte de ninguna restricción del modelo.

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

En el Compose, el servicio `java-simulator` declara `tty: true` y `stdin_open: true` para que la interfaz pueda abrirse con `docker compose attach java-simulator`. Se sale de la interfaz sin detener el contenedor con la secuencia de desconexión de Docker (`Ctrl-P`, `Ctrl-Q`) o con `Q`.

El seguimiento aguas abajo hace que el simulador conozca el catálogo Iceberg y RustFS, cosa que antes no ocurría. Es una dependencia de solo lectura y desactivable; el camino del dato no cambia.

> ⚠️ **Por validar antes de implementar.** Dos puntos de esta sección no se han probado: que una interfaz Lanterna funcione dentro del contenedor a través de `docker compose attach`, también desde una terminal de Windows; y que DuckDB JDBC 1.5.6.0 adjunte el catálogo y lea Bronze desde Java 25. Figuran como validaciones 10 y 11 en el documento de decisiones y validaciones.

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

`max_slot_wal_keep_size` acota el WAL que el slot puede retener si Flink está detenido; sin él, un Flink caído llena el disco del host.

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

```text
PostgreSQL                   Uso
-------------------------------------------------
bigint                       claves
integer                      conteos/posiciones
numeric(p,s)                 valores decimales exactos
text                         texto/códigos
boolean                      indicadores
date                         fecha de calendario
timestamp(6) with time zone  timestamps operativos
```

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
- `poster_path` y `backdrop_path` son rutas relativas.
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

Catálogo de los 21 campos documentados de `enrichment`.

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

```text
catalog.movie                     -> bronze.movie
catalog.collection                -> bronze.collection
catalog.movie_genre               -> bronze.movie_genre
catalog.movie_cast                -> bronze.movie_cast
catalog.movie_enrichment          -> bronze.movie_enrichment
```

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
  password: <secreto del laboratorio>
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
- **Creación de tablas.** El conector crea automáticamente el namespace `bronze` y sus tablas; no hay DDL de Bronze que mantener.
- **Formato v2.** Se fija `format-version: 2`, que es el que soporta el flujo de UPDATE y DELETE.

### Garantías y requisitos operativos

- **Checkpointing obligatorio.** El sink de Iceberg publica los datos en cada checkpoint de Flink; sin checkpointing Bronze queda vacío. Se fijará `execution.checkpointing.interval` (propuesta: 30 s) y los checkpoints se guardarán en `flink/data/`.
- **At-least-once.** El sink no ofrece exactly-once: reintenta y se apoya en la clave primaria para escribir de forma idempotente. Por eso todas las tablas capturadas tienen PK.
- **Una sola base.** El conector PostgreSQL captura tablas de una única base de datos; `elastiflix` cumple.
- **Catálogo REST.** La documentación del sink enumera los tipos `hadoop`, `hive` y `glue`, además de `catalog-impl` para una implementación propia. El catálogo REST se configura por esa segunda vía, como muestra el borrador; la validación 2 confirmó que funciona.
- **Credenciales S3.** El borrador no lleva claves. `S3FileIO` las toma de las variables de entorno `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` y `AWS_REGION`, que deben declararse tanto en `flink-jobmanager` como en `flink-taskmanager`. Así las credenciales viven en `.env` y no en el YAML del pipeline.
- **Dependencias en la imagen de Flink.** Las que lista la guía oficial para Flink 2.2.1: la distribución de Flink CDC 3.7.0 para Flink 2.2, los conectores `flink-cdc-pipeline-connector-postgres` y `flink-cdc-pipeline-connector-iceberg` (`3.7.0-2.2`) en `$FLINK_CDC_HOME/lib`, y en `$FLINK_HOME/lib` el `iceberg-flink-runtime-2.0`, Hadoop client API y runtime 3.3.6 y Commons Logging 1.2. La guía usa Iceberg 1.10.1; este laboratorio toma el último parche de esa línea, 1.10.2, y añade `iceberg-aws-bundle` 1.10.2 para `S3FileIO`. Hadoop se mantiene en la 3.3.6 que indica la guía aunque exista la 3.5.0, porque forma parte del conjunto probado con el conector. El conector PostgreSQL ya incluye su driver JDBC.
- **Reinicio.** Si cae el TaskManager, el job se recupera solo desde su último checkpoint. Si se reinicia el JobManager, el job se pierde: el clúster standalone no tiene alta disponibilidad y arranca sin jobs. Hay que reenviar el pipeline con `--from-savepoint` apuntando al último checkpoint retenido; así retoma sin repetir el snapshot y entrega lo que cambió mientras estuvo parado. El slot de replicación permanece en PostgreSQL entre tanto.
- **Checkpoints retenidos y compartidos.** Para que ese reenvío sea posible, los checkpoints se guardan en `flink/data/`, montado en la misma ruta en el JobManager y en el TaskManager, con `execution.checkpointing.dir: file:///opt/flink/state/checkpoints` y `execution.checkpointing.externalized-checkpoint-retention: RETAIN_ON_CANCELLATION`. Flink corre como usuario `flink`: el directorio debe pertenecerle antes de arrancar.
- **`flink-cdc-submit` idempotente de verdad.** El job one-shot sigue esta regla cada vez que se ejecuta:
  1. Consulta la API REST de Flink. Si ya hay un job en ejecución con el nombre del pipeline, termina sin hacer nada.
  2. Si no lo hay y existe un checkpoint retenido en `flink/data/`, reenvía con `--from-savepoint` hacia el más reciente.
  3. Solo si no hay ni job ni checkpoint hace un envío nuevo, con snapshot inicial. Si en ese momento Bronze ya tiene tablas, se trata de una pérdida de estado y aplica el punto siguiente.

  Sin esta regla, repetir `docker compose up` es dañino. Un segundo envío no falla: Flink lo acepta y arranca otro job que repite el snapshot completo sobre las mismas tablas. Bronze sigue cuadrando en filas, pero todas vuelven a `+I` con el `cdc_op_ts` del nuevo snapshot, se pierde la marca `+U` y la fecha real de cada cambio, y se acumula un delete de igualdad por cada fila reescrita.
- **Perder los checkpoints no es inocuo.** Un envío nuevo repite el snapshot, pero el snapshot solo ve lo que existe: una fila borrada en PostgreSQL mientras no había job no vuelve a leerse y queda en Bronze como viva, sin tombstone. En la prueba del documento de decisiones y validaciones, 3 películas borradas durante la parada y 89 filas de sus relaciones siguieron contando como vivas. Por eso los checkpoints se persisten y, si aun así se pierden, hace falta reconciliar. La forma de reconciliar es la decisión abierta D-2 del [documento de decisiones y validaciones](DECISIONS-AND-VALIDATIONS.md).

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

Persistencia local:

```text
rustfs/data/
```

Los demás servicios no manipularán directamente ese directorio. Accederán mediante el endpoint S3.

Detalles de operación:

- Imagen `rustfs/rustfs:1.0.6`; API S3 en el puerto 9000 y consola en el 9001.
- El contenedor corre como `10001:10001`; `rustfs/data/` debe ser escribible por ese usuario.
- Credenciales por las variables `RUSTFS_ACCESS_KEY` y `RUSTFS_SECRET_KEY`; healthcheck contra `/health/ready`.
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
- El job one-shot `iceberg-init` crea los namespaces `bronze`, `silver` y `gold`.
- Sin autenticación: el catálogo solo es alcanzable dentro de la red del Compose.
- Alternativas si la imagen de referencia se queda corta: Lakekeeper o Apache Polaris. Cambiar de catálogo no altera el resto del diseño porque todos los motores hablan el protocolo REST.

## 17. 🥉 Capa BRONZE

### Objetivo

Réplica relacional `as-is` del sistema operacional PostgreSQL.

No se realiza modelado dimensional en esta capa.

Inventario aproximado:

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

Airflow gobernará exclusivamente el procesamiento analítico PySpark.

Pipeline lógico (DAG `elastiflix_medallion`):

![DAG de Airflow: validate_bronze, bronze_to_silver, validate_silver, silver_to_gold, validate_gold e iceberg_maintenance, con los jobs PySpark y las capas Iceberg que tocan](diagrams/airflow-medallion-dag.svg)

> 🔍 **Cómo leerlo:** la fila superior es el DAG, de izquierda a derecha. Cada tarea de transformación lanza un job PySpark (fila central) que lee una capa y escribe la siguiente (fila inferior). Cada `validate_*` consulta la capa de su mismo nombre.
>
> Versión interactiva: [`diagrams/airflow-medallion-dag.html`](diagrams/airflow-medallion-dag.html) · Fuente editable: [`diagrams/airflow-medallion-dag.json`](diagrams/airflow-medallion-dag.json).

Tareas:

| Tarea | Qué hace | Si falla |
|---|---|---|
| `validate_bronze` | Comprueba que existen las 20 tablas y que `max(cdc_op_ts)` es reciente | El DAG se detiene; Silver conserva su último estado |
| `bronze_to_silver` | `SparkSubmitOperator` sobre `bronze_to_silver.py` | Se reintenta; el job es idempotente |
| `validate_silver` | Una sola versión vigente por business key, rangos SCD2 sin solapes, sin SK huérfanas | El DAG se detiene; Gold conserva su último estado |
| `silver_to_gold` | `SparkSubmitOperator` sobre `silver_to_gold.py` | Se reintenta; Gold se recarga completo |
| `validate_gold` | Conteos mínimos y columnas clave sin nulos | El DAG queda en error; Superset sigue mostrando la carga anterior |
| `iceberg_maintenance` | Compacta Bronze y expira snapshots antiguos | No bloquea la corrida siguiente |

Las validaciones son consultas PySpark o SQL sencillas con aserciones; no se añade un framework de calidad de datos.

Airflow no gobernará cada evento CDC.

### Despliegue de Airflow

- Imagen propia basada en `apache/airflow:3.4.0-python3.12`, con Java 21, PySpark 4.1.4 y `apache-airflow-providers-apache-spark` 6.3.4. La versión de PySpark del cliente debe coincidir con la del clúster Spark.
- El proveedor 6.3.4 depende de `pyspark-client>=4.0.0` sin tope superior, así que por sí solo instalaría la 4.3.0. Se fijan `pyspark==4.1.4` y `pyspark-client==4.1.4` en el mismo `pip install`.
- **Misma versión menor de Python en Airflow y en Spark.** `SparkSubmitOperator` lanza `spark-submit` en modo cliente contra el clúster standalone, que no admite modo clúster para aplicaciones Python. El driver corre entonces dentro del contenedor de Airflow y los ejecutores dentro de `spark-worker`; si sus versiones menores de Python difieren, PySpark aborta el job. La imagen base de Spark trae Python 3.10 (Ubuntu 22.04) y Airflow no publica imagen con 3.10, por lo que `pyspark/Dockerfile` instala Python 3.12 y fija `PYSPARK_PYTHON` a ese intérprete. La validación 8 del documento de decisiones y validaciones reprodujo el fallo y comprobó la solución.
- **Cómo se instala Python 3.12 en la imagen de Spark.** Con `uv`: `pip3 install uv`, `uv python install 3.12` con `UV_PYTHON_INSTALL_DIR=/opt/python` y un enlace `/usr/local/bin/python3.12`. No toca el Python 3.10 del sistema ni añade repositorios de paquetes. La imagen declara `PYSPARK_PYTHON=python3.12`, y la de Airflow también: el driver comunica a los ejecutores el nombre del intérprete y cada lado lo resuelve en su `PATH`.
- **Solo fallan los jobs que ejecutan Python en los ejecutores.** Un job que use únicamente la API de DataFrame corre aunque las versiones no coincidan; una UDF de Python o una operación sobre RDD aborta con `PYTHON_VERSION_MISMATCH`. No conviene apoyarse en esa diferencia: basta una UDF para romper un job que antes funcionaba.
- **Lo que necesita la imagen de Airflow para ser driver.** Java 21 (`openjdk-21-jre-headless`, con `JAVA_HOME`), los JAR `iceberg-spark-runtime-4.1_2.13` e `iceberg-aws-bundle` 1.12.0 dentro del directorio `jars` del paquete `pyspark`, y `SPARK_CONF_DIR` apuntando a la misma configuración de catálogo que usa Spark (`pyspark/conf/`, documento de decisiones y validaciones). El comando `spark-submit` lo aporta el propio paquete `pyspark`.
- **Los jobs se montan también en Airflow.** En modo cliente `spark-submit` lee el archivo de la aplicación en la máquina que lo lanza, así que `pyspark/jobs/` y `pyspark/conf/` se montan en los contenedores de Airflow además de en los de Spark.
- **El driver debe ser alcanzable desde los ejecutores.** Cada tarea fija `spark.driver.host` al nombre del servicio que ejecuta las tareas (`airflow-scheduler`, con `LocalExecutor`) y `spark.driver.bindAddress=0.0.0.0`.
- **Conexión de Spark.** `AIRFLOW_CONN_SPARK_DEFAULT=spark://spark-master:7077?deploy-mode=client`.
- **Entre servicios de Airflow 3.** Todos comparten `AIRFLOW__API_AUTH__JWT_SECRET`, y el scheduler alcanza la API de ejecución con `AIRFLOW__CORE__EXECUTION_API_SERVER_URL=http://airflow-apiserver:8080/execution/`.
- `LocalExecutor`. Servicios de Airflow 3: `airflow-apiserver`, `airflow-scheduler`, `airflow-dag-processor`, más el job one-shot `airflow-init` (migra la base y crea el usuario administrador).
- Metadatos en `metadata-db` (base `airflow`).
- Programación: el DAG se dispara a mano durante la demostración y, opcionalmente, cada 10 minutos. `max_active_runs = 1` para que dos corridas no escriban Silver a la vez.

## 19. ⚡ Job PySpark #1: Bronze → Silver

Archivo previsto:

```text
pyspark/jobs/bronze_to_silver.py
```

Responsabilidades:

- leer el estado actual de Bronze, incluidos los tombstones (`cdc_op_type = '-D'`);
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

Total propuesto: 14 dimensiones, 2 hechos y 6 bridges.

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

1. `cdc_op_ts` de la fila Bronze, cuando es mayor que cero;
2. `updated_at` de la fila, o `created_at` si no existe `updated_at`;
3. el timestamp lógico de la corrida de Airflow, solo si no hay ninguno de los anteriores.

> ⚠️ **Regla por revisar.** Este orden suponía que `cdc_op_ts` vale `0` en las filas del snapshot inicial, y no es así. La alternativa y su estado son la decisión abierta D-1 del [documento de decisiones y validaciones](DECISIONS-AND-VALIDATIONS.md).

La versión que se cierra recibe como `effective_to` el `effective_from` de la que la reemplaza.

### Generación de surrogate keys

- `nueva SK = max(SK existente) + row_number()`, ordenando las filas nuevas por business key y `effective_from`. Es estable entre reejecuciones.
- No se usa `monotonically_increasing_id()`: sus valores dependen del particionado y cambian de una corrida a otra.
- Las claves `0` y `-1` están reservadas (sección 30); la numeración real empieza en `1`.

## 22. `dim_movie`

Grain: una versión histórica de una película.

Atributos propuestos:

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

Los paths canónicos se decidirán con una regla determinística. La propuesta inicial es conservar el primer valor no nulo observado y versionar posteriores cambios aceptados.

## 24. Dimensiones de catálogo

Las tres son Tipo 1. «Columnas de auditoría» significa `source_updated_at` y `silver_processed_at`.

### Datos de referencia

Varios atributos de estas dimensiones no existen en PostgreSQL (el nombre de un idioma, el sistema al que pertenece un rating, el código ISO de un país). Provienen de archivos CSV versionados en `pyspark/reference/`, mantenidos a mano como parte del laboratorio:

```text
pyspark/reference/languages.csv   language_code -> language_name, is_tmdb_specific
pyspark/reference/statuses.csv    status_code   -> status_description
pyspark/reference/ratings.csv     rating_code   -> rating_system, rating_description
pyspark/reference/countries.csv   source_name   -> standard_country_name, country_code
pyspark/reference/spoken.csv      source_name   -> standard_language_name, language_code
pyspark/reference/enrichment.csv  field_name    -> field_description
```

Cuando un valor fuente no aparece en su archivo de referencia, los atributos derivados quedan en `NULL` y `quality_status = 'unmapped'`. No se inventan equivalencias.

### `dim_original_language`

```text
original_language_sk
language_code
language_name
is_tmdb_specific
columnas de auditoría
```

### `dim_status`

```text
status_sk
status_code
status_description
columnas de auditoría
```

### `dim_rating`

```text
rating_sk
rating_code
rating_system
rating_description
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

- `record_hash` se calcula sobre las medidas, los conteos y las claves foráneas del hecho. Solo se inserta una fila nueva cuando ese hash difiere del último snapshot de la película. Reejecutar el job sin cambios en Bronze no añade filas.
- Un cambio en las relaciones de la película (por ejemplo, un género menos) altera un conteo y por tanto genera snapshot.
- Un cambio solo descriptivo (título, tagline) crea una versión nueva en `dim_movie` pero no un snapshot.
- `movie_sk` apunta a la versión de `dim_movie` vigente en `snapshot_at`. `snapshot_at` es el `source_updated_at` del estado observado, no la hora del job.
- Como Bronze entrega el último estado, entre dos corridas se registra como máximo un snapshot por película (sección 17).

Campos propuestos:

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
is_lead_cast
allocation_weight
effective_from
effective_to
is_current
```

La regla de `is_lead_cast` se definirá únicamente cuando exista un requisito analítico concreto.

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
columnas de auditoría
```

### `dim_enrichment_code`

```text
enrichment_code_sk
code
source_family
source_system
source_date_text
currency_code
currency_year
columnas de auditoría
```

Permitirá interpretar códigos como:

```text
wikipedia_infobox_fx:EUR:2003
```

sin perder el código original.

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

- película sin colección -> `collection_sk = -1`;
- rating desconocido/nulo -> `rating_sk = 0`;
- dimensión aún no disponible -> temporalmente `SK = 0`.

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
budget
revenue
```

no necesitan crear una nueva versión de `dim_movie`; generan un nuevo snapshot cuando cambia el `record_hash` del hecho (sección 27).

### UPDATE de relaciones

Añadir o quitar un género, una keyword o un miembro del reparto:

1. cerrar la fila de bridge que desapareció (`effective_to`, `is_current = false`);
2. insertar la fila de bridge nueva;
3. recalcular `allocation_weight` de las filas vigentes de esa relación;
4. generar snapshot, porque cambia un conteo.

### DELETE

Silver detecta el borrado por el tombstone de Bronze (`cdc_op_type = '-D'`) y no elimina físicamente el historial:

1. cerrar la versión vigente de `dim_movie`;
2. cerrar bridges activos de esa película;
3. insertar un snapshot con `is_deleted = true`;
4. conservar el historial.

Las entidades compartidas (`dim_person`, `dim_genre`, etc.) no se cierran: siguen existiendo en PostgreSQL.

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

Estrategia de escritura: **recarga completa en cada corrida**. Con unos miles de películas, recalcular cada producto y reemplazar la tabla es más simple y más seguro que un MERGE incremental, y deja archivos sin deletes, que es lo que mejor lee DuckDB. Cada reemplazo es un snapshot Iceberg atómico: Superset ve la carga anterior o la nueva, nunca una mezcla.

## 33. 🥇 Capa GOLD

Gold contendrá resultados materializados mediante PySpark. Aunque conceptualmente operen como vistas materializadas del negocio, la implementación local será mediante tablas Iceberg materializadas por el job PySpark.

Productos candidatos:

```text
gold.movie_current_overview
gold.genre_performance
gold.collection_performance
gold.financial_performance
gold.release_trends
gold.cast_analysis
gold.data_quality_coverage
```

Los nombres y KPIs exactos quedarán sujetos al diseño final de dashboards.

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

## 34. 🦆 DuckDB

DuckDB funcionará como SQL/query engine, no como almacenamiento primario ni como Iceberg Catalog.

Responsabilidades:

- conectarse al Iceberg REST Catalog;
- leer las tablas Gold en RustFS;
- exponer una interfaz SQL para consumo;
- servir como backend SQL de Apache Superset.

### Dónde corre

DuckDB es una librería embebida: no escucha en un puerto ni acepta conexiones de otros contenedores. Por eso no existe un «servidor DuckDB» al que Superset se conecte. En este laboratorio corre en dos lugares, con la misma versión y el mismo SQL de inicialización:

| Lugar | Para qué |
|---|---|
| Dentro del contenedor de Superset | Es el camino real de los dashboards, vía `duckdb-engine` |
| Contenedor `duckdb` (perfil `tools` del Compose), basado en `duckdb/duckdb:1.5.6` | Línea de comandos para explorar Gold a mano; no forma parte del flujo |

### Inicialización de cada conexión

DuckDB se usa en memoria; no guarda datos propios. Cada conexión nueva debe cargar las extensiones, declarar el acceso a RustFS, adjuntar el catálogo y crear las vistas de consumo. Ese SQL vive en `duckdb/init/attach_lakehouse.sql`. Es el que pasó las validaciones 6 y 7 del documento de decisiones y validaciones:

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

CREATE OR REPLACE VIEW memory.main.<producto> AS SELECT * FROM lake.gold.<producto>;
```

La última sentencia se repite para cada producto Gold.

Reglas:

- **Tres extensiones, no dos.** `httpfs`, `iceberg` y `avro` se instalan durante el build de la imagen. `iceberg` necesita `avro` y, si no la encuentra, intenta descargarla al cargarse; sin acceso a Internet esa descarga hace fallar todas las consultas. En runtime solo se cargan (`LOAD`), y `autoinstall_known_extensions = false` convierte cualquier extensión ausente en un error visible en lugar de una descarga silenciosa.
- **Directorio de extensiones propio.** Se instalan en `/opt/duckdb_extensions`, la misma ruta en la imagen de Superset y en la del contenedor de línea de comandos, y `extension_directory` apunta ahí. El directorio por defecto queda bajo el `HOME` del usuario, que en Superset es `/app/superset_home`: el volumen montado en esa ruta taparía lo instalado en el build.
- **Credenciales por variables de entorno.** `${AWS_ACCESS_KEY_ID}` y `${AWS_SECRET_ACCESS_KEY}` se sustituyen justo antes de ejecutar el archivo; no hay claves escritas en él.
- **Vistas en la base en memoria, una por producto Gold.** Son obligatorias para los datasets de Superset (sección 35). Se crean en este script porque una base en memoria no conserva nada entre conexiones.
- DuckDB nunca escribe en el lakehouse. Superset rechaza cualquier DDL o DML sobre esta base, que es su comportamiento por defecto.
- Superset solo consulta el namespace `gold`.
- El archivo no lleva `;` dentro de comentarios: quien lo ejecuta descarta las líneas de comentario y parte el resto por `;`.

## 35. 📊 Apache Superset

Superset será la capa de visualización.

No consultará PostgreSQL, Flink ni Bronze directamente.

Ruta de consumo:

```text
Superset -> DuckDB -> Iceberg Gold -> RustFS
```

Gold será la fuente de verdad para las visualizaciones.

### Configuración

- Imagen propia basada en `apache/superset:6.1.0-py312`, con `duckdb` 1.5.6, `duckdb-engine` 0.17.0, `psycopg2-binary` y las extensiones de DuckDB preinstaladas. Se usa la variante `-py312` porque la etiqueta `6.1.0` a secas trae Python 3.10, ya sin soporte.
- La imagen base de la serie 6.1 es mínima: no trae ningún driver, tampoco el de PostgreSQL que Superset necesita para sus propios metadatos. Por eso `psycopg2-binary` forma parte de la imagen. Los paquetes se instalan en el entorno virtual `/app/.venv` con `uv pip install`.
- Superset 6.1.0 limita DuckDB a `duckdb<2,>=1.4.2`. Subir a DuckDB 2.x requiere antes una versión de Superset que lo admita.
- La base de datos se registra con la URI SQLAlchemy `duckdb:///:memory:`.
- Un hook de conexión definido en `superset/config/superset_config.py` ejecuta `duckdb/init/attach_lakehouse.sql` cada vez que SQLAlchemy abre una conexión DuckDB. Sin ese hook, las conexiones nuevas no verían el catálogo. Es un listener del evento `connect` de SQLAlchemy registrado sobre la clase `Engine`, que actúa solo cuando la conexión es de DuckDB. Superset ofrece además `DB_CONNECTION_MUTATOR` para ajustar la URI y los parámetros del motor antes de `create_engine`; no hizo falta.
- **Datasets sobre vistas, en el esquema `main`.** Superset no consigue leer las columnas de una tabla Iceberg adjunta: el inspector de SQLAlchemy devuelve una sola columna sin tipo, y sin columnas no se puede construir un gráfico. Sí las lee de las vistas de la base en memoria que crea el script de inicialización (sección 34). Cada dataset se define como tabla física `main.<producto>`. La alternativa, que también funciona, es un dataset virtual con `SELECT * FROM lake.gold.<producto>`, pero ahí Superset no reconoce el tipo de las columnas `DECIMAL`. SQL Lab puede consultar `lake.gold.<producto>` directamente.
- **Coste por consulta.** Superset abre las conexiones a las bases analíticas sin pool (`NullPool`), de modo que cada consulta crea un DuckDB en memoria nuevo y repite la inicialización. La validación 7 lo midió: la inicialización cuesta unos 40 ms y cada vista añade entre 5 y 9 ms, frente a los 7 ms de la consulta en sí. De extremo a extremo, una consulta por la API de Superset tarda unos 150 ms en secuencia y hasta 440 ms en el percentil 95 con ocho consultas simultáneas y cuatro workers. Es aceptable para el laboratorio; no hace falta el archivo DuckDB de solo lectura que se había previsto como alternativa.
- Cada worker de Superset tiene su propio DuckDB en memoria. No comparten archivo, así que no hay bloqueos entre procesos.
- Metadatos de Superset en `metadata-db` (base `superset`).
- El job one-shot `superset-init` migra la base, crea el usuario administrador y registra la base de datos DuckDB. Los datasets y dashboards se importan desde `superset/config/` cuando Gold ya tiene datos.

## 36. Calidad de datos

La filosofía acordada es:

```text
PostgreSQL  -> conserva semántica fuente
Bronze      -> réplica as-is
Silver      -> limpia, conforma, historiza
Gold        -> sirve métricas y productos analíticos
```

Ejemplos documentados que podrán resolverse en Silver:

- `Guadaloupe` -> posible estandarización a `Guadeloupe`, conservando el valor fuente.
- variantes de nombres de compañías no se fusionarán sin una regla explícita.
- variantes de nombres de personas no se fusionarán automáticamente.
- `cn` se conservará como código TMDB.
- `No Language` seguirá siendo un valor real.
- un nombre de keyword compartido por dos identificadores se conserva como dos keywords distintas.
- `budget` y `revenue` mantienen null como ausencia, nunca cero sintético.
- `user_score` y `vote_average` siguen siendo medidas distintas.
- `plot` puede reflejar una extracción truncada alrededor de 3,000 caracteres; no se inventará contenido faltante.

## 37. Particionamiento Iceberg

No se particionarán inicialmente dimensiones pequeñas.

Para `fact_movie_snapshot`, debido al volumen modesto del laboratorio, se evaluará:

```text
sin partición
```

o, si las ejecuciones generan suficiente historial:

```text
months(snapshot_at)
```

Se evitará una granularidad excesiva que genere demasiados archivos pequeños.

## 38. Consideraciones de mantenimiento Iceberg

Los cambios fila a fila, SCD2 y MERGE pueden generar archivos adicionales. El mantenimiento se reparte por capa:

| Capa | Qué se acumula | Mantenimiento |
|---|---|---|
| 🥉 Bronze | Un commit por checkpoint de Flink y por tabla, con deletes de igualdad | **Desde el inicio**: compactación (`rewrite_data_files`) y expiración de snapshots en la tarea `iceberg_maintenance` |
| 🥈 Silver | Archivos reescritos por cada MERGE | Expiración de snapshots; compactación solo si se observa degradación |
| 🥇 Gold | Un snapshot por recarga completa | Expiración de snapshots, conservando los últimos |

Bronze no puede esperar: con un checkpoint cada 30 s y 20 tablas, en una hora de demostración se generan miles de archivos pequeños, y cada lectura de Spark debe aplicar los deletes acumulados.

Quedan para cuando haga falta demostrar operación del lakehouse:

- limpieza de archivos huérfanos;
- validación del número/tamaño de archivos.

Estas tareas no deben oscurecer el flujo principal.

Procedimientos de Iceberg que usa `iceberg_maintenance`, comprobados en la validación 5 del documento de decisiones y validaciones:

```sql
CALL lake.system.rewrite_data_files(
    table => 'bronze.movie',
    options => map('rewrite-all', 'true', 'remove-dangling-deletes', 'true'));
CALL lake.system.rewrite_position_delete_files(
    table => 'bronze.movie', options => map('rewrite-all', 'true'));
CALL lake.system.expire_snapshots(table => 'bronze.movie', retain_last => 5);
```

- La compactación puede correr con Flink escribiendo: no hubo conflictos de commit ni reinicios del job.
- `rewrite-all` tiene sentido mientras las tablas sean pequeñas, como en este laboratorio; con tablas grandes se sustituye por `delete-file-threshold`.
- Los archivos de deletes que la compactación deja sin uso se borran físicamente al expirar los snapshots que los referencian. `retain_last` decide cuánto historial queda; el valor de arriba es una propuesta.

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
superset-init      migra la base de Superset, crea el administrador y registra DuckDB
```

Opcional, bajo el perfil `tools`:

```text
duckdb             línea de comandos para explorar Gold
```

Todos se declaran en el mismo `docker-compose.yml`. Las credenciales del laboratorio se leen de `.env`; el repositorio versiona `.env.example`. El inventario de cuentas y variables está en la sección 45.

`java-simulator` declara `tty: true` y `stdin_open: true`, para poder abrir su interfaz con `docker compose attach java-simulator`.

### Aislamiento frente a otros proyectos del host

Quien revise el laboratorio puede tener otros entornos Docker en la misma máquina, incluso otro laboratorio de ElastiFlix. Para que no se pisen:

- **Nombre de proyecto explícito.** El archivo empieza con `name: elastiflix-cdc-lakehouse`. Sin él, Compose deriva el nombre del directorio donde se clonó el repositorio, y dos clones o un directorio renombrado producirían proyectos distintos sobre los mismos datos.
- **Sin `container_name`.** Los contenedores toman el nombre que genera Compose (`elastiflix-cdc-lakehouse-postgresql-1`). Un nombre fijo como `elastiflix-postgres` choca con cualquier otro proyecto que use el mismo.
- **Red propia.** Los servicios se hablan por la red por defecto del proyecto y por nombre de servicio (`postgresql`, `rustfs`, `iceberg-rest`); no se usan redes externas ni `network_mode: host`.
- **Puertos del host configurables.** Cada puerto publicado se declara como `127.0.0.1:${VAR:-valor}:puerto`, con la variable en `.env.example`. Si el `5432` u otro ya está ocupado, se cambia en `.env` sin tocar el Compose. Las conexiones entre servicios no dependen de esos puertos.

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

### Presupuesto de memoria

Con 16 GB en el host, cada servicio declara un límite. Reparto orientativo, a ajustar tras la primera ejecución:

| Servicio | Límite |
|---|---:|
| PostgreSQL operacional | 1 GB |
| `metadata-db` | 0.5 GB |
| Flink JobManager + TaskManager | 1 GB + 2 GB |
| Spark master + worker | 0.5 GB + 3 GB |
| Airflow (tres servicios) | 3 GB |
| Superset | 2 GB |
| RustFS + Iceberg REST | 1 GB + 0.5 GB |
| Event Simulator | 0.5 GB |

Total aproximado: 15 GB. Si el host tiene menos, se puede detener el simulador o Superset mientras corre el DAG.

## 40. Orden de dependencias esperado

![Orden de arranque de los servicios de Docker Compose en cuatro carriles: operacional y CDC, almacenamiento y catálogo, batch y orquestación, y consumo](diagrams/compose-startup-order.svg)

> 🔍 **Cómo leerlo:** cada flecha es un `depends_on`. La etiqueta indica la condición: `healthy` espera al healthcheck del servicio y `completó` espera a que un job one-shot termine bien. El camino verde es el crítico: sin bucket no hay catálogo, sin namespaces no se envía el pipeline, y el simulador no emite hasta que el pipeline está corriendo.
>
> Versión interactiva: [`diagrams/compose-startup-order.html`](diagrams/compose-startup-order.html) · Fuente editable: [`diagrams/compose-startup-order.json`](diagrams/compose-startup-order.json).

Reglas:

- Los servicios con estado (`postgresql`, `metadata-db`, `rustfs`, `iceberg-rest`, Flink, Spark) exponen healthcheck.
- Las dependencias sobre jobs one-shot usan `condition: service_completed_successfully`.
- Los jobs one-shot son idempotentes: `docker compose up` puede repetirse sin romper nada.
- El simulador arranca después de `flink-cdc-submit` para que las primeras inserciones se capturen ya en modo streaming y el observador las vea llegar a Bronze.
- Airflow y Superset no esperan a Spark ni a que Gold tenga datos; solo las corridas del DAG y los datasets los necesitan.

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
| Airflow | Orquestación de jobs PySpark |
| Iceberg REST Catalog | Catálogo lakehouse compartido |
| RustFS | Object storage S3-compatible |
| DuckDB | Motor SQL analítico, embebido en Superset |
| Superset | Dashboards y visualización |
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
10. Airflow ejecuta `bronze_to_silver`.
11. Silver crea/actualiza dimensiones SCD2, hechos y bridges.
12. Airflow ejecuta `silver_to_gold`.
13. Gold materializa datasets analíticos.
14. DuckDB consulta Gold.
15. Superset refleja los resultados en dashboards.

## 43. 🚀 Trabajo siguiente

Con esta arquitectura y modelos definidos, la implementación puede avanzar en este orden:

0. ~~Ejecutar las validaciones previas del documento de decisiones y validaciones~~ (hecho: las nueve pasaron).
1. ~~Fijar versiones compatibles~~ (hecho en la sección 3; se confirma con el paso 0).
2. Generar los 20 CSV de `raw_data/` descritos en la sección 8.
3. Implementar DDL PostgreSQL completo con las restricciones de la sección 12, y comprobarlo cargando los CSV con `COPY`.
4. Implementar inicialización de logical replication: roles, publicación y parámetros.
5. Construir Java Event Simulator.
6. Configurar RustFS e Iceberg REST Catalog.
7. Configurar Flink CDC PostgreSQL -> Iceberg Bronze.
8. Crear catálogo y namespaces `bronze`, `silver`, `gold`.
9. Implementar `bronze_to_silver.py`.
10. Implementar SCD Type 2 y bridges.
11. Implementar `silver_to_gold.py`.
12. Configurar Airflow DAG.
13. Configurar DuckDB contra Iceberg.
14. Configurar Superset contra DuckDB.
15. Agregar healthchecks, observabilidad básica y validaciones.
16. Construir dashboards y KPIs finales.
17. Ejecutar una prueba end-to-end con INSERT, UPDATE y DELETE.

## 44. ✅ Criterio de éxito

El laboratorio se considerará exitoso cuando un revisor externo pueda clonar/copiar el proyecto, levantarlo con Docker Compose y observar un cambio real generado por Java recorrer de extremo a extremo:

```text
CSV
 -> Java transaction
 -> PostgreSQL WAL
 -> Flink CDC
 -> Iceberg Bronze
 -> Airflow/PySpark
 -> Silver dimensional/SCD2
 -> Airflow/PySpark
 -> Gold materializado
 -> DuckDB
 -> Apache Superset
```

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
| `postgresql`, `metadata-db` | `postgres` | 999:999 | `postgresql/data`, `metadata-db/data` |
| `flink-jobmanager`, `flink-taskmanager` | `flink` | 9999:9999 | `flink/data` |
| `spark-master`, `spark-worker` | `spark` | 185:185 | Ninguno |
| `airflow-*` | `airflow` | 50000:0 | `airflow/logs` |
| `superset` | `superset` | 1000:1000 | `superset/data` |
| `rustfs` | `rustfs` | 10001:10001 | `rustfs/data` |
| `iceberg-rest` | `iceberg` | 1000:1000 | `iceberg/data` |
| `java-simulator` | `simulator` | 10002:10002 | Ninguno; lee `raw_data/` en solo lectura |

- La imagen de PostgreSQL arranca como `root`, ajusta ella misma la propiedad de su directorio de datos y baja a `postgres`. No necesita preparación.
- El resto no puede cambiar la propiedad de su directorio. En Linux, un directorio recién clonado pertenece al usuario del host y el servicio falla al escribir. En Docker Desktop sobre Windows los directorios montados aparecen escribibles para todos y el problema no se manifiesta.
- **Job `volumes-init`.** Un job one-shot que corre como `root`, antes que los servicios con estado, y asigna a cada directorio de la tabla el UID:GID de su servicio. Reutiliza una imagen ya presente en el laboratorio. Es el job de permisos que las secciones 3.2 y 7 mencionaban sin nombrar.
- `java-simulator` es la única imagen propia sin usuario heredado: su Dockerfile crea el usuario `simulator`.

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
| Clave de acceso de RustFS | RustFS | `rustfs-init`, `iceberg-rest`, Flink, Spark, DuckDB | Lectura y escritura sobre el bucket `warehouse` |

- **Una sola clave de RustFS.** Todos los clientes comparten la misma clave de acceso, que llega a cada contenedor en las variables `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY`. Lo deseable sería una clave de solo lectura para DuckDB, que nunca escribe; no se ha comprobado que RustFS 1.0.6 permita crear claves con permisos distintos.
- **Sin autenticación:** el Iceberg REST Catalog, el master de Spark y el clúster de Flink no piden credenciales. Solo son alcanzables dentro de la red del Compose o, sus interfaces web, desde `127.0.0.1`.
- **Secretos internos**, que no son cuentas pero viven junto a ellas: la `SECRET_KEY` de Superset, y en Airflow el secreto JWT que comparten sus servicios, la clave de la API y la clave Fernet.

### 45.4 Cuentas de acceso para personas

Una cuenta administradora por herramienta. No hay cuentas de solo lectura.

| Herramienta | Dirección | Cuenta | Cómo se crea |
|---|---|---|---|
| Superset | `http://127.0.0.1:8088` | Administrador | `superset-init`, con `superset fab create-admin`. Comprobado en la validación 7 |
| Airflow | `http://127.0.0.1:8080` | Administrador | `airflow-init`. El mecanismo está por validar; ver abajo |
| Consola de RustFS | `http://127.0.0.1:9001` | La clave de acceso de RustFS | No se crea: es la misma clave del servicio. Por validar |
| PostgreSQL operacional | `127.0.0.1:5432` | `postgres` para administrar; `elastiflix_app` para consultar como la aplicación | `postgresql/init/` |
| Flink UI, Spark UI | `http://127.0.0.1:8081`, `:8082` | Ninguna | No tienen inicio de sesión |
| Event Simulator | `docker compose attach java-simulator` | Ninguna | Quien puede ejecutar Docker puede abrir la interfaz |

> ⚠️ **Por validar: el administrador de Airflow.** Airflow 3 trae por defecto un gestor de autenticación simple, que define los usuarios en la configuración y genera sus contraseñas, y no ofrece `airflow users create`. Ese comando pertenece al gestor basado en Flask AppBuilder, que es un proveedor aparte. La validación 8 corrió con el gestor por defecto y sin iniciar sesión en la interfaz. Falta decidir cuál de los dos usa el laboratorio y comprobar el inicio de sesión; figura como validación 12.

### 45.5 Dónde se definen

Todas las credenciales salen de `.env`, que no se versiona. El repositorio incluye `.env.example` con valores de laboratorio, suficientes para levantar el entorno tal cual.

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
- Los valores de `.env.example` son de laboratorio y están pensados para una máquina local con los puertos ligados a `127.0.0.1`. Quien exponga el laboratorio fuera de su máquina debe cambiarlos.
- Las contraseñas de `elastiflix_app` y `elastiflix_cdc` las aplica el script de inicialización de PostgreSQL leyendo las variables; no se versionan dentro del SQL.

## 46. 📚 Decisiones y validaciones

Las decisiones tomadas durante el diseño, las que siguen abiertas, las descartadas, las validaciones ejecutadas con sus resultados y el registro de cambios de cada revisión viven en un documento propio: **[DECISIONS-AND-VALIDATIONS.md](DECISIONS-AND-VALIDATIONS.md)**.

Este documento describe el diseño vigente. Aquel explica por qué es así y qué se probó para sostenerlo.

| Qué | Estado |
|---|---|
| Validaciones previas de la Fase 0 | 9 de 9 superadas |
| Validación de volumen con las 20 tablas y el dataset completo | Superada |
| `MERGE` SCD2 de Silver y mantenimiento a volumen | Superadas |
| Pérdida de checkpoints | Falla; pendiente de la decisión D-2 |
| Validaciones nuevas de esta revisión (10, 11 y 12) | Pendientes |
| Decisiones abiertas | 7 |
