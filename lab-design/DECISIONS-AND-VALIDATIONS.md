# 📚 Decisiones y validaciones del laboratorio ElastiFlix

Este documento acompaña a [LAB-DESIGN.md](LAB-DESIGN.md). Aquel describe el diseño vigente; este explica por qué es así, qué quedó descartado, qué sigue abierto y qué se probó para sostenerlo.

Las secciones que se citan por número pertenecen a `LAB-DESIGN.md`.

| Parte | Contenido |
|---|---|
| [1. Decisiones](#1-decisiones) | Vigentes, de versiones, abiertas y descartadas |
| [2. Validaciones](#2-validaciones) | Qué se probó, con qué resultado y qué quedó sin cubrir |
| [3. Registro de cambios](#3-registro-de-cambios) | Qué cambió en cada revisión del diseño |

## 1. Decisiones

### 1.1 Decisiones vigentes

Cada fila es una decisión que el diseño ya refleja. «Origen» indica la revisión o la validación que la produjo.

| # | Decisión | Motivo | Sección del diseño | Origen |
|---:|---|---|---|---|
| 1 | Cada componente usa la versión estable más reciente que el resto admite | Las versiones más nuevas de Flink, Spark y DuckDB no son compatibles entre sí todavía | 3 | Revisión 3 |
| 2 | Toda imagen base existe en Docker Hub, con etiqueta exacta y para `amd64` y `arm64` | Reproducibilidad y un único registro | 3.1, 3.2 | Revisión 3 |
| 3 | Iceberg 1.10.2 en Flink, 1.12.0 en Spark | Último parche de la línea contra la que compila Flink CDC; la convivencia se probó | 3 | Validaciones 2 y 5 |
| 4 | Python 3.12 en Airflow, Spark y Superset; en Spark se instala con `uv` | PySpark exige la misma versión menor en driver y ejecutores | 3, 18 | Validación 8 |
| 5 | PostgreSQL 19.0, sin respaldo a la 18 | Flink CDC 3.7.0 lee su WAL; Airflow y Superset operan sobre ella | 10 | Validaciones 1 y 9 |
| 6 | El dataset son 20 CSV, uno por tabla, con datos sintéticos | El simulador deja de normalizar y de arbitrar datos sucios | 8 | Revisión 4 |
| 7 | Las claves de `genre`, `person`, `production_company`, `production_country` y `spoken_language` las asigna el dataset | Un identificador significa lo mismo en el CSV, en PostgreSQL y en Bronze | 8.4, 12 | Revisión 4 |
| 8 | Finales de línea LF forzados por `.gitattributes` | Los scripts se ejecutan en contenedores Linux | 7 | Revisión 3 |
| 9 | Compose con nombre de proyecto explícito, sin `container_name` y con puertos configurables | Convivir con otros proyectos Docker de la misma máquina | 39 | Revisión 3 |
| 10 | Las credenciales S3 llegan por las variables `AWS_*` | No hay claves en el YAML del pipeline ni en el SQL | 14, 34 | Validación 2 |
| 11 | El catálogo guarda su SQLite en `iceberg/data/` mediante `CATALOG_URI` | El valor por defecto se pierde al recrear el contenedor | 16 | Validación 4 |
| 12 | `rustfs-init` usa la imagen de RustFS con `curl --aws-sigv4` | No hace falta una imagen de cliente S3 | 15 | Validación 2 |
| 13 | DuckDB instala `httpfs`, `iceberg` y `avro` en el build, en un directorio propio | Sin `avro`, `iceberg` falla cuando no hay Internet | 34 | Validación 7 |
| 14 | Los datasets de Superset van sobre vistas de la base en memoria | Superset no lee las columnas de una tabla Iceberg adjunta | 34, 35 | Validación 7 |
| 15 | Superset conserva el `NullPool`; no hace falta un archivo DuckDB de solo lectura | Inicializar DuckDB en cada consulta cuesta decenas de milisegundos | 35 | Validación 7 |
| 16 | La imagen de Superset incluye `psycopg2-binary` | La imagen base de la serie 6.1 no trae ningún driver | 35 | Validación 7 |
| 17 | La imagen de Airflow lleva Java 21, PySpark y los JAR de Iceberg; los jobs se montan también en Airflow | En modo cliente el driver corre en Airflow | 18 | Validación 8 |
| 18 | `iceberg_maintenance` corre en cada ejecución del DAG, y Gold también expira snapshots | Bronze acumula deletes desde el primer cambio; leerlo sin compactar pasó de 1.4 s a más de 180 s | 18, 38 | Validaciones 5 y de volumen |
| 19 | Los checkpoints de Flink se retienen en un directorio compartido por JobManager y TaskManager | El job no sobrevive a un reinicio del JobManager | 14 | Validación de volumen |
| 20 | `flink-cdc-submit` detecta un job en ejecución y reanuda desde el checkpoint retenido | Un segundo envío repite el snapshot completo | 14 | Validación de volumen |
| 21 | El origen de un `MERGE INTO` es una vista temporal o una tabla de trabajo, nunca un DataFrame en caché | Con caché, Spark 4.1.4 falla al planificar | 19 | Validación de Silver |
| 22 | El simulador tiene una interfaz de consola enriquecida | Elegida frente a una interfaz web y a una de escritorio | 9 | Revisión 5 |
| 23 | Desde la interfaz se observa, se controla, se lanzan operaciones a mano y se sigue el cambio hasta Bronze | Permite demostrar un cambio concreto de extremo a extremo | 9.1, 9.3 | Revisión 5 |
| 24 | Una cuenta administradora por herramienta; cuentas técnicas con el mínimo privilegio | Suficiente para un laboratorio local, sin renunciar a un despliegue realista | 45 | Revisión 5 |
| 25 | El job `volumes-init` ajusta la propiedad de los directorios de datos | Casi todos los servicios corren con un usuario que no puede hacerlo por sí mismo | 39, 45.2 | Revisión 5 |

### 1.2 Decisiones de versiones

ℹ️ **Criterio: la versión estable más reciente que el resto del stack admite.** Cada componente se revisó el 2026-11-22 contra Docker Hub, Maven Central y PyPI. Están en su última versión estable publicada: PostgreSQL 19.0, Flink CDC 3.7.0, Airflow 3.4.0 y su proveedor Spark 6.3.4, Superset 6.1.0, RustFS 1.0.6, `duckdb-engine` 0.17.0, JDBC 42.7.14, Commons CSV 1.14.1, Maven 3.10.0 e Iceberg 1.12.0 en Spark. Los que quedan por debajo de la última publicada tienen un motivo de compatibilidad comprobado:

- **Flink 2.2.1 y no 2.3.0.** Flink 2.3.0 ya está en Docker Hub, pero Flink CDC 3.7 solo soporta Flink 1.20 y 2.2: su tabla de compatibilidad lo declara y sus conectores se publican únicamente con los sufijos `-1.20` y `-2.2`. La 2.2.1 es el último parche de la línea 2.2.
- **Spark 4.1.4 y no 4.3.0.** Iceberg publica un runtime por cada versión menor de Spark. Iceberg 1.12.0 (la más reciente) cubre Spark 3.5, 4.0 y 4.1; en Maven Central no existe `iceberg-spark-runtime-4.2` ni `-4.3`, así que con 4.3.0 los jobs no podrían leer ni escribir Iceberg. La 4.1.4 es el último parche de la línea 4.1.
- **Iceberg 1.10.2 dentro de Flink y no 1.12.0.** Flink CDC 3.7.0 se compila contra Iceberg 1.10.1 y, en su perfil para Flink 2.x, usa el artefacto `iceberg-flink-runtime-2.0`. La guía oficial de Flink CDC «Real-time PostgreSQL Ingestion into Iceberg» lista ese conjunto para Flink 2.2.1: «Iceberg Flink runtime 1.10.1 (2.0)». Se adopta el último parche de esa misma línea, 1.10.2. No se salta a 1.11.0 (cambio de versión menor respecto a lo que compila el conector) ni al runtime 1.12.0 para Flink 2.2 (otro artefacto). Si el parche diera problemas, el respaldo es 1.10.1; ver [parte 2](#2-validaciones).
- **Dos versiones de Iceberg conviven.** Flink escribe Bronze con 1.10.2 y Spark lee Bronze y escribe Silver y Gold con 1.12.0. Las tablas se crean en formato v2, que ambas versiones y DuckDB leen.
- **Iceberg REST Catalog 1.10.1.** Es la etiqueta versionada más reciente de `apache/iceberg-rest-fixture` en Docker Hub; las versiones 1.10.2, 1.11.0 y 1.12.0 de Iceberg no publicaron imagen. Solo `latest` es más nueva, y la política de versiones la excluye.
- **DuckDB 1.5.6 y no 2.0.1.** Superset 6.1.0 declara `duckdb<2,>=1.4.2` en su extra `duckdb`, de modo que DuckDB 2.x queda fuera hasta que Superset lo admita. La 1.5.6 es la última versión de la serie 1.x.
- **Superset 6.1.0 y no 7.0.0.** De la 7.0.0 solo existen candidatas (`7.0.0rc3`).
- **Java 25 y no 27.** La 25 es la LTS vigente; 26 y 27 son versiones de soporte corto. Se fija la etiqueta exacta `25.0.5.1_2-jre` en lugar de la móvil `25-jre`.
- **Python 3.12 en las tres imágenes que lo usan.** PySpark exige la misma versión menor de Python en el driver y en los ejecutores. El driver corre dentro de Airflow (`SparkSubmitOperator` en modo cliente) y los ejecutores dentro de Spark. Las imágenes por defecto no coinciden: `apache/airflow:3.4.0` trae Python 3.13, `apache/spark:4.1.4-…-python3-ubuntu` trae el 3.10 de Ubuntu 22.04 y `apache/superset:6.1.0` trae 3.10, que dejó de tener soporte en octubre de 2026. Se toma 3.12 porque es la versión más alta para la que Airflow y Superset publican imagen (`-python3.12`, `-py312`); la imagen de Spark la instala en su build. La validación 8 reprodujo el fallo con las imágenes por defecto y confirmó la solución. Ver «Despliegue de Airflow» en la sección 18.
- **PostgreSQL 19.0** se publicó el 2026-11-19, después de Flink CDC 3.7.0 (2026-10-10). Su compatibilidad con el conector se comprobó en la validación 1 de la [parte 2](#2-validaciones).

### 1.3 Decisiones abiertas

| # | Decisión pendiente | Opciones | Estado |
|---|---|---|---|
| D-1 | Origen de `effective_from` en las dimensiones SCD2 (sección 21) | La regla original usa primero `cdc_op_ts`. La alternativa usa `updated_at` en las filas vivas y `cdc_op_ts` solo en los DELETE y en las tablas sin `updated_at` | La validación de Silver usó la alternativa y funcionó. Falta confirmarla como regla |
| D-2 | Cómo reconciliar Bronze cuando se pierden los checkpoints (sección 14) | Reconstruir Bronze, o reconciliar por fecha | Sin decidir. Recomendación: reconstruir Bronze |
| D-3 | Gestor de autenticación de Airflow (sección 45.4) | El gestor simple que trae Airflow 3, o el basado en Flask AppBuilder | Sin decidir; depende de la validación 12 |
| D-4 | Clave de RustFS de solo lectura para DuckDB (sección 45.3) | Una sola clave para todos, o una segunda con permisos de lectura | Sin comprobar si RustFS 1.0.6 lo permite |
| D-5 | Dataset definitivo | Conservar el actual o sustituirlo por el regenerado | Regeneración en curso: el actual cumple el formato pero tiene medidas que crecen con `movie_id` y solo 847 títulos distintos |
| D-6 | Leyenda del diagrama de linaje | Rotular las flechas grises como «Carga batch PySpark» o como movimiento genérico | Sin decidir; exige regenerar el diagrama |
| D-7 | Diagramas desfasados por la Revisión 5 | Añadir al de arquitectura la consulta del simulador a Bronze, y al de orden de arranque el job `volumes-init` | Pendiente de regenerar con Archify |

**D-1, detalle.** Este orden se escribió suponiendo que `cdc_op_ts` vale `0` en las filas del snapshot inicial, de modo que esas filas cayeran en `updated_at`. La validación 1 mostró que no es así: el conector PostgreSQL de Flink CDC 3.7.0 pone ahí el instante en que leyó la fila. Con la regla tal como está, una fila que ya existía cuando arrancó el pipeline recibe como `effective_from` la hora del snapshot y no la de su último cambio. En el laboratorio solo afecta a lo que exista antes de enviar el pipeline (los catálogos sembrados por el DDL), porque las películas se insertan después. Si se quiere la fecha real, la alternativa es invertir los dos primeros puntos para las filas que no son tombstones: `updated_at` cuando la tabla lo tiene y `cdc_op_ts` solo para los DELETE y para las tablas sin `updated_at`.

**D-2, detalle.** Un envío nuevo del pipeline repite el snapshot, pero no vuelve a leer los DELETE ocurridos mientras no había job: esas filas quedan vivas en Bronze. Las dos formas de corregirlo:

1. **Reconstruir Bronze.** Antes del envío nuevo se eliminan las tablas Bronze, y `bronze_to_silver.py` trata como borrada toda versión vigente cuya clave ya no aparece en Bronze. Es simple, a cambio de perder los tombstones acumulados.
2. **Reconciliar por fecha.** Tras un snapshot repetido, toda fila viva de Bronze con `cdc_op_ts` anterior al inicio de ese snapshot es una fila que ya no existe en origen. Conserva los tombstones, pero exige saber cuándo empezó el snapshot.

### 1.4 Decisiones descartadas

No se utilizará:

- BigQuery para este laboratorio local;
- carga exclusivamente batch de los CSV hacia PostgreSQL;
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

## 2. Validaciones

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
| 10 | Una interfaz Lanterna 3.1.5 funciona dentro del contenedor del simulador a través de `docker compose attach`, también desde una terminal de Windows | Imagen del simulador | Usar JLine, o reducir la interfaz a una salida de texto que se refresca |
| 11 | DuckDB JDBC 1.5.6.0 adjunta el catálogo REST y lee `bronze.movie` desde Java 25, con las extensiones instaladas en el build | Las de la prueba 2 + simulador | Consultar Bronze desde el simulador con el cliente Java de Iceberg, o quitar el seguimiento aguas abajo |
| 12 | Inicio de sesión en la interfaz de Airflow 3.4.0 con un administrador creado por `airflow-init` | Airflow, `metadata-db` | Cambiar de gestor de autenticación (decisión D-3) |

Estado de verificación de las versiones al 2026-11-22:

| Afirmación | Cómo se verificó |
|---|---|
| Existen, para `linux/amd64` y `linux/arm64`, las diez imágenes de la sección 3.2 del diseño | `docker manifest inspect` y API de etiquetas de Docker Hub |
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

Lo que **no** está verificado y por eso figura en la tabla de validaciones: el comportamiento conjunto de las piezas. Las nueve primeras pruebas se han ejecutado y superado. Las pruebas 10, 11 y 12 se añadieron en la Revisión 5 y están pendientes. Abajo están los resultados y lo que cada una dejó sin cubrir.

### Resultados

| # | Fecha | Resultado |
|---:|---|---|
| 1 | 2026-11-22 | ✅ Superada |
| 2 | 2026-11-22 | ✅ Superada, con Iceberg 1.10.2 |
| 3 | 2026-11-22 | ✅ Superada |
| 4 | 2026-11-22 | ✅ Superada |
| 5 | 2026-11-22 | ✅ Superada |
| 6 | 2026-11-22 | ✅ Superada |
| 7 | 2026-11-22 | ✅ Superada, con tres ajustes al diseño |
| 8 | 2026-11-22 | ✅ Superada |
| 9 | 2026-11-22 | ✅ Superada |
| Volumen | 2026-11-22 | ✅ Superada, con dos requisitos nuevos para `flink-cdc-submit` |
| Silver y mantenimiento | 2026-11-22 | ✅ Superadas, con una restricción en el `MERGE` |
| Pérdida de checkpoints | 2026-11-22 | ❌ Bronze queda desalineado; depende de la decisión D-2 |
| 10, 11 y 12 | — | ⏳ Pendientes |

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

#### Validación 7: Superset sobre DuckDB, y la mitad de la 9

Entorno: `rustfs/rustfs:1.0.6`, `apache/iceberg-rest-fixture:1.10.1`, la imagen de Spark de la validación 5 para escribir dos tablas Gold (6,899 y 120 filas), `postgres:19.0` como `metadata-db` y una imagen propia sobre `apache/superset:6.1.0-py312` con `psycopg2-binary`, `duckdb` 1.5.6 y `duckdb-engine` 0.17.0. Superset corrió con cuatro workers de Gunicorn. **La red del Compose se declaró interna, sin salida a Internet**, para que cualquier descarga en runtime fallara a la vista. Las consultas se lanzaron por la API REST de Superset, que es el camino de SQL Lab y de los gráficos.

| Qué se comprobó | Resultado |
|---|---|
| `superset db upgrade`, creación del administrador y `superset init` sobre PostgreSQL 19.0 | Correcto: 344 migraciones aplicadas, sin errores |
| Registro de la base con `superset set-database-uri` y la URI `duckdb:///:memory:` | Correcto; Superset la reconoce como `duckdb` |
| El hook ejecuta el SQL de inicialización en cada conexión | Sí: una inicialización por consulta, lo que confirma el `NullPool` |
| Extensiones precargadas, sin red | **Falló con el diseño original:** `iceberg` intenta descargar `avro`. Con `avro` instalada en el build, correcto |
| Extensiones fuera de `/app/superset_home`, con un volumen montado en esa ruta | Correcto con `extension_directory` |
| SQL Lab sobre `lake.gold.<tabla>`: conteos, agregaciones, tipos y un join entre dos tablas Gold | Correcto |
| DML desde SQL Lab | Rechazado por Superset (`DML_NOT_ALLOWED_ERROR`) |
| Dataset físico sobre una tabla Iceberg adjunta | **No sirve:** Superset detecta una sola columna sin tipo y el gráfico falla |
| Dataset físico sobre una vista de `memory.main` | Correcto: las 12 columnas con su tipo, y la consulta de gráfico funciona |
| Dataset virtual con SQL sobre `lake.gold` | Funciona, pero las columnas `DECIMAL` quedan sin tipo |
| Varios workers | Las consultas se reparten entre los cuatro; cada uno inicializa su propio DuckDB |
| Fiabilidad | 729 de 730 consultas correctas. La fallida fue un error interno de Superset (`'NoneType' object has no attribute 'push'`) que no se reprodujo en cinco rondas más |
| Metadatos de Superset en PostgreSQL 19 tras las pruebas | 759 consultas y 3 datasets registrados, sin errores |

Coste de repetir la inicialización en cada consulta:

| Medida | Sin vistas | 2 vistas | 7 vistas |
|---|---:|---:|---:|
| Inicialización, mediana en secuencia | 42 ms | 60 ms | 79 ms |
| Inicialización, mediana con 8 consultas simultáneas | 102 ms | 115 ms | 162 ms |
| Consulta completa por la API, mediana en secuencia | 137 ms | 158 ms | 170 ms |
| Consulta completa por la API, P95 con 8 simultáneas | 399 ms | 414 ms | 440 ms |
| Consultas por segundo con 8 simultáneas | 24.6 | 22.9 | 21.0 |

La misma consulta sobre una conexión ya inicializada tarda 7 ms: la inicialización pesa más que la consulta, pero el total es aceptable.

Observaciones que afectan al diseño, ya incorporadas en las secciones 34 y 35:

- **Hay que instalar `avro`** además de `httpfs` e `iceberg`. Es el fallo más serio que encontró esta prueba: con Internet pasa inadvertido, porque DuckDB la descarga sola, y sin Internet rompe todas las consultas.
- **Los datasets van sobre vistas**, no sobre las tablas Iceberg. Lo que el diseño daba como opcional pasa a ser necesario.
- **La imagen de Superset necesita `psycopg2-binary`**: la base de la serie 6.1 no trae ningún driver.
- Los datasets se crean con esquema `main`. Con `memory.main` el gráfico funciona, pero una tarea interna de Superset que detecta formatos de fecha falla al citar ese nombre como si fuera un solo identificador.

Lo que esta prueba no cubre: la interfaz web en un navegador, la importación de dashboards, la caché de resultados de Superset y el volumen real de Gold. La opción `READ_ONLY` al adjuntar el catálogo no se probó. La parte de Airflow de la validación 9 se comprobó después, junto con la 8.

#### Validaciones 8 y 9: Python de Airflow y Spark, y metadatos sobre PostgreSQL 19

Entorno: `postgres:19.0` como `metadata-db`, `rustfs/rustfs:1.0.6`, `apache/iceberg-rest-fixture:1.10.1`, un clúster Spark standalone y los tres servicios de Airflow 3 (`api-server`, `scheduler`, `dag-processor`) con `LocalExecutor`. La imagen de Airflow parte de `apache/airflow:3.4.0-python3.12` y añade Java 21, `pyspark` 4.1.4, `pyspark-client` 4.1.4, el proveedor Spark 6.3.4 y los JAR de Iceberg 1.12.0. La de Spark es la de la validación 5 más Python 3.12 instalado con `uv`. La red del Compose fue interna, sin salida a Internet.

Se usaron dos jobs: uno solo con la API de DataFrame y otro con una UDF de Python, una operación sobre RDD y una escritura en Iceberg.

Primero, el fallo que motivó el cambio de diseño, con los ejecutores todavía en el Python 3.10 de la imagen base:

| Caso | Driver | Ejecutores | Resultado |
|---|---|---|---|
| Job solo con DataFrame | 3.12 | 3.10 | Termina bien: no ejecuta Python en los ejecutores |
| Job con UDF de Python | 3.12 | 3.10 | **Falla:** `PYTHON_VERSION_MISMATCH`, «Python in worker has different version: 3.10 than that in driver: 3.12» |
| Job con UDF, pidiendo `python3.12` | 3.12 | 3.10, sin `python3.12` | **Falla:** `Cannot run program "python3.12"` |

Después, con Python 3.12 en los dos lados y el DAG lanzado por el scheduler:

| Qué se comprobó | Resultado |
|---|---|
| Python 3.12 instalado con `uv` en la imagen de Spark | Correcto: 3.12.16, el mismo parche que trae la imagen de Airflow |
| `pyspark` y `pyspark-client` en la misma versión | Correcto: ambos 4.1.4; el paquete importado reporta 4.1.4 |
| Airflow detecta el DAG | Sí, sin errores de importación |
| DAG con dos `SparkSubmitOperator` encadenados, disparado a mano | `success` al primer intento, 29 s en total |
| Modo cliente contra el clúster standalone | El driver corre en `airflow-scheduler` y los ejecutores se conectan de vuelta a él |
| UDF de Python y operación sobre RDD en los ejecutores | Corren con Python 3.12.16 |
| Escritura y lectura de una tabla Iceberg desde el job lanzado por Airflow | Correcto, con los JAR de Iceberg en la imagen de Airflow |
| `airflow db migrate` sobre PostgreSQL 19.0 | Correcto: 73 tablas creadas, sin errores |
| `api-server`, `scheduler` y `dag-processor` sobre PostgreSQL 19.0 | Arrancan y operan; ningún error ni traza en sus logs durante la prueba |
| Sin salida a Internet | Nada intentó descargar en runtime |

La validación 9 queda completa: Superset se comprobó en la validación 7 y Airflow aquí.

Decisión que quedaba abierta y se cierra: Python 3.12 se instala en la imagen de Spark con `uv`. Los detalles de las dos imágenes están en la sección 18.

Lo que estas pruebas no cubren: los jobs reales `bronze_to_silver.py` y `silver_to_gold.py`, la programación periódica del DAG, los reintentos, el `MERGE` de Silver y la arquitectura `arm64`. El DAG se disparó por línea de comandos; no se usó la interfaz web de Airflow.

#### Validación de volumen: las 20 tablas y el dataset completo

Las nueve validaciones usaron tres tablas y unas decenas de filas. Esta repite el camino PostgreSQL 19 → Flink CDC → Bronze con el esquema completo de la sección 12 y el dataset de `raw_data/`, y cubre lo que aquellas dejaron fuera: volumen, checkpoint de 30 s, checkpoints persistidos y reinicio del JobManager.

Entorno: el de las validaciones 2 a 4, con el pipeline de la sección 14 sin cambios, checkpoint cada 30 s, checkpoints en un volumen compartido por JobManager y TaskManager, y los límites de memoria de la sección 39 (PostgreSQL 1 GB, JobManager 1 GB, TaskManager 2 GB, RustFS 1 GB, catálogo 0.5 GB). El dataset se cargó con `COPY`, solo como forma de poblar la base para la prueba. Los conteos de Bronze se leyeron con DuckDB.

| Qué se comprobó | Resultado |
|---|---|
| DDL de las 20 tablas, con sus claves, `CHECK`, cascadas y `REPLICA IDENTITY FULL` | Se aplica sin errores; las 20 tablas entran en la publicación |
| Carga de los 20 CSV | 438,925 filas en 6 s, sin violar ninguna restricción |
| Snapshot inicial de las 20 tablas | Completo en unos 70 s; el conector crea las 20 tablas Bronze |
| Bronze frente a PostgreSQL tras el snapshot | Las 20 tablas coinciden fila por fila en número: 438,925 |
| 2,000 UPDATE, 300 DELETE con cascada y 150 reinserciones, en streaming | Bronze coincide con PostgreSQL en las 20 tablas (431,884 filas vivas) y conserva 7,041 tombstones |
| Marcas de operación | 1,700 películas en `+U`, 150 en `-D` y las reinsertadas en `+I`, como corresponde |
| Memoria bajo carga | TaskManager 1.1 de 2 GB, JobManager 0.58 de 1 GB, PostgreSQL 0.25 de 1 GB, catálogo 0.2 de 0.5 GB, RustFS 0.09 de 1 GB |
| Checkpoints de 30 s | Todos completados, en menos de 1 s cada uno; ninguno fallido |
| Retención de WAL | El slot confirma con un retraso de unos tres checkpoints; llegó a retener 31 MB y bajó a menos de 1 MB |
| Reinicio de JobManager y TaskManager | El job se pierde: el clúster arranca sin jobs. El slot queda inactivo en PostgreSQL |
| Reenvío con `--from-savepoint` al checkpoint retenido | Retoma sin repetir el snapshot: solo cambiaron en Bronze las 196 filas afectadas por los cambios hechos durante la parada, y los conteos vuelven a coincidir |
| Segundo envío con el job ya en ejecución | **Dañino:** Flink lo acepta y un segundo job repite el snapshot completo. Las filas cuadran, pero todas vuelven a `+I` con un `cdc_op_ts` nuevo |
| Lectura de Bronze sin compactar | 1.4 s tras el snapshot, 13 s tras los cambios en streaming y 192 s tras el snapshot duplicado, para contar las 20 tablas |

Consecuencias para el diseño, ya incorporadas en la sección 14:

- **El job no sobrevive a un reinicio del JobManager.** El diseño decía que el pipeline retomaba solo desde su último checkpoint; eso vale para una caída del TaskManager, no para el JobManager.
- **`flink-cdc-submit` necesita lógica**, no solo un envío: detectar un job ya en ejecución y, si no lo hay, reanudar desde el checkpoint retenido.
- **Los checkpoints deben retenerse** y vivir en un directorio compartido por JobManager y TaskManager, propiedad del usuario `flink`.

Otras observaciones:

- El presupuesto de memoria de la sección 39 es holgado para Flink y PostgreSQL con este volumen.
- La degradación de lectura confirma con cifras lo que ya indicaba la validación 5: sin compactación, el coste de leer Bronze crece con cada cambio.
- El DDL usado es un borrador escrito a partir de la sección 12; todavía no está en `postgresql/init/`.

Lo que esta prueba no cubre: el simulador Java (los datos se cargaron con `COPY` y con SQL), la compactación a este volumen, Silver y Gold, y la pérdida de los checkpoints.

#### Validación de Silver, mantenimiento a volumen y pérdida de checkpoints

Entorno: el de la validación de volumen, con las 20 tablas y el dataset completo en Bronze, más un clúster Spark standalone con los límites de la sección 39 y un contenedor que hace de driver en modo cliente.

**`MERGE` SCD2 de `dim_movie`.** Un prototipo de `bronze_to_silver` para esa dimensión, con un único `MERGE INTO` que cierra versiones e inserta las nuevas, claves sustitutas por `max + row_number` y las filas especiales 0 y -1. Para `effective_from` usó la variante propuesta en la sección 21: `updated_at` en las filas vivas y `cdc_op_ts` en los tombstones.

| Corrida | Cambios en origen | Resultado |
|---|---|---|
| 1 | Primera carga | Una versión vigente por película viva; 10 s |
| 2 | 500 UPDATE descriptivos, 500 UPDATE solo de medidas, 100 DELETE | 600 versiones cerradas y 500 nuevas; los UPDATE de medidas no generan versión |
| 3 | Reinserción de 50 películas borradas | 50 versiones nuevas con `version_number` 2; ninguna cerrada |
| 4 | Ninguno | No se ejecuta el `MERGE` ni se crea snapshot: idempotente |

En las cuatro corridas se cumplieron las comprobaciones de `validate_silver`: una sola versión vigente por película, rangos sin solapes, claves sustitutas sin repetir y versiones vigentes iguales al estado de Bronze. Cada corrida tardó unos 10 s.

- **Restricción encontrada:** con un DataFrame en caché como origen, el `MERGE` falla con un error interno de Spark. Con una vista temporal o una tabla de trabajo funciona (sección 19).
- **Lo que no cubre:** el resto de dimensiones, los hechos y los bridges.

**Mantenimiento de las 20 tablas Bronze**, con Flink recibiendo 20 UPDATE cada 3 s:

| Medida | Resultado |
|---|---|
| Duración total | 62 s para las 20 tablas, entre 2 y 4 s por tabla |
| Archivos de datos | De 51 a 20 |
| Archivos de deletes eliminados | 51 de igualdad y 3 posicionales |
| Conflictos con Flink | Ninguno; el job siguió en `RUNNING` sin checkpoints fallidos |
| Bronze frente a PostgreSQL después | Las 20 tablas coinciden |
| Lectura de las 20 tablas con DuckDB | De 9.3 s a 0.2 s |

**Pérdida de los checkpoints.** Con Flink detenido se borraron los checkpoints, se hicieron 30 UPDATE y 3 DELETE en PostgreSQL y se envió el pipeline de nuevo, sin checkpoint.

| Qué se observó | Resultado |
|---|---|
| Envío nuevo con el slot ya existente | Aceptado; el job reutiliza el slot y queda en `RUNNING` |
| Snapshot repetido | Todas las filas existentes vuelven a escribirse, con `cdc_op_ts` nuevo |
| UPDATE hechos durante la parada | Llegan, porque el snapshot lee el estado actual |
| **DELETE hechos durante la parada** | **No llegan:** las 3 películas y 89 filas de sus relaciones siguen vivas en Bronze, sin tombstone |
| Bronze frente a PostgreSQL | **No coinciden:** 434,323 filas vivas frente a 434,231 |
| Silver después | Ninguna versión nueva, porque el contenido no cambió; pero conserva como vigentes las 3 películas borradas |
| Lectura de Bronze | 189 s, por los deletes de igualdad del snapshot repetido |

El diseño afirmaba que repetir el snapshot era seguro porque la escritura es un upsert por clave. Vale para inserciones y actualizaciones, no para borrados. La sección 14 recoge las dos formas de resolverlo; falta elegir una.

## 3. Registro de cambios

### Revisión 5, 2026-11-22

| Tema | Antes | Ahora | Sección del diseño |
|---|---|---|---|
| Simulador | Aplicación de consola que solo informa por texto | Interfaz de consola enriquecida: actividad en vivo, control en caliente, operaciones a mano y seguimiento del cambio hasta Bronze. Requisitos numerados | 9 |
| Simulador | Sin relación con el lakehouse | Consulta Bronze en solo lectura con DuckDB embebido, para el seguimiento | 9.3, 9.8 |
| Stack | Tabla con el rol de cada componente | Añade el propósito de cada componente en el laboratorio; entran Lanterna y DuckDB JDBC | 3 |
| Cuentas | Roles de PostgreSQL mencionados en la sección 10; el resto sin definir | Inventario completo: usuarios de los contenedores, cuentas técnicas, cuentas de acceso y variables de `.env` | 45 |
| Job de permisos | Mencionado sin nombre en dos secciones y ausente de la lista de jobs | `volumes-init`, con los directorios y usuarios que ajusta | 39, 45.2 |
| Documentación | Decisiones, validaciones y registro de cambios dentro del diseño (secciones 43, 46 y 47) | En este documento. El diseño conserva una sección 46 que enlaza aquí | 46 |
| Numeración | «Trabajo siguiente» era la sección 44 y «Criterio de éxito» la 45 | Pasan a ser la 43 y la 44 | 43, 44 |

### Revisión 4, 2026-11-22

El dataset de entrada pasa de un único `raw_data/elastiflix.csv`, con una fila por película y JSON dentro de las celdas, a **un CSV por tabla**.

| Tema | Antes | Ahora | Sección |
|---|---|---|---|
| Dataset | Un CSV derivado del índice original, sin especificar | 20 CSV, uno por tabla, con datos sintéticos que reproducen el perfil del índice original | 8 |
| Contenido de `raw_data/` | `elastiflix.csv` | Los 20 CSV, el script que los genera y su README | 7, 8.1 |
| Simulador | Lee una fila por película, deserializa JSON y resuelve entidades por nombre | Lee archivos ya normalizados; inserta cada fila con la clave del archivo; alta perezosa de catálogos y entidades | 9 |
| Nombres repetidos y conflictos de keyword | Los arbitraba el simulador | Llegan resueltos en el dataset | 8.6, 9, 12 |
| Claves de `genre`, `person`, `production_company`, `production_country`, `spoken_language` | `GENERATED ALWAYS AS IDENTITY` | `bigint` asignado por el dataset, consecutivo desde 1 | 8.4, 12 |
| `NOT NULL` de `movie` | Sujetos a perfilar el CSV | Confirmados por el perfilado del índice original | 12.2 |
| Diagramas de arquitectura y de linaje | Nodo `elastiflix.csv` | Nodo `raw_data/*.csv` | 4, 6 |

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
