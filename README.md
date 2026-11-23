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

> 🔄 **Implementación y documentación terminadas; falta la etiqueta final.** Las fases F2 a F12 dejaron el laboratorio completo y comprobado de extremo a extremo: desde vacío, un comando lo levanta en menos de dos minutos, y un INSERT, un UPDATE y un DELETE del simulador se siguieron por PostgreSQL, Bronze, Silver y Gold hasta un gráfico de Superset. Se comprobó también desde un clon limpio, siguiendo solo este README. Del [plan de trabajo](planning/PLAN.md) solo queda publicar la etiqueta de Git de la versión final (F12-07).

| Elemento | Estado |
|---|---|
| Documento de diseño ([`lab-design/LAB-DESIGN.md`](lab-design/LAB-DESIGN.md)) | ✅ Revisión 7, con la implementación |
| Diagramas y bocetos ([`lab-design/diagrams/`](lab-design/diagrams/)) | ✅ Quince, generados con Archify: diez técnicos y cinco dibujos sencillos para el wiki |
| Versiones del stack | ✅ Última estable compatible de cada componente; verificadas contra Docker Hub, Maven Central y PyPI |
| Imágenes base en Docker Hub | ✅ Las once existen para `amd64` y `arm64` |
| Estructura de directorios del proyecto | ✅ Creada; con contenido en `raw_data/`, `metadata-db/`, `postgresql/`, `flink/`, `java-simulator/`, `pyspark/`, `airflow/`, `duckdb/` y `superset/` |
| Validaciones de compatibilidad entre componentes | ✅ 12 de 12 superadas. Resultados en el [documento de decisiones y validaciones](lab-design/DECISIONS-AND-VALIDATIONS.md#2-validaciones) |
| Dataset de entrada: 20 CSV en [`raw_data/`](raw_data/), uno por tabla | ✅ Definitivo: 6,899 películas sintéticas, 438,925 filas y 25.7 MB, con su script generador y su [README](raw_data/README.md) |
| Base del proyecto: `.env.example`, `docker-compose.yml`, `volumes-init` y `metadata-db` | ✅ Fase F2 terminada |
| PostgreSQL operacional: esquema `catalog`, cuentas, publicación y servicio en el Compose | ✅ Fase F3 terminada |
| Almacenamiento y catálogo: RustFS, bucket `warehouse`, catálogo Iceberg y sus tres namespaces | ✅ Fase F4 terminada |
| Flink CDC hacia Bronze: imagen, pipeline, envío idempotente y reconstrucción | ✅ Fase F5 terminada |
| Event Simulator: transacciones reales, interfaz de consola y seguimiento de cada cambio hasta Bronze | ✅ Fase F6 terminada |
| Spark y capa Silver: imagen, clúster y el job que mantiene 14 dimensiones, 2 hechos y 6 bridges con historial | ✅ Fase F7 terminada |
| Capa Gold: el job que recarga los siete productos analíticos | ✅ Fase F8 terminada |
| Orquestación con Airflow: imagen, servicios, DAG `elastiflix_medallion`, validaciones y mantenimiento de Iceberg | ✅ Fase F9 terminada |
| DuckDB y Superset: línea de comandos de DuckDB, imagen y servicios de Superset, y la guía para conectar Gold y crear un gráfico, seguida en un navegador | ✅ Fase F10 terminada |
| Integración de extremo a extremo: vuelta a cero, arranque completo, cambios seguidos hasta Superset, reinicio y memoria | ✅ Fase F11 terminada |
| Documentación final y comprobación desde un clon limpio | 🔄 Fase F12: hecho todo salvo la etiqueta de Git de la versión final |

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

Un directorio por servicio, con sus datos dentro:

```text
postgresql-19-cdc-duckdb/
|-- docker-compose.yml
|-- .env.example
|-- README.md, AGENTS.md, CLAUDE.md
|-- lab-design/        diseño, decisiones y validaciones, y los diagramas
|-- wiki/              páginas del wiki, para lectores de negocio, y el script que las publica
|-- planning/          plan de actividades y el script que calcula su avance
|-- raw_data/          dataset de entrada: un CSV por tabla, su generador y su README
|-- java-simulator/    Event Simulator (Java 25): proyecto Maven, pruebas e imagen
|-- postgresql/        DDL, cuentas, publicación y carga de desarrollo
|-- metadata-db/       metadatos de Airflow y Superset
|-- flink/             imagen, configuración y pipeline CDC; checkpoints
|-- iceberg/           datos del Iceberg REST Catalog
|-- pyspark/           imagen de Spark, configuración, datos de referencia y jobs
|-- airflow/           imagen de Airflow y DAG elastiflix_medallion
|-- duckdb/            SQL de inicialización e imagen de la línea de comandos
`-- superset/          imagen y configuración
```

Lo que el laboratorio genera al funcionar va en los subdirectorios `data/` y `logs/` de cada servicio, que Git ignora. La excepción son los datos de RustFS, que viven en un volumen de Docker y no en un directorio. Cada diagrama de `lab-design/diagrams/` tiene tres archivos: la fuente `.json`, la página `.html` y el `.svg`. El detalle de subdirectorios está en la [sección 7 del diseño](lab-design/LAB-DESIGN.md#7--estructura-del-repositorio).

## 7. ✅ Requisitos

- 🐳 Docker Engine con Docker Compose v2 o posterior. En Windows, Docker Desktop con el backend WSL 2.
- CPU x86_64/amd64. El laboratorio se construye y se valida en un solo equipo con Windows 11.
- En un Mac con Apple Silicon no está probado: las imágenes base existen para `arm64`, pero ninguna validación se ha ejecutado ahí. Los puntos a revisar están en la sección 2.2 del [diseño](lab-design/LAB-DESIGN.md).
- Recomendado: **8 CPU, 16 GB RAM y al menos 30 GB libres**.
- Acceso a Internet durante el primer build. El runtime no depende de servicios cloud externos.

## 8. ▶️ Ejecución

### Primer arranque

1. Copia la plantilla de configuración. Sus valores son de laboratorio y sirven tal cual en una máquina local:

   ```bash
   cp .env.example .env
   ```

   En PowerShell: `Copy-Item .env.example .env`.

2. Levanta el laboratorio con un único comando, desde la raíz del repositorio:

   ```bash
   docker compose up -d --build
   ```

Ese comando construye las cinco imágenes propias que usan los servicios, ejecuta los jobs de preparación (permisos de los directorios de datos, bucket, namespaces, envío del pipeline CDC, metadatos de Airflow y Superset) y arranca los 13 servicios. No hay pasos manuales intermedios.

Qué esperar después de lanzarlo:

| Cuándo | Qué ocurre |
|---|---|
| La primera vez | Se descargan las imágenes base y se construyen las cinco propias. Construirlas sin caché tardó 2 min 37 s, con las imágenes base ya descargadas; descargarlas depende de la conexión. Las siguientes veces ya están construidas |
| Al terminar el comando, 1 o 2 minutos con las imágenes construidas | Los 13 servicios están en marcha y el pipeline de Flink CDC, corriendo |
| Un minuto después de lanzarlo | El simulador empieza a insertar películas en PostgreSQL, y Flink las lleva a Bronze en segundos |
| Unos 6 minutos después | Termina la primera corrida del DAG, que arranca sola: Silver y Gold ya tienen datos |
| Cada 10 minutos | El DAG vuelve a correr y Gold se actualiza |

Para ver el estado:

```bash
docker compose ps -a
```

Lo normal es ver 13 servicios en `Up`, 12 de ellos con `(healthy)`, y seis jobs de preparación en `Exited (0)`. El simulador no lleva comprobación de salud. Repetir `docker compose up -d` no duplica nada: los jobs vuelven a ejecutarse y no cambian lo que ya existe.

> ℹ️ Para esperar a que un servicio esté sano, nómbralo: `docker compose up -d --wait metadata-db`. Sin nombre, `--wait` devuelve error en cuanto termina un job de preparación, aunque termine bien.
>
> ℹ️ En Git Bash, antepón `MSYS_NO_PATHCONV=1` a los comandos de este README que llevan rutas de dentro de un contenedor, como `/tmp/…`, `/opt/…` o `/scripts/…`. Sin ello, Git Bash las convierte en rutas de Windows y el comando falla.

### Direcciones y cuentas

Todo se publica solo en `127.0.0.1`. Los usuarios y las contraseñas están en `.env`; los puertos también se cambian ahí.

| Qué | Dirección | Con qué se entra |
|---|---|---|
| Superset | <http://127.0.0.1:8088> | `SUPERSET_ADMIN_USER` y `SUPERSET_ADMIN_PASSWORD` |
| Airflow | <http://127.0.0.1:8080> | `AIRFLOW_ADMIN_USER` y `AIRFLOW_ADMIN_PASSWORD` |
| Flink | <http://127.0.0.1:8081> | No pide cuenta |
| Spark | <http://127.0.0.1:8082> | No pide cuenta |
| Consola de RustFS | <http://127.0.0.1:9001/rustfs/console/> | `RUSTFS_ACCESS_KEY` y `RUSTFS_SECRET_KEY`, en la pestaña de inicio de sesión por clave |
| Catálogo Iceberg (API REST) | <http://127.0.0.1:8181/v1/namespaces> | No pide cuenta |
| PostgreSQL operacional | `127.0.0.1:5432`, base `elastiflix` | `postgres` con `POSTGRES_PASSWORD`, o `elastiflix_app` con `ELASTIFLIX_APP_PASSWORD` |
| Event Simulator | `docker compose attach java-simulator` | No pide cuenta |

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

El simulador lleva 71 pruebas unitarias, que se ejecutan al construir su imagen: si una falla, la imagen no se construye.

### El DAG de Airflow

El DAG `elastiflix_medallion` corre solo cada 10 minutos desde el primer arranque, sin activarlo. Cada corrida tarda entre 4 y 5 minutos y hace esto, en orden:

| Tarea | Qué hace |
|---|---|
| `validate_bronze` | Comprueba que existen las 20 tablas Bronze y que el pipeline de Flink está en marcha |
| `bronze_to_silver` | Actualiza el modelo dimensional de Silver |
| `validate_silver` | Comprueba que Silver es coherente |
| `silver_to_gold` | Recarga los siete productos de Gold |
| `validate_gold` | Comprueba que Gold se puede consultar |
| `iceberg_maintenance` | Compacta Bronze y expira snapshots antiguos; corre siempre |
| `mark_run_failed` | Solo corre si alguna tarea anterior falló, y deja la corrida en error |

Si una validación falla, las tareas siguientes no corren, salvo el mantenimiento, y la corrida queda en error. La causa está en el log de la tarea que falló. El detalle está en la sección 18 del diseño, [Apache Airflow](lab-design/LAB-DESIGN.md#despliegue-de-airflow).

> ℹ️ Los datos de RustFS no están en un directorio del repositorio: viven en un volumen de Docker, `rustfs-data`. La razón está en la [sección 15 del diseño](lab-design/LAB-DESIGN.md#15--rustfs). Solo se borran al [volver a cero](#detener-reanudar-y-volver-a-cero).

### Los jobs de Silver y Gold

Airflow lanza estos dos jobs en cada corrida del DAG. También se pueden lanzar a mano, por ejemplo con el DAG en pausa. El de Silver:

```bash
docker compose run --rm --no-deps spark-worker spark-submit /opt/spark/jobs/bronze_to_silver.py
```

La primera corrida crea las 22 tablas de Silver; las siguientes solo escriben lo que cambió en Bronze, y una corrida sin cambios no escribe nada. Tarda alrededor de un minuto con el dataset completo. En Git Bash hay que anteponer `MSYS_NO_PATHCONV=1` al comando. La interfaz de Spark está en <http://127.0.0.1:8082>. El detalle del job está en la [sección 19 del diseño](lab-design/LAB-DESIGN.md#19--job-pyspark-1-bronze--silver).

Con Silver al día, Gold se recarga con el segundo job:

```bash
docker compose run --rm --no-deps spark-worker spark-submit /opt/spark/jobs/silver_to_gold.py
```

Cada corrida reemplaza completas las siete tablas de Gold, que son las que consulta Superset. Tarda menos de un minuto. Sus columnas están en la [sección 33 del diseño](lab-design/LAB-DESIGN.md#33--capa-gold).

### Superset y DuckDB

Arranca vacío: sin base de datos conectada, sin datasets y sin dashboards. Quien usa el laboratorio conecta Gold y diseña sus gráficos. Son tres pasos, y cada uno está explicado, botón por botón, en la [guía de la sección 35 del diseño](lab-design/LAB-DESIGN.md#guía-conectar-gold-y-crear-una-visualización):

| Paso | Lo esencial |
|---|---|
| 1. Conectar la fuente de datos | Menú **+**, **Data**, **Connect database**; elegir **DuckDB** y pasar a la cadena SQLAlchemy: `duckdb:///:memory:` |
| 2. Registrar un dataset | **Datasets**, **+ Dataset**; esquema `memory.main` y uno de los siete productos de Gold |
| 3. Crear una visualización | Elegir el tipo de gráfico, una columna para el eje y una métrica; **Create chart** y **Save** |

La URI no lleva servidor ni contraseña: DuckDB no es un servicio, corre dentro de Superset. Cada consulta lee Gold tal como lo dejó la última corrida del DAG, así que basta con recargar el dashboard para ver los datos nuevos.

Para consultar el lakehouse a mano hay una línea de comandos de DuckDB, opcional, con el catálogo ya adjunto como `lake`. Su imagen, la sexta del laboratorio, se construye la primera vez que se usa:

```bash
docker compose --profile tools run --rm duckdb
```

Dentro, `SELECT count(*) FROM lake.gold.movie_current_overview;` lee Gold, y también están `lake.silver` y `lake.bronze`. Con `-c "SQL"` al final del comando ejecuta una consulta y termina.

### Carga de desarrollo

Para desarrollar sin esperar al simulador, las tablas se pueden llenar de una vez con la carga de desarrollo, que mete los 20 CSV (438,925 filas). Solo carga sobre una base vacía, así que se levanta solo la cadena que llega hasta el pipeline, sin el simulador (`docker compose up -d flink-cdc-submit`), se lanza la carga y después `docker compose up -d`. En Git Bash este comando necesita `MSYS_NO_PATHCONV=1` delante; sin ello no encuentra el script. El detalle está en la [sección 39 del diseño](lab-design/LAB-DESIGN.md#datos-de-desarrollo):

```bash
docker compose run --rm --no-deps -v ./raw_data:/raw_data:ro -v ./postgresql/scripts:/scripts:ro postgresql bash -c 'PGPASSWORD="$ELASTIFLIX_APP_PASSWORD" psql -h postgresql -U elastiflix_app -d elastiflix -v ON_ERROR_STOP=1 -f /scripts/load_dev_data.sql'
```

### Detener, reanudar y volver a cero

| Qué | Cómo |
|---|---|
| Detener el laboratorio sin perder nada | `docker compose down` |
| Volver a levantarlo | `docker compose up -d`. El pipeline se reanuda desde su último checkpoint, el simulador sigue con la película siguiente y el DAG lanza su corrida a su hora |
| Parar solo el simulador | `docker compose stop java-simulator`; se reanuda con `docker compose start java-simulator` |
| Después de reiniciar el equipo | `docker compose up -d`. Ningún servicio se reinicia solo |

Para volver a cero, es decir, dejar el laboratorio como recién clonado sin perder las imágenes ni el `.env`:

```bash
docker compose down
for d in postgresql/data metadata-db/data flink/data iceberg/data superset/data airflow/logs; do
  find "$d" -mindepth 1 -maxdepth 1 ! -name .gitkeep -exec rm -rf {} +
done
docker volume rm elastiflix-cdc-lakehouse_rustfs-data
docker compose up -d
```

Los seis directorios y el volumen se vacían siempre juntos: vaciar solo algunos deja el catálogo apuntando a archivos que ya no existen. Con ello se pierde también lo creado en Superset y el historial de Airflow. El bucle es de Bash; en Windows se ejecuta desde Git Bash o WSL. En Linux esos archivos pertenecen a los usuarios de los contenedores y borrarlos puede pedir `sudo`; no está probado.

### Si algo no arranca

- **Mira primero el estado y el log.** `docker compose ps -a` dice qué servicio no está sano o qué job no terminó con `Exited (0)`, y `docker compose logs <servicio>` dice por qué.
- **Repite `docker compose up -d`.** Es seguro, y basta cuando un servicio se quedó a medias en el primer arranque.
- **Si el DAG falla en `validate_bronze`**, o el pipeline de Flink no está corriendo (`VBRONZE-002`) o faltan tablas en Bronze (`VBRONZE-001`), que es normal en los primeros segundos y durante una reconstrucción. Para lo primero, `docker compose up -d` reanuda el pipeline desde su último checkpoint.
- **Un puerto ocupado** se cambia en `.env`, en las variables que terminan en `_HOST_PORT`.

### Flujo demostrativo esperado

1. Arranca el stack; PostgreSQL tiene el esquema pero no las películas.
2. Flink CDC queda corriendo y el simulador empieza a insertar.
3. Las filas llegan a PostgreSQL y, segundos después, a Bronze.
4. El simulador genera `UPDATE` y `DELETE`; se reflejan por CDC.
5. Airflow, cada 10 minutos, ejecuta `bronze_to_silver` y luego `silver_to_gold`.
6. DuckDB consulta Gold. En Superset se conecta esa fuente de datos y se crea la primera visualización.

Superset arranca sin dashboards: quien usa el laboratorio diseña los suyos, como se explica en [Superset y DuckDB](#superset-y-duckdb).

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
| [`wiki/`](wiki/Home.md) | El laboratorio explicado sin tecnicismos, para lectores de negocio. Son las páginas del wiki de GitHub: se escriben aquí y se publican con `bash wiki/publish.sh` |
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
