# 🎬 ElastiFlix PostgreSQL CDC Lakehouse Lab

> 🟦 **CDC** · 🟪 **Lakehouse** · 🟩 **Medallion Architecture** · 🟨 **SCD Type 2** · 🟥 **BI**
>
> **Laboratorio local, reproducible y orientado a demostración técnica**, construido completamente con contenedores y un único `docker compose up`.

## 1. Propósito

Este documento consolida las decisiones acordadas para diseñar e implementar un laboratorio reproducible de ingeniería de datos end-to-end para **ElastiFlix**.

El laboratorio simulará actividad transaccional sobre PostgreSQL 19, capturará cambios mediante Apache Flink CDC, persistirá las capas de datos con Apache Iceberg sobre almacenamiento S3-compatible local, construirá un modelo dimensional mediante PySpark, materializará productos analíticos para consumo y los expondrá mediante DuckDB y Apache Superset.

Todo el entorno deberá levantarse desde un único `docker-compose.yml`.

> 📝 **Revisión 3 (2026-11-22):** este documento incorpora las correcciones de la revisión de diseño y una segunda pasada de versiones. Cada componente está en su versión estable más reciente compatible con el resto, y toda imagen base se comprobó en Docker Hub; ver [sección 3](#3--software-stack). El detalle de cada cambio está en la [sección 47](#47--registro-de-cambios-de-la-revisión) y lo que aún debe probarse antes de implementar está en la [sección 46](#46--validaciones-previas-fase-0).

> 🎨 **Leyenda visual:** 🥉 Bronze = réplica operacional; 🥈 Silver = modelo dimensional histórico; 🥇 Gold = serving analítico; 🟪 infraestructura compartida; 🟥 consumo BI.

## 2. ✅ Requisitos

### 2.1 Requisitos funcionales

- 📄 Contar con el archivo fuente `raw_data/elastiflix.csv`, derivado del catálogo ElastiFlix y sin los campos vectoriales.
- ☕ Ejecutar un simulador de eventos en Java 25 que lea el CSV y produzca transacciones `INSERT`, `UPDATE` y `DELETE` reales.
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
- El runtime final no deberá depender de servicios cloud externos. Esto incluye las extensiones de DuckDB (`iceberg`, `httpfs`), que se instalarán durante el build de la imagen y no en la primera consulta.

### 2.3 Requisitos de interoperabilidad

> 🔑 **Regla de oro:** un tipo de dato del modelo operacional solo se utilizará si puede recorrer de forma segura la cadena **PostgreSQL → Flink CDC → Iceberg → PySpark/DuckDB → Superset**.

Se privilegiarán `bigint`, `integer`, `numeric(p,s)`, `text`, `boolean`, `date` y timestamps interoperables. Se evitarán tipos especializados cuando dificulten CDC o consumo analítico.

## 3. 🧰 Software Stack

Las versiones base recomendadas se fijan para que el laboratorio sea reproducible. Cuando dos componentes mantienen una relación de compatibilidad estricta, esa compatibilidad tiene prioridad sobre usar simplemente “la versión más nueva”.

| Componente | Versión base | Imagen o artefacto | Rol |
|---|---:|---|---|
| PostgreSQL | **19.0** | `postgres:19.0` | Base operacional con logical replication; la misma imagen sirve a `metadata-db` |
| Java | **25** (LTS) | `eclipse-temurin:25.0.5.1_2-jre` | Event Simulator |
| Apache Maven | **3.10.0** | `maven:3.10.0-eclipse-temurin-25` | Etapa de build del simulador |
| PostgreSQL JDBC | **42.7.14** | `org.postgresql:postgresql` | Driver del simulador |
| Apache Commons CSV | **1.14.1** | `org.apache.commons:commons-csv` | Lectura del CSV en el simulador |
| Apache Flink | **2.2.1** | `flink:2.2.1-java21` | Runtime de streaming |
| Apache Flink CDC | **3.7.0** | conectores `postgres` e `iceberg`, versión `3.7.0-2.2` | PostgreSQL CDC → Iceberg |
| Apache Iceberg en Flink | **1.10.2** | `iceberg-flink-runtime-2.0`, `iceberg-aws-bundle` | Sink Iceberg del pipeline CDC |
| Apache Spark / PySpark | **4.1.4** | `apache/spark:4.1.4-scala2.13-java21-python3-ubuntu` | Bronze → Silver → Gold |
| Apache Iceberg en Spark | **1.12.0** | `iceberg-spark-runtime-4.1_2.13`, `iceberg-aws-bundle` | Lectura y escritura de Silver y Gold |
| Python | **3.12** | variantes `-python3.12` y `-py312` de las imágenes; se instala en la de Spark | Intérprete común de Airflow, Spark y Superset |
| Apache Airflow | **3.4.0** | `apache/airflow:3.4.0-python3.12` | Orquestación |
| Proveedor Spark de Airflow | **6.3.4** | `apache-airflow-providers-apache-spark` | `SparkSubmitOperator` |
| DuckDB | **1.5.6** | paquete Python `duckdb`; `duckdb/duckdb:1.5.6` para la línea de comandos | SQL/query engine embebido |
| duckdb-engine | **0.17.0** | paquete Python `duckdb-engine` | Dialecto SQLAlchemy para Superset |
| Apache Superset | **6.1.0** | `apache/superset:6.1.0-py312` | BI y dashboards |
| RustFS | **1.0.6** | `rustfs/rustfs:1.0.6` | Object storage S3-compatible |
| Iceberg REST Catalog | **1.10.1** | `apache/iceberg-rest-fixture:1.10.1` | Catálogo compartido |
| Docker Compose | **v2 o posterior** | — | Runtime del laboratorio |

> ℹ️ **Criterio: la versión estable más reciente que el resto del stack admite.** Cada componente se revisó el 2026-11-22 contra Docker Hub, Maven Central y PyPI. Están en su última versión estable publicada: PostgreSQL 19.0, Flink CDC 3.7.0, Airflow 3.4.0 y su proveedor Spark 6.3.4, Superset 6.1.0, RustFS 1.0.6, `duckdb-engine` 0.17.0, JDBC 42.7.14, Commons CSV 1.14.1, Maven 3.10.0 e Iceberg 1.12.0 en Spark. Los que quedan por debajo de la última publicada tienen un motivo de compatibilidad comprobado:
>
> - **Flink 2.2.1 y no 2.3.0.** Flink 2.3.0 ya está en Docker Hub, pero Flink CDC 3.7 solo soporta Flink 1.20 y 2.2: su tabla de compatibilidad lo declara y sus conectores se publican únicamente con los sufijos `-1.20` y `-2.2`. La 2.2.1 es el último parche de la línea 2.2.
> - **Spark 4.1.4 y no 4.3.0.** Iceberg publica un runtime por cada versión menor de Spark. Iceberg 1.12.0 (la más reciente) cubre Spark 3.5, 4.0 y 4.1; en Maven Central no existe `iceberg-spark-runtime-4.2` ni `-4.3`, así que con 4.3.0 los jobs no podrían leer ni escribir Iceberg. La 4.1.4 es el último parche de la línea 4.1.
> - **Iceberg 1.10.2 dentro de Flink y no 1.12.0.** Flink CDC 3.7.0 se compila contra Iceberg 1.10.1 y, en su perfil para Flink 2.x, usa el artefacto `iceberg-flink-runtime-2.0`. La guía oficial de Flink CDC «Real-time PostgreSQL Ingestion into Iceberg» lista ese conjunto para Flink 2.2.1: «Iceberg Flink runtime 1.10.1 (2.0)». Se adopta el último parche de esa misma línea, 1.10.2. No se salta a 1.11.0 (cambio de versión menor respecto a lo que compila el conector) ni al runtime 1.12.0 para Flink 2.2 (otro artefacto). Si el parche diera problemas, el respaldo es 1.10.1; ver [sección 46](#46--validaciones-previas-fase-0).
> - **Dos versiones de Iceberg conviven.** Flink escribe Bronze con 1.10.2 y Spark lee Bronze y escribe Silver y Gold con 1.12.0. Las tablas se crean en formato v2, que ambas versiones y DuckDB leen.
> - **Iceberg REST Catalog 1.10.1.** Es la etiqueta versionada más reciente de `apache/iceberg-rest-fixture` en Docker Hub; las versiones 1.10.2, 1.11.0 y 1.12.0 de Iceberg no publicaron imagen. Solo `latest` es más nueva, y la política de versiones la excluye.
> - **DuckDB 1.5.6 y no 2.0.1.** Superset 6.1.0 declara `duckdb<2,>=1.4.2` en su extra `duckdb`, de modo que DuckDB 2.x queda fuera hasta que Superset lo admita. La 1.5.6 es la última versión de la serie 1.x.
> - **Superset 6.1.0 y no 7.0.0.** De la 7.0.0 solo existen candidatas (`7.0.0rc3`).
> - **Java 25 y no 27.** La 25 es la LTS vigente; 26 y 27 son versiones de soporte corto. Se fija la etiqueta exacta `25.0.5.1_2-jre` en lugar de la móvil `25-jre`.
> - **Python 3.12 en las tres imágenes que lo usan.** PySpark exige la misma versión menor de Python en el driver y en los ejecutores. El driver corre dentro de Airflow (`SparkSubmitOperator` en modo cliente) y los ejecutores dentro de Spark. Las imágenes por defecto no coinciden: `apache/airflow:3.4.0` trae Python 3.13, `apache/spark:4.1.4-…-python3-ubuntu` trae el 3.10 de Ubuntu 22.04 y `apache/superset:6.1.0` trae 3.10, que dejó de tener soporte en octubre de 2026. Se toma 3.12 porque es la versión más alta para la que Airflow y Superset publican imagen (`-python3.12`, `-py312`); la imagen de Spark la instala en su build. Ver «Despliegue de Airflow» en la sección 18.
> - **PostgreSQL 19.0** se publicó el 2026-11-19, después de Flink CDC 3.7.0 (2026-10-10). Su compatibilidad con el conector se comprobó en la validación 1 de la [sección 46](#46--validaciones-previas-fase-0).

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
| JDBC 42.7.14 y Commons CSV 1.14.1 | JAR del simulador | Maven Central |
| PySpark 4.1.4 y proveedor Spark 6.3.4 | Imagen de Airflow | PyPI |
| DuckDB 1.5.6, `duckdb-engine` 0.17.0 y extensiones `httpfs` e `iceberg` | Imagen de Superset | PyPI y repositorio de extensiones de DuckDB |

Los jobs one-shot (`rustfs-init`, `iceberg-init`, `airflow-init`, y el que ajusta permisos) reutilizan alguna de las imágenes anteriores; no añaden imágenes nuevas al laboratorio.

## 4. 🗺️ Diagrama de Arquitectura

![Arquitectura end-to-end del laboratorio ElastiFlix: del CSV a Superset pasando por PostgreSQL, Flink CDC, las tres capas Iceberg, PySpark, Airflow y DuckDB](diagrams/lab-architecture.svg)

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
3. El dataset fuente será un CSV con más de 5,000 registros. La fuente documentada completa contiene 6,899 películas.
4. El CSV no se cargará masivamente con `COPY` como mecanismo principal del laboratorio. Una aplicación Java 25 simulará actividad transaccional insertando registros gradualmente.
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

> 🔍 **Cómo leerlo:** de izquierda a derecha. Las flechas verdes son captura continua de Flink CDC; las grises, cargas batch de PySpark; las punteadas, resolución de claves dentro de Silver. Los bridges también alimentan Gold (pesos N:M), aunque esa flecha no se dibuja.
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
|   `-- elastiflix.csv
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

> ⚠️ **Permisos de los bind mounts:** varias imágenes corren con un usuario no root y necesitan que el directorio del host sea escribible por ese UID. RustFS usa `10001:10001` y Airflow `50000:0`. Un job one-shot ajustará la propiedad de los directorios `data/` antes de arrancar esos servicios.

No se utilizará un directorio raíz genérico `volumes/`.

## 8. 🎞️ Dataset fuente ElastiFlix

La fuente documentada es el índice Elasticsearch `elastiflix-reloaded`, cuyo índice concreto corresponde a `elastiflix-dq-staging-20261113-220031` en la fotografía de datos proporcionada.

Características documentadas:

- 6,899 películas.
- Una película por documento.
- `_id` coincide con `id`.
- `id` corresponde al TMDB movie id y será la clave natural de película.
- Todas las propiedades no vectoriales están presentes en `_source`; algunas pueden contener `null` o arrays vacíos.

### Tipos vectoriales expresamente excluidos

No se modelarán ni propagarán:

```text
plot_1024
plot_512
plot_256
```

La exclusión aplica a:

- CSV operativo del laboratorio, cuando sea posible;
- PostgreSQL;
- Bronze;
- Silver;
- Gold;
- DuckDB;
- Superset.

## 9. ☕ Aplicación Java 25 Event Simulator

La aplicación de consola Java 25 será responsable de simular una aplicación transaccional real.

### Responsabilidades

1. Leer secuencialmente el CSV de `raw_data`.
2. Deserializar los objetos y arrays JSON incluidos dentro de las celdas CSV.
3. Resolver el modelo relacional normalizado.
4. Ejecutar transacciones JDBC reales sobre PostgreSQL.
5. Generar `INSERT` progresivos para crear sensación de eventos en tiempo real.
6. Generar también `UPDATE` y `DELETE` sobre registros existentes.
7. Respetar claves primarias, claves foráneas y tablas puente.
8. Mostrar en consola la actividad que está generando.
9. Permitir comportamiento reproducible mediante una semilla aleatoria.
10. Leer el CSV con un parser que respete comillas y saltos de línea dentro de celdas (por ejemplo Apache Commons CSV); las celdas contienen JSON y no se pueden separar por comas.

### Reglas de carga

- **Nombres repetidos dentro de una película.** `person`, `genre`, `production_company`, `production_country` y `spoken_language` se identifican por nombre exacto. Si un mismo nombre aparece dos veces en la lista de una película, el simulador conserva la primera aparición y descarta las siguientes; de lo contrario la clave primaria de la tabla puente abortaría toda la transacción.
- **Conflictos de `keyword`.** Si un `keyword_id` ya existe con otro nombre, se conserva el primer nombre y la discrepancia se escribe en el log del simulador con nivel `WARN`. No se persiste en el modelo.
- **Tipos de UPDATE.** El simulador alterna tres clases, para ejercitar los tres caminos de Silver: descriptivo (`title`, `tagline`, `overview`, `homepage`), de medidas (`popularity`, `vote_count`, `vote_average`, `user_score`, `budget_usd`, `revenue_usd`) y de relaciones (añadir o quitar un género o una keyword). Todo UPDATE sobre `movie`, `collection` o `keyword` actualiza `updated_at`.
- **DELETE.** Siempre sobre `movie`; las relaciones caen por `ON DELETE CASCADE`.
- **Modo continuo.** Con `SIMULATOR_CONTINUOUS=true`, al agotar el CSV el simulador sigue generando UPDATE y DELETE, y puede volver a insertar desde el CSV una película borrada. Silver trata esa reinserción como una reactivación (sección 31). Con `false`, termina al agotar el CSV.

### Configuración propuesta

```text
SIMULATOR_DELAY_MS
SIMULATOR_INSERT_WEIGHT
SIMULATOR_UPDATE_WEIGHT
SIMULATOR_DELETE_WEIGHT
SIMULATOR_RANDOM_SEED
SIMULATOR_CONTINUOUS
```

Los pesos serán configurables y no forman parte de una restricción del modelo.

### Semántica transaccional

Una fila CSV puede afectar varias tablas. La carga de una película deberá ejecutarse de manera transaccional:

```text
BEGIN
  resolver/crear collection
  resolver/crear catálogos
  insertar movie
  insertar genres/bridges
  insertar keywords/bridges
  insertar cast/bridges
  insertar companies/bridges
  insertar countries/bridges
  insertar spoken languages/bridges
  insertar enrichment
COMMIT
```

Flink verá cambios físicos de múltiples tablas originados por las transacciones normales de PostgreSQL.

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
- PostgreSQL 19.0 se publicó el 2026-11-19. Flink CDC 3.7.0 es anterior e incluye Debezium 1.9.8, que no declara soporte para versiones tan nuevas. El protocolo `pgoutput` es estable entre versiones mayores, y la validación 1 de la sección 46 lo confirmó el 2026-11-22: el conector toma el snapshot, lee el WAL y se recupera de una caída contra PostgreSQL 19.0. PostgreSQL 18 deja de ser necesario como respaldo.

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

> ⚠️ **`NOT NULL` sujetos a perfilado.** `original_title`, `plot`, `release_date` y `popularity` se declaran `NOT NULL` porque la fuente documentada los trae siempre poblados, pero la sección 8 admite nulos en `_source`. Antes de escribir el DDL se perfilará `raw_data/elastiflix.csv`; cualquier columna con algún nulo pasará a `NULL` en lugar de rechazar la película.

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
genre_id   bigint GENERATED ALWAYS AS IDENTITY PK
name       text UNIQUE NOT NULL
```

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

No habrá `UNIQUE(name)` porque existen conflictos id/nombre.

Política: el primer nombre observado para un `keyword_id` será canónico. Las discrepancias posteriores no modifican la fila; el simulador las escribe en su log con nivel `WARN` (sección 9).

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
person_id   bigint GENERATED ALWAYS AS IDENTITY PK
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

Se preservará el orden de facturación. Como `person` se identifica por nombre, un nombre repetido en el reparto de una película se carga una sola vez, con el primer `billing_order` (sección 9).

### 12.11 `production_company`

```text
company_id  bigint GENERATED ALWAYS AS IDENTITY PK
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
country_id  bigint GENERATED ALWAYS AS IDENTITY PK
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
spoken_language_id  bigint GENERATED ALWAYS AS IDENTITY PK
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

El pipeline parte de la guía oficial de Flink CDC «Real-time PostgreSQL Ingestion into Iceberg», que cubre snapshot inicial, INSERT, UPDATE y DELETE con PostgreSQL, `pgoutput` y `REPLICA IDENTITY FULL`. Respecto a esa guía, este laboratorio cambia dos cosas: el catálogo (REST sobre RustFS en lugar de Hadoop sobre disco local) y el bloque `transform`. Ambas pasaron las validaciones 2 y 3 de la sección 46 con el borrador de abajo, sin modificarlo.

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
- **Reinicio.** Al reiniciar, el pipeline retoma desde su último checkpoint. Si se pierden los checkpoints, vuelve a tomar el snapshot inicial, lo cual es seguro porque la escritura es un upsert por PK.

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

Los tres valores se confirmaron en la validación 3 de la sección 46. Las filas del snapshot inicial llegan como `+I`.

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
- **Misma versión menor de Python en Airflow y en Spark.** `SparkSubmitOperator` lanza `spark-submit` en modo cliente contra el clúster standalone, que no admite modo clúster para aplicaciones Python. El driver corre entonces dentro del contenedor de Airflow y los ejecutores dentro de `spark-worker`; si sus versiones menores de Python difieren, PySpark aborta el job. La imagen base de Spark trae Python 3.10 (Ubuntu 22.04) y Airflow no publica imagen con 3.10, por lo que `pyspark/Dockerfile` instala Python 3.12 y fija `PYSPARK_PYTHON` a ese intérprete. Se comprueba en la sección 46.
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

> ⚠️ **Regla por revisar.** Este orden se escribió suponiendo que `cdc_op_ts` vale `0` en las filas del snapshot inicial, de modo que esas filas cayeran en `updated_at`. La validación 1 mostró que no es así: el conector PostgreSQL de Flink CDC 3.7.0 pone ahí el instante en que leyó la fila. Con la regla tal como está, una fila que ya existía cuando arrancó el pipeline recibe como `effective_from` la hora del snapshot y no la de su último cambio. En el laboratorio solo afecta a lo que exista antes de enviar el pipeline (los catálogos sembrados por el DDL), porque las películas se insertan después. Si se quiere la fecha real, la alternativa es invertir los dos primeros puntos para las filas que no son tombstones: `updated_at` cuando la tabla lo tiene y `cdc_op_ts` solo para los DELETE y para las tablas sin `updated_at`.

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

DuckDB se usa en memoria; no guarda datos propios. Cada conexión nueva debe cargar las extensiones, declarar el acceso a RustFS y adjuntar el catálogo. Ese SQL vive en `duckdb/init/attach_lakehouse.sql`. La sintaxis es la documentada por DuckDB para un catálogo REST sin autenticación y un object store S3-compatible; lo que queda por probar es su funcionamiento contra RustFS (sección 46):

```sql
LOAD httpfs;
LOAD iceberg;

CREATE OR REPLACE SECRET rustfs (
    TYPE s3,
    KEY_ID '<clave del laboratorio>',
    SECRET '<secreto del laboratorio>',
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

Reglas:

- Las extensiones `httpfs` e `iceberg` se instalan durante el build de la imagen. En runtime solo se cargan (`LOAD`), sin descargar nada.
- El catálogo se adjunta en solo lectura. DuckDB nunca escribe en el lakehouse.
- Superset solo consulta el namespace `gold`.

DuckDB podrá utilizar vistas SQL sobre las tablas Gold si simplifican el consumo; se crean en el mismo script de inicialización, ya que una base en memoria no las conserva entre conexiones.

## 35. 📊 Apache Superset

Superset será la capa de visualización.

No consultará PostgreSQL, Flink ni Bronze directamente.

Ruta de consumo:

```text
Superset -> DuckDB -> Iceberg Gold -> RustFS
```

Gold será la fuente de verdad para las visualizaciones.

### Configuración

- Imagen propia basada en `apache/superset:6.1.0-py312`, con `duckdb` 1.5.6, `duckdb-engine` 0.17.0 y las extensiones de DuckDB preinstaladas. Se usa la variante `-py312` porque la etiqueta `6.1.0` a secas trae Python 3.10, ya sin soporte.
- Superset 6.1.0 limita DuckDB a `duckdb<2,>=1.4.2`. Subir a DuckDB 2.x requiere antes una versión de Superset que lo admita.
- La base de datos se registra con la URI SQLAlchemy `duckdb:///:memory:`.
- Un hook de conexión definido en `superset/config/superset_config.py` ejecuta `duckdb/init/attach_lakehouse.sql` cada vez que SQLAlchemy abre una conexión DuckDB. Sin ese hook, las conexiones nuevas no verían el catálogo. Superset ofrece además `DB_CONNECTION_MUTATOR` para ajustar la URI y los parámetros del motor antes de `create_engine`.
- **Coste por consulta.** Superset abre las conexiones a las bases analíticas sin pool (`NullPool`) por defecto, de modo que cada consulta crea un DuckDB en memoria nuevo y repite la inicialización. Con pocas tablas Gold debería ser aceptable; se mide en la sección 46 y, si no lo es, la alternativa es un archivo DuckDB de solo lectura generado por un job.
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
- conflictos en keyword id/nombre se manejarán de forma determinística.
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

Procedimientos de Iceberg que usa `iceberg_maintenance`, comprobados en la validación 5 de la sección 46:

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

Todos se declaran en el mismo `docker-compose.yml`. Las credenciales del laboratorio se leen de `.env`; el repositorio versiona `.env.example`.

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
| CSV | Fuente inicial de películas |
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
4. Java comienza a emitir las películas desde el CSV mediante INSERT.
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

## 43. Decisiones expresamente descartadas

No se utilizará:

- BigQuery para este laboratorio local;
- carga exclusivamente batch del CSV hacia PostgreSQL;
- DuckDB como sustituto del Iceberg REST Catalog;
- almacenamiento directo de Iceberg en carpetas manipuladas independientemente por cada motor;
- vectores o embeddings;
- JSON/arrays como sustitutos de la normalización operacional;
- Airflow como controlador evento-a-evento de Flink CDC;
- Superset accediendo directamente a Bronze o PostgreSQL para los dashboards finales;
- DELETE lógico como sustituto general del DELETE físico en el simulador operacional;
- `money` para montos;
- tipos PostgreSQL especializados que dificulten la interoperabilidad del CDC;
- DuckDB como servicio de red al que Superset se conecta;
- Spark 4.2 o 4.3 mientras Iceberg no publique un runtime para esas versiones;
- el Iceberg REST Catalog integrado de RustFS mientras siga en *preview*;
- SCD Type 2 en dimensiones cuyo único atributo es su propia clave o nombre;
- `movie_sk` como ancla de los bridges;
- la base operacional como almacén de metadatos de Airflow o Superset;
- pasos manuales de preparación fuera de Docker Compose.

## 44. 🚀 Trabajo siguiente

Con esta arquitectura y modelos definidos, la implementación puede avanzar en este orden:

0. Ejecutar las validaciones previas de la sección 46. La primera, PostgreSQL 19 con Flink CDC 3.7.0, ya pasó.
1. ~~Fijar versiones compatibles~~ (hecho en la sección 3; se confirma con el paso 0).
2. Preparar el CSV completo de 6,899 películas sin vectores y perfilarlo (nulos, duplicados, longitudes).
3. Implementar DDL PostgreSQL completo, con las restricciones ajustadas al perfilado.
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

## 45. ✅ Criterio de éxito

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

## 46. 🧪 Validaciones previas (Fase 0)

Antes de implementar el laboratorio completo conviene probar, con el mínimo de piezas, las uniones entre componentes que no están garantizadas por documentación. Cada una es una prueba de pocas horas.

| # | Qué se valida | Piezas mínimas | Si falla |
|---:|---|---|---|
| 1 | Flink CDC 3.7.0 lee el WAL de PostgreSQL 19.0 con `pgoutput` (snapshot inicial, INSERT, UPDATE, DELETE) | PostgreSQL, Flink, sink de consola | Usar PostgreSQL 18 |
| 2 | El sink Iceberg de Flink CDC escribe a través de un catálogo REST sobre RustFS, con el runtime Iceberg 1.10.2 | + RustFS, `iceberg-rest` | Volver a Iceberg 1.10.1, la versión de la guía; probar `catalog.properties.type: rest`; como último recurso, otro catálogo REST |
| 3 | `SOFT_DELETE` más `__data_event_type__` y `op_ts` producen tombstones con la fila completa, y qué valores toma `cdc_op_type` | las de la prueba 2 | Rediseñar la detección de DELETE en Silver |
| 4 | El catálogo conserva las tablas tras reiniciar el contenedor `iceberg-rest` | las de la prueba 2 | Cambiar el backend del catálogo |
| 5 | Spark 4.1.4 con Iceberg 1.12.0 lee las tablas Bronze escritas por Flink con Iceberg 1.10.2, incluidos los deletes de igualdad, y puede compactarlas | + Spark | Alinear la versión de Iceberg de Spark con la de Flink |
| 6 | DuckDB 1.5.6 adjunta el catálogo REST y lee una tabla Gold escrita por Spark | + DuckDB | Ajustar el formato de escritura de Gold |
| 7 | Superset 6.1.0 ejecuta el SQL de inicialización en cada conexión DuckDB, consulta Gold con varios workers y el coste de repetir la inicialización por consulta es aceptable | + Superset | Usar un archivo DuckDB de solo lectura generado por un job |
| 8 | Un job PySpark lanzado desde la imagen de Airflow (Python 3.12, modo cliente) corre en los ejecutores de la imagen de Spark con Python 3.12 instalado en el build | Spark, imagen de Airflow | Cambiar la forma de instalar Python en la imagen de Spark; como último recurso, lanzar `spark-submit` dentro del contenedor de Spark |
| 9 | Airflow 3.4.0 y Superset 6.1.0 migran y operan sus metadatos sobre PostgreSQL 19.0 | `metadata-db`, `airflow-init`, `superset-init` | Usar PostgreSQL 18 solo en `metadata-db` |

Estado de verificación de las versiones al 2026-11-22:

| Afirmación | Cómo se verificó |
|---|---|
| Existen, para `linux/amd64` y `linux/arm64`, las diez imágenes de la [sección 3.2](#32-imágenes-en-docker-hub) | `docker manifest inspect` y API de etiquetas de Docker Hub |
| No hay versión estable más nueva de PostgreSQL (19.0), Airflow (3.4.0), Superset (6.1.0; la 7.0.0 está en `rc3`) ni RustFS (1.0.6). `apache/iceberg-rest-fixture` no tiene etiqueta versionada posterior a 1.10.1 | API de etiquetas de Docker Hub |
| Existen Flink 2.3.0 y Spark 4.3.0 en Docker Hub, y no se adoptan | API de etiquetas de Docker Hub |
| Flink CDC 3.7 soporta solo Flink 1.20 y 2.2 | Tabla de compatibilidad de Flink CDC (Context7); sufijos `-1.20` y `-2.2` de los artefactos en Maven Central |
| Existen los conectores Flink CDC `3.7.0-2.2`, `iceberg-flink-runtime-2.0` 1.10.2, `iceberg-spark-runtime-4.1_2.13` 1.12.0 e `iceberg-aws-bundle` en ambas versiones. 3.7.0 es la última versión de Flink CDC y 1.12.0 la última de Iceberg | `maven-metadata.xml` en Maven Central |
| No existe `iceberg-spark-runtime-4.2_2.13` ni `-4.3_2.13`; `iceberg-flink-runtime-2.0` llega hasta 1.11.0 | Listado de `org/apache/iceberg` en Maven Central |
| DuckDB 1.5.6 es la última 1.x (la última publicada es 2.0.1); `duckdb-engine` 0.17.0, el proveedor Spark de Airflow 6.3.4, JDBC 42.7.14 y Commons CSV 1.14.1 son las últimas versiones | PyPI y Maven Central |
| Superset 6.1.0 declara `duckdb<2,>=1.4.2` y `duckdb-engine>=0.17.0` en su extra `duckdb` | Metadatos de `apache-superset` 6.1.0 en PyPI |
| El proveedor Spark 6.3.4 depende de `pyspark-client>=4.0.0`; PySpark 4.1.4 declara soporte para Python 3.10 a 3.14 | Metadatos en PyPI |
| `apache/airflow:3.4.0` trae Python 3.13, `apache/superset:6.1.0` Python 3.10 y la imagen de Spark 4.1.4 se basa en Ubuntu 22.04; las variantes `-python3.12` y `-py312` traen Python 3.12 | Configuración de cada imagen (`docker buildx imagetools inspect`) |
| Las extensiones `httpfs` e `iceberg` de DuckDB 1.5.6 están publicadas para `linux_amd64` | Repositorio de extensiones de DuckDB |
| Flink CDC 3.7.0 se compila contra Iceberg 1.10.1 y usa `iceberg-flink-runtime-2.0` en su perfil Flink 2.x; incluye Debezium 1.9.8 | `pom.xml` del tag `release-3.7.0` |
| Iceberg soporta Spark 3.5, 4.0 y 4.1, y Flink 2.2 desde 1.12.0 | Tabla de soporte multi-motor de Iceberg |
| Opciones `metadata.list`, `SOFT_DELETE`, `route`, `table-id.include-database` y tipos de catálogo del sink | Documentación de Flink CDC 3.7.0 |
| Forma del pipeline PostgreSQL → Iceberg, dependencias para Flink 2.2.1 y creación automática de namespace y tablas | Guía oficial de Flink CDC (Context7; está en la rama principal, no en la documentación publicada de 3.7.0) |
| Sintaxis de `ATTACH ... (TYPE iceberg, ENDPOINT, AUTHORIZATION_TYPE 'none')` y del secreto S3 en DuckDB | Documentación de DuckDB (Context7) |
| Variables `CATALOG_*` del catálogo REST de referencia y uso de RustFS como object store | Quickstart de Spark de Iceberg (Context7) |
| Airflow corre como UID 50000 con GID 0 | Documentación de Airflow (Context7) |
| Superset abre conexiones analíticas con `NullPool` y expone `DB_CONNECTION_MUTATOR` | Código fuente de Superset (Context7) |
| La imagen `postgres` 18+ usa el volumen `/var/lib/postgresql` | README de la imagen oficial |
| RustFS corre como UID 10001 y su catálogo Iceberg integrado es *preview* | README de RustFS |
| La imagen del catálogo REST de referencia usa por defecto un archivo SQLite en `/tmp` del contenedor y declara un healthcheck | Configuración de la imagen `apache/iceberg-rest-fixture:1.10.1` |

Lo que **no** está verificado y por eso figura en la tabla de validaciones: el comportamiento conjunto de las piezas. De las nueve pruebas se han ejecutado las seis primeras; siguen pendientes la 7, la 8 y la 9.

### Resultados

| # | Fecha | Resultado |
|---:|---|---|
| 1 | 2026-11-22 | ✅ Superada |
| 2 | 2026-11-22 | ✅ Superada, con Iceberg 1.10.2 |
| 3 | 2026-11-22 | ✅ Superada |
| 4 | 2026-11-22 | ✅ Superada |
| 5 | 2026-11-22 | ✅ Superada |
| 6 | 2026-11-22 | ✅ Superada |

#### Validación 1: Flink CDC 3.7.0 lee el WAL de PostgreSQL 19.0

Entorno: `postgres:19.0` con `wal_level=logical`, y `flink:2.2.1-java21` con la distribución de Flink CDC `3.7.0-2.2`, el conector `postgres` y el sink `values`, que imprime cada evento. El bloque `source` fue el de la sección 14, sin cambios. Se usaron tres tablas del esquema `catalog` (`movie`, `genre`, `movie_genre`) que cubren todos los tipos de la sección 11, una clave `IDENTITY`, una clave compuesta y un `ON DELETE CASCADE`.

| Qué se comprobó | Resultado |
|---|---|
| Envío del pipeline | Aceptado; el job queda en `RUNNING` y completa checkpoints |
| Rol `elastiflix_cdc` con `REPLICATION` y `SELECT`, sin superusuario | Suficiente |
| Publicación creada por el DDL y `autocreate.mode: disabled` | El conector la reutiliza y crea él mismo el slot `elastiflix_cdc` con `pgoutput` |
| `tables: elastiflix.catalog.\.*` con `table-id.include-database: false` | Captura las tres tablas; el identificador que emite es `catalog.<tabla>` |
| Snapshot inicial | 10 de 10 filas previas, con sus claves primarias |
| Tipos | `bigint`→`BIGINT`, `integer`→`INT`, `text`→`STRING`, `date`→`DATE`, `boolean`→`BOOLEAN`, `numeric(p,s)`→`DECIMAL(p,s)` con la misma precisión y escala, `timestamp(6) with time zone`→`TIMESTAMP_LTZ(6)`; los `NULL` llegan como nulos |
| INSERT | Una transacción sobre tres tablas produce un evento por fila, todos con el mismo `op_ts` |
| UPDATE | Trae la fila anterior y la nueva completas |
| Columna larga (12 800 caracteres, almacenada en TOAST) no modificada por el UPDATE | Llega completa en la fila anterior y en la nueva, gracias a `REPLICA IDENTITY FULL` |
| DELETE con cascada | Un evento por la película y uno por cada relación, cada uno con la fila completa; primero llega el de la película y después los de sus relaciones |
| Reinserción de una clave borrada | Llega como INSERT normal |
| Caída del TaskManager con escrituras durante la caída | El slot se conserva inactivo en PostgreSQL; al volver, el job se restaura del último checkpoint y entrega los cuatro cambios pendientes |
| Pérdidas y duplicados | Ninguno: 24 eventos de datos, todos distintos, y los conteos por tabla coinciden con las filas finales de PostgreSQL |
| Avance del slot | `confirmed_flush_lsn` avanza tras los checkpoints; WAL retenido al final: 896 bytes |

Observaciones que afectan al diseño:

- **`op_ts` no vale `0` en el snapshot.** Las filas del snapshot traen el instante en que el conector las leyó. Se corrigieron las secciones 14 y 17, y la regla de `effective_from` de la sección 21 queda marcada para revisión.
- **Ruido esperado en los logs.** Durante el snapshot PostgreSQL registra `replication slot "elastiflix_cdc_0" does not exist`, una vez por tabla. Todo indica que el conector intenta borrar un slot auxiliar de la fase de snapshot que no llegó a crear; no se investigó más. No afecta al resultado y no debe tratarse como fallo en los healthchecks.

Lo que esta prueba no cubre: las 20 tablas reales, el volumen del dataset completo y el reinicio del JobManager, porque los checkpoints se guardaron en memoria. El sink Iceberg y las columnas `cdc_op_type` y `cdc_op_ts` corresponden a las validaciones 2 y 3.

#### Validaciones 2, 3 y 4: sink Iceberg, tombstones y persistencia del catálogo

Entorno: el de la validación 1 más `rustfs/rustfs:1.0.6`, `apache/iceberg-rest-fixture:1.10.1` y, en la imagen de Flink, el conector `iceberg` `3.7.0-2.2`, `iceberg-flink-runtime-2.0` 1.10.2, `iceberg-aws-bundle` 1.10.2, Hadoop client 3.3.6 y Commons Logging 1.2. El pipeline fue el borrador completo de la sección 14, sin cambios. Los datos se leyeron con `duckdb/duckdb:1.5.6` usando el SQL de la sección 34.

| # | Qué se comprobó | Resultado |
|---:|---|---|
| 2 | Catálogo REST por `catalog-impl`, con `S3FileIO` sobre RustFS | El pipeline arranca a la primera y completa checkpoints sin errores |
| 2 | Runtime Iceberg 1.10.2 con el conector compilado contra 1.10.1 | Funciona; no hizo falta volver a 1.10.1 |
| 2 | Creación automática de namespace y tablas | El conector crea `bronze` y sus tres tablas; en `bronze.movie` se comprobó que queda sin particionar, en formato v2 y con la clave primaria como campo identificador |
| 2 | Bucket creado por `rustfs-init` con `curl --aws-sigv4` | Correcto |
| 2 | Tipos en Iceberg | `DECIMAL` con su precisión y escala, `DATE`, `TIMESTAMP WITH TIME ZONE`; `cdc_op_type` es texto y `cdc_op_ts` es `BIGINT` |
| 2 | Columna de 12 800 caracteres | Llega completa |
| 3 | Valores de `cdc_op_type` | `+I` para el snapshot y los INSERT, `+U` para los UPDATE, `-D` para los DELETE |
| 3 | Tombstone | La fila borrada permanece con `-D`, todos sus valores y el `cdc_op_ts` del borrado; lo mismo cada relación borrada por la cascada |
| 3 | Una fila por clave primaria | Sí: cada UPDATE o DELETE sustituye a la fila anterior |
| 3 | Reinserción de una clave borrada | Sustituye al tombstone por una fila `+I`; las relaciones borradas siguen como `-D` |
| 3 | UPDATE y DELETE de la misma fila dentro de un checkpoint | Queda `-D` con los valores del UPDATE; el `+U` intermedio no se ve, como anticipa la sección 17 |
| 3 | INSERT y DELETE de una clave nueva dentro de un checkpoint | Queda un tombstone de una fila que Bronze nunca mostró viva |
| 4 | Reinicio del contenedor `iceberg-rest` | Tablas y snapshots intactos |
| 4 | Recreación del contenedor con `CATALOG_URI` apuntando a `/catalog` | Tablas y snapshots intactos; SQLite funciona sobre el bind mount en NTFS |
| 4 | Flink tras recrear el catálogo | Sigue publicando snapshots sin reiniciar el job |

Observaciones que afectan al diseño:

- **Las credenciales S3 no estaban en el borrador.** Se resuelven con las variables `AWS_*` en los dos contenedores de Flink (sección 14).
- **El catálogo no es en memoria por defecto**, sino un archivo en `/tmp` del contenedor; la conclusión sobre la persistencia no cambia (sección 16).
- **Bronze acumula deletes desde el primer cambio.** Tras cuatro commits, `bronze.movie` tenía 5 filas (dos de ellas tombstones) repartidas en 4 archivos de datos con 11 registros, más 4 archivos de deletes de igualdad y 1 de deletes posicionales. Confirma que la compactación de la sección 38 hace falta desde el inicio.
- **Silver debe aceptar tombstones sin fila previa.** Una clave insertada y borrada entre dos corridas llega solo como `-D`; `bronze_to_silver.py` no debe suponer que antes hubo una versión vigente.
- **DuckDB ya lee Bronze.** El SQL de la sección 34 adjuntó el catálogo y leyó tablas con deletes de igualdad sin ajustes. Adelanta parte de la validación 6, que sigue pendiente porque se refiere a tablas Gold escritas por Spark.

Lo que estas pruebas no cubren: las 20 tablas, el volumen real, el intervalo de checkpoint de 30 s previsto (se usó 10 s), los checkpoints persistidos en `flink/data/` y la lectura desde Spark, que es la validación 5.

#### Validaciones 5 y 6: Spark sobre Bronze y DuckDB sobre Gold

Entorno: el de las validaciones 2 a 4, con Flink escribiendo Bronze, más un clúster Spark standalone (`apache/spark:4.1.4-scala2.13-java21-python3-ubuntu`, un master y un worker) con `iceberg-spark-runtime-4.1_2.13` 1.12.0 e `iceberg-aws-bundle` 1.12.0 en `/opt/spark/jars`. Los jobs PySpark se lanzaron con `spark-submit` en modo cliente contra el master.

Configuración del catálogo en Spark, la misma para leer Bronze y escribir Gold:

```properties
spark.sql.extensions                        org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions
spark.sql.catalog.lake                      org.apache.iceberg.spark.SparkCatalog
spark.sql.catalog.lake.type                 rest
spark.sql.catalog.lake.uri                  http://iceberg-rest:8181
spark.sql.catalog.lake.warehouse            s3://warehouse/
spark.sql.catalog.lake.io-impl              org.apache.iceberg.aws.s3.S3FileIO
spark.sql.catalog.lake.s3.endpoint          http://rustfs:9000
spark.sql.catalog.lake.s3.path-style-access true
spark.sql.session.timeZone                  UTC
```

Las credenciales S3 llegan, igual que en Flink, por las variables `AWS_*` del master, del worker y del contenedor que lanza el job.

| # | Qué se comprobó | Resultado |
|---:|---|---|
| 5 | Spark 4.1.4 con Iceberg 1.12.0 lee tablas escritas por Flink con Iceberg 1.10.2 | Lee las tres tablas; las filas vivas y los tombstones coinciden con PostgreSQL |
| 5 | Deletes de igualdad | Se aplican: con 8 registros en archivos de datos, `bronze.movie` devuelve sus 4 filas |
| 5 | Esquema visto por Spark | Tipos correctos, `NOT NULL` conservado y `timestamp` con zona UTC |
| 5 | Compactación con `rewrite_data_files`, `rewrite_position_delete_files` y `expire_snapshots` | Termina bien en las tres tablas; `movie_genre` y `genre` quedan en 1 archivo de datos y 0 de deletes |
| 5 | Compactación con Flink escribiendo un UPDATE cada 2 s | Sin conflictos de commit; el job de Flink sigue en `RUNNING`, sin reinicios ni checkpoints fallidos |
| 5 | Contenido tras compactar | Idéntico: misma huella en `movie_genre` y `genre`, y `movie` coincide con PostgreSQL tras los 30 UPDATE concurrentes |
| 5 | Lectura con DuckDB después de la compactación | Mismo resultado que Spark |
| 6 | Spark crea el namespace `gold` y una tabla con `CREATE OR REPLACE TABLE ... USING iceberg`, formato v2 | Correcto |
| 6 | DuckDB 1.5.6 lee la tabla Gold escrita por Spark | Mismas filas y tipos: `DECIMAL(19,2)`, `DATE`, `TIMESTAMP WITH TIME ZONE`, `BIGINT`, texto |
| 6 | Agregaciones en DuckDB sobre Gold | Correctas |
| 6 | Segunda corrida de recarga completa tras un DELETE y un UPDATE en origen | DuckDB ve el contenido nuevo: la película borrada desaparece y la medida cambia |

Observaciones que afectan al diseño:

- **Bronze se ensucia muy rápido.** Recién compactada, `bronze.movie` acumuló en un minuto 9 archivos de datos, 8 de deletes de igualdad y 8 de deletes posicionales para 4 filas, por los 30 UPDATE de la prueba. Con el checkpoint de 30 s previsto serán menos commits, pero la tarea `iceberg_maintenance` debe correr en cada ejecución del DAG, no de forma ocasional.
- **Gold conserva un snapshot por recarga.** `CREATE OR REPLACE TABLE` no borra el historial; tras dos corridas la tabla tenía 2 snapshots. La expiración de snapshots de la sección 38 aplica también a Gold.
- **El SQL de DuckDB de la sección 34 no necesita cambios.** Funcionó igual contra tablas de Flink, tablas compactadas y tablas de Spark.

Lo que estas pruebas no cubren: los jobs corrieron con el Python 3.10 de la imagen de Spark tanto en el driver como en los ejecutores, así que no dicen nada del desajuste con Airflow, que es la validación 8. Tampoco cubren el `MERGE` de Silver, tablas particionadas, lectores concurrentes durante una recarga de Gold ni el volumen real.

## 47. 📝 Registro de cambios de la revisión

### Revisión 3, 2026-11-22

Segunda pasada de versiones con dos criterios: usar la versión estable más reciente que el resto del stack admita, y que toda imagen base exista en Docker Hub.

| Antes | Ahora | Motivo |
|---|---|---|
| Iceberg 1.10.1 en Flink | 1.10.2 | Último parche de la línea contra la que compila Flink CDC 3.7.0 |
| `eclipse-temurin:25-jre` | `eclipse-temurin:25.0.5.1_2-jre` | Etiqueta exacta en lugar de una móvil |
| `apache/airflow:3.4.0` (Python 3.13) | `apache/airflow:3.4.0-python3.12` | Misma versión menor de Python que los ejecutores de Spark |
| `apache/superset:6.1.0` (Python 3.10) | `apache/superset:6.1.0-py312` | Python 3.10 ya no tiene soporte |
| Imagen de Spark con el Python 3.10 de su base | Python 3.12 instalado en `pyspark/Dockerfile` | PySpark exige la misma versión menor en driver y ejecutores |
| Contenedor `duckdb` sin imagen base definida | `duckdb/duckdb:1.5.6` | Imagen oficial en Docker Hub |
| `metadata-db` sin imagen definida | `postgres:19.0` | Misma imagen que la base operacional |
| — | Maven 3.10.0 (`maven:3.10.0-eclipse-temurin-25`), Commons CSV 1.14.1, `pyspark-client` 4.1.4 | Dependencias de build y runtime sin fijar |
| «DuckDB 1.5.6: se conserva la línea acordada» | DuckDB 1.5.6 porque Superset 6.1.0 exige `duckdb<2` | Se sustituye la preferencia por la restricción comprobada |

Se revisaron y **no cambian**, por ser ya la última versión estable o la última compatible: PostgreSQL 19.0, Java 25, Flink 2.2.1, Flink CDC 3.7.0, Spark 4.1.4, Iceberg 1.12.0 en Spark, Airflow 3.4.0, proveedor Spark 6.3.4, DuckDB 1.5.6, `duckdb-engine` 0.17.0, Superset 6.1.0, RustFS 1.0.6, Iceberg REST Catalog 1.10.1 y JDBC 42.7.14. El motivo de cada una está en la sección 3.

Otros cambios de esta revisión:

- Política de versiones ampliada: última estable compatible, sin candidatas, y toda imagen base en Docker Hub para `amd64` y `arm64` (sección 3.1). Tabla de imágenes por servicio (sección 3.2).
- Nombre de proyecto de Compose explícito, sin `container_name` y con puertos del host configurables, para convivir con otros proyectos Docker de la misma máquina (sección 39).
- `.gitattributes` con finales de línea LF (sección 7).
- Dos validaciones nuevas en la Fase 0: Python de Airflow y Spark, y PostgreSQL 19 como base de metadatos (sección 46).

### Revisión 2, 2026-11-22

Cambios respecto a la versión inicial del documento.

#### Versiones

| Antes | Ahora | Motivo |
|---|---|---|
| Spark / PySpark 4.3.0 | 4.1.4 | Iceberg no publica runtime para Spark 4.2 ni 4.3 |
| Iceberg 1.11.0 (Spark) | 1.12.0 | Versión vigente con runtime para Spark 4.1 |
| «Iceberg runtime para Flink 1.10.1» | 1.10.1, artefacto `iceberg-flink-runtime-2.0` | Se precisa el artefacto que usa Flink CDC 3.7.0 |
| DuckDB 1.5.x | 1.5.6 | Versión exacta; 2.0.1 existe y no se adopta |
| RustFS 1.0.x | 1.0.6 | Versión exacta |
| Iceberg REST «compatible» | `apache/iceberg-rest-fixture:1.10.1` | Faltaba definir implementación |
| — | JDBC 42.7.14, `duckdb-engine` 0.17.0, proveedor Spark 6.3.4 | Dependencias de runtime sin fijar |

#### Diseño

| Tema | Cambio | Sección |
|---|---|---|
| Bronze | Añade `cdc_op_type` y `cdc_op_ts`; los DELETE quedan como tombstones. Se documenta que solo se conserva el último estado por clave | 14, 17 |
| Silver | SCD2 solo en `dim_movie`, `dim_collection` y `dim_keyword`; el resto Tipo 1 | 20, 21, 24, 25 |
| Silver | SCD2 por comparación de estado; se retira «eventos tardíos» | 19, 21 |
| Silver | Bridges y `fact_movie_enrichment` anclados a `movie_id` en lugar de `movie_sk` | 28, 29 |
| Silver | Regla de `effective_from`, generación de surrogate keys y reparación de `SK = 0` | 21, 30 |
| Silver | Datos de referencia en `pyspark/reference/` para atributos sin fuente | 24 |
| Silver | Grain de `fact_movie_snapshot` precisado; casos de relaciones y reinserción | 27, 31 |
| Gold | Recarga completa en cada corrida | 32 |
| DuckDB | Embebido en Superset; el contenedor `duckdb` pasa a ser herramienta opcional | 34, 35 |
| Catálogo | Implementación concreta y persistencia en `iceberg/data/` | 16 |
| Flink CDC | Forma del pipeline, checkpointing obligatorio, semántica at-least-once | 14 |
| PostgreSQL | Roles, publicación, `max_slot_wal_keep_size`; `REPLICA IDENTITY FULL` pasa a ser requisito | 10 |
| Compose | Cinco jobs one-shot, `metadata-db`, servicios de Airflow 3, presupuesto de memoria | 39, 40 |
| Airflow | Tareas de validación definidas y tarea `iceberg_maintenance` | 18, 38 |

#### Modelo relacional

| Antes | Ahora |
|---|---|
| `vote_count > 0` | `vote_count >= 0` |
| Índice único parcial en `poster_path` | Eliminado; se conserva el de `imdb_id` |
| `source_position` en `movie_collection` | Eliminado |
| `source_position` sin `NOT NULL` y con `UNIQUE` solo en dos tablas | `NOT NULL` y `UNIQUE(movie_id, source_position)` en las cinco tablas de relación ordenadas |
| Discrepancias de `keyword` «serán registradas» | Se escriben en el log del simulador |
| `NOT NULL` fijos en `movie` | `original_title`, `plot`, `release_date` y `popularity` quedan sujetos al perfilado del CSV |
| `created_at` / `updated_at` sin nulabilidad | `NOT NULL` con valor por defecto |

#### Documento

- Subsecciones del modelo relacional renumeradas de 9.x a 12.x, y las del modelo Silver de 17.x a 20.x.
- Directorio raíz corregido a `postgresql-19-cdc-duckdb/`; se refleja la ubicación real de este documento en `lab-design/`.
- `.env` deja de versionarse; se versiona `.env.example` y se añade `.gitignore`.
- Montaje de PostgreSQL corregido a `/var/lib/postgresql`.
- Los diagramas Mermaid y ASCII se sustituyen por diagramas generados con Archify en `lab-design/diagrams/`.
