# 🗓️ Plan de trabajo del laboratorio ElastiFlix

Este documento es el **único plan de actividades** del laboratorio, de principio a fin. Dice qué hay que hacer y en qué orden. El cómo está en el diseño:

- [LAB-DESIGN.md](../lab-design/LAB-DESIGN.md): el diseño vigente. Cada actividad cita la sección que la explica.
- [DECISIONS-AND-VALIDATIONS.md](../lab-design/DECISIONS-AND-VALIDATIONS.md): las decisiones y las validaciones.

El plan no lleva fechas ni estimaciones de duración: no hay una fecha comprometida. El avance se mide en actividades terminadas.

## 1. Tablero de avance

**Estado global: 🟢 Verde.** No hay bloqueos ni decisiones abiertas.

<!-- tablero:inicio -->
| Fase | Nombre | Actividades | Hechas | Avance | Estado |
|---|---|---:|---:|---:|---|
| F0 | Diseño y validaciones previas | 21 | 20 | 95 % | 🔄 En curso |
| F1 | Dataset de entrada | 9 | 9 | 100 % | ✅ Terminada |
| F2 | Base del proyecto | 7 | 0 | 0 % | ⏳ Pendiente |
| F3 | PostgreSQL operacional | 14 | 0 | 0 % | ⏳ Pendiente |
| F4 | Almacenamiento y catálogo | 6 | 0 | 0 % | ⏳ Pendiente |
| F5 | Flink CDC hacia Bronze | 16 | 0 | 0 % | ⏳ Pendiente |
| F6 | Event Simulator | 36 | 0 | 0 % | ⏳ Pendiente |
| F7 | Spark y capa Silver | 33 | 0 | 0 % | ⏳ Pendiente |
| F8 | Capa Gold | 11 | 0 | 0 % | ⏳ Pendiente |
| F9 | Orquestación con Airflow | 17 | 0 | 0 % | ⏳ Pendiente |
| F10 | DuckDB y Superset | 14 | 0 | 0 % | ⏳ Pendiente |
| F11 | Integración de extremo a extremo | 11 | 0 | 0 % | ⏳ Pendiente |
| F12 | Documentación y cierre | 7 | 0 | 0 % | ⏳ Pendiente |
| | **Global** | **202** | **29** | **14 %** | 🔄 En curso |

Actualizado el 2026-11-22.
<!-- tablero:fin -->

El tablero no se edita a mano: lo recalcula `python planning/update_progress.py` a partir de las casillas marcadas.

Significado del estado global:

- 🟢 **Verde:** no hay bloqueos abiertos.
- 🟡 **Ámbar:** hay bloqueos, pero queda trabajo que no depende de ellos.
- 🔴 **Rojo:** no se puede avanzar en ninguna fase sin resolver un bloqueo.

## 2. Cómo usar este plan

Estas reglas valen igual para una persona que para un agente de programación (Claude Code, Google Antigravity, GitHub Copilot, Cursor o Junie).

1. **Trabaja una actividad a la vez**, en el orden en que aparecen dentro de su fase.
2. **Respeta las dependencias** de la sección 3. Si la fase en curso se bloquea, pasa a una fase que pueda avanzar en paralelo.
3. **Lee antes de hacer.** Abre la referencia que cita la actividad; ahí está el detalle.
4. **No cambies el diseño por tu cuenta.** Si una actividad no se puede cumplir como está escrita, anótalo en la sección 6 y detente.
5. **Comprueba antes de marcar.** Una actividad está hecha cuando cumple la definición de terminado de la sección 4.
6. **Registra el avance en el mismo cambio que el trabajo:**
   - marca la actividad cambiando `[ ]` por `[x]`;
   - ejecuta `python planning/update_progress.py` para recalcular el tablero;
   - añade una línea a la bitácora de la sección 5.
7. **Al cerrar una fase**, comprueba su «Terminada cuando». Si no se cumple, la fase sigue abierta aunque todas sus casillas estén marcadas: añade la actividad que falte.
8. **Si aparece trabajo que el plan no prevé**, añádelo como actividad nueva al final de su fase, con el siguiente número. No renumeres las existentes.

Cada actividad tiene un identificador fijo, como `F3-04`: fase 3, actividad 4. Úsalo en la bitácora y en los mensajes de commit.

## 3. Fases y dependencias

![Dependencias entre las 13 fases del plan, de F0 a F12: en la columna central, de arriba abajo, el camino más largo (F2, F3, F5, F7, F8, F9, F11 y F12); a los lados, las fases F0, F1, F4, F6 y F10 con las fases que dependen de ellas](../lab-design/diagrams/plan-phases.svg)

> Versión interactiva: [`../lab-design/diagrams/plan-phases.html`](../lab-design/diagrams/plan-phases.html) · Fuente editable: [`../lab-design/diagrams/plan-phases.json`](../lab-design/diagrams/plan-phases.json).

Las flechas continuas son dependencias entre fases completas; las verdes, además, forman el camino más largo, que ocupa la columna central. Las punteadas indican que la fase espera a una o dos actividades concretas de F0, no a toda la fase.

| Fase | Depende de | Puede avanzar en paralelo con |
|---|---|---|
| F0 · Diseño y validaciones previas | Nada | F1 y F2 |
| F1 · Dataset de entrada | Nada | F0 y F2 |
| F2 · Base del proyecto | Nada | F0 y F1 |
| F3 · PostgreSQL operacional | F2 | F4 |
| F4 · Almacenamiento y catálogo | F2 | F3 |
| F5 · Flink CDC hacia Bronze | F3, F4 y la actividad F0-12 | F6 |
| F6 · Event Simulator | F3 y las actividades F0-14 y F0-15 | F4, F5, F7 y F8 |
| F7 · Spark y capa Silver | F5 y la actividad F0-13 | F6 |
| F8 · Capa Gold | F7 | F6 |
| F9 · Orquestación con Airflow | F8 y las actividades F0-16 y F0-17 | F10 |
| F10 · DuckDB y Superset | F8 | F9 |
| F11 · Integración de extremo a extremo | F1, F5, F6, F9 y F10 | Ninguna |
| F12 · Documentación y cierre | F11 | Ninguna |

**Camino más largo:** F2 → F3 → F5 → F7 → F8 → F9 → F11 → F12. Un retraso en cualquiera de esas fases retrasa el final. F6 es la fase con más actividades, pero puede hacerse en paralelo desde que termina F3.

**Hitos:**

| Hito | Se alcanza al terminar | Qué se puede enseñar |
|---|---|---|
| H1 · Bronze en vivo | F5 | Un cambio en PostgreSQL aparece en Bronze segundos después |
| H2 · Simulador en marcha | F6 | Transacciones generadas y dirigidas desde la consola |
| H3 · Lakehouse completo | F8 | Silver con historial y los siete productos Gold |
| H4 · Dashboards | F10 | Los productos Gold en Superset |
| H5 · Laboratorio completo | F11 | Un cambio recorre todo el camino con un único `docker compose up` |

### F0 · Diseño y validaciones previas

- **Objetivo:** Tener un diseño completo y probado antes de escribir el laboratorio.
- **Depende de:** Nada
- **Terminada cuando:** La validación 11 está ejecutada.

- [x] **F0-01** Definir los requisitos y el stack del laboratorio. _(diseño §2 y §3)_
- [x] **F0-02** Fijar las versiones y comprobar sus imágenes en Docker Hub. _(diseño §3)_
- [x] **F0-03** Diseñar el modelo relacional de 20 tablas. _(diseño §12)_
- [x] **F0-04** Diseñar las capas Bronze, Silver y Gold. _(diseño §17 a §33)_
- [x] **F0-05** Crear los cinco diagramas del diseño. _(diseño §4, §6, §12, §18 y §40)_
- [x] **F0-06** Crear la estructura de directorios del repositorio. _(diseño §7)_
- [x] **F0-07** Ejecutar las validaciones 1 a 9. _(validaciones, parte 2)_
- [x] **F0-08** Ejecutar la validación de volumen con las 20 tablas. _(validaciones, parte 2)_
- [x] **F0-09** Validar el `MERGE` SCD2 y el mantenimiento a volumen. _(validaciones, parte 2)_
- [x] **F0-10** Definir los requisitos y la interfaz del simulador. _(diseño §9)_
- [x] **F0-11** Definir las cuentas y credenciales. _(diseño §45)_
- [x] **F0-12** Decidir cómo reconciliar Bronze si se pierden los checkpoints. _(decisión 27)_
- [x] **F0-13** Decidir el origen de `effective_from`. _(decisión 26)_
- [x] **F0-14** Ejecutar la validación 10: consola Lanterna dentro del contenedor. _(validaciones, parte 2)_
- [ ] **F0-15** Ejecutar la validación 11: DuckDB JDBC lee Bronze desde Java 25. _(validaciones, parte 2)_
- [x] **F0-16** Ejecutar la validación 12: inicio de sesión del administrador de Airflow. _(validaciones, parte 2)_
- [x] **F0-17** Decidir el gestor de autenticación de Airflow. _(decisión 30)_
- [x] **F0-18** Decidir si DuckDB usa una clave de RustFS de solo lectura. _(decisión 28)_
- [x] **F0-19** Corregir la leyenda del diagrama de linaje. _(decisión 29)_
- [x] **F0-20** Regenerar los diagramas de arquitectura y de orden de arranque. _(diseño §4 y §40)_
- [x] **F0-21** Comprobar la reconstrucción de Bronze tras perder los checkpoints. _(diseño §38)_

### F1 · Dataset de entrada

- **Objetivo:** Tener en `raw_data/` los 20 CSV definitivos, validados.
- **Depende de:** Nada
- **Terminada cuando:** El dataset definitivo está en `raw_data/`, validado y cargado una vez en PostgreSQL 19 sin errores.

- [x] **F1-01** Perfilar el catálogo original. _(diseño §8.1)_
- [x] **F1-02** Generar la primera versión de los 20 CSV sintéticos. _(diseño §8)_
- [x] **F1-03** Validar la primera versión de forma independiente. _(validaciones, parte 2)_
- [x] **F1-04** Recibir el dataset regenerado. _(decisión 31)_
- [x] **F1-05** Validar el formato y las claves del dataset regenerado. _(diseño §8.2 a §8.4)_
- [x] **F1-06** Validar el perfil y las correlaciones del dataset regenerado. _(validaciones, parte 2)_
- [x] **F1-07** Comprobar que el generador produce archivos idénticos en dos ejecuciones. _(diseño §8.1)_
- [x] **F1-08** Cargar el dataset regenerado en PostgreSQL 19 con `COPY`, como prueba. _(diseño §8.3)_
- [x] **F1-09** Confirmar cuál es el dataset definitivo. _(decisión 31)_

### F2 · Base del proyecto

- **Objetivo:** Tener el esqueleto del Compose y la configuración común que usarán todos los servicios.
- **Depende de:** Nada
- **Terminada cuando:** `docker compose config` valida sin errores y `volumes-init` termina con código 0.

- [ ] **F2-01** Crear `.env.example` con todas las variables. _(diseño §45.5)_
- [ ] **F2-02** Crear el `.env` local a partir de `.env.example`. _(diseño §45.5)_
- [ ] **F2-03** Crear `docker-compose.yml` con el nombre del proyecto. _(diseño §39)_
- [ ] **F2-04** Declarar los puertos del host como variables ligadas a `127.0.0.1`. _(diseño §39)_
- [ ] **F2-05** Añadir el job `volumes-init`. _(diseño §45.2)_
- [ ] **F2-06** Comprobar que `docker compose config` valida sin errores. _(diseño §39)_
- [ ] **F2-07** Comprobar que `volumes-init` deja cada directorio con su usuario. _(diseño §45.2)_

### F3 · PostgreSQL operacional

- **Objetivo:** Tener la base `elastiflix` con su esquema `catalog` lista para capturar cambios.
- **Depende de:** F2
- **Terminada cuando:** El servicio arranca sano, crea las 20 tablas y la publicación, y los 20 CSV cargan con `COPY` sin errores.

- [ ] **F3-01** Escribir el DDL de los 4 catálogos. _(diseño §12)_
- [ ] **F3-02** Escribir el DDL de las 7 entidades compartidas. _(diseño §12)_
- [ ] **F3-03** Escribir el DDL de `movie` y `movie_collection`. _(diseño §12)_
- [ ] **F3-04** Escribir el DDL de las 6 tablas de relación y de `movie_enrichment`. _(diseño §12)_
- [ ] **F3-05** Revisar el DDL con las observaciones de la validación del dataset. _(validaciones, parte 2)_
- [ ] **F3-06** Crear el rol `elastiflix_app`. _(diseño §45.3)_
- [ ] **F3-07** Crear el rol `elastiflix_cdc`. _(diseño §45.3)_
- [ ] **F3-08** Tomar las contraseñas de los roles desde variables de entorno. _(diseño §45.5)_
- [ ] **F3-09** Configurar `REPLICA IDENTITY FULL` en las 20 tablas. _(diseño §10)_
- [ ] **F3-10** Crear la publicación `elastiflix_pub`. _(diseño §10)_
- [ ] **F3-11** Añadir el servicio `postgresql` al Compose con sus parámetros de replicación. _(diseño §10)_
- [ ] **F3-12** Añadir el healthcheck de `postgresql`. _(diseño §40)_
- [ ] **F3-13** Comprobar que el esquema se crea al arrancar. _(diseño §10)_
- [ ] **F3-14** Comprobar que los 20 CSV cargan sin errores con `COPY`. _(diseño §8.3)_

### F4 · Almacenamiento y catálogo

- **Objetivo:** Tener RustFS y el Iceberg REST Catalog listos para recibir tablas.
- **Depende de:** F2
- **Terminada cuando:** El bucket `warehouse` y los namespaces `bronze`, `silver` y `gold` existen y sobreviven a recrear los contenedores.

- [ ] **F4-01** Añadir el servicio `rustfs` con su healthcheck. _(diseño §15)_
- [ ] **F4-02** Añadir el job `rustfs-init` que crea el bucket `warehouse`. _(diseño §15)_
- [ ] **F4-03** Añadir el servicio `iceberg-rest` con su catálogo guardado en `iceberg/data/`. _(diseño §16)_
- [ ] **F4-04** Añadir el job `iceberg-init` que crea los tres namespaces. _(diseño §16)_
- [ ] **F4-05** Comprobar que el bucket y los namespaces existen. _(diseño §15 y §16)_
- [ ] **F4-06** Comprobar que los namespaces siguen ahí tras recrear `iceberg-rest`. _(diseño §16)_

### F5 · Flink CDC hacia Bronze

- **Objetivo:** Replicar en Bronze, de forma continua, cada cambio de PostgreSQL.
- **Depende de:** F3, F4 y la actividad F0-12
- **Terminada cuando:** Las 20 tablas están en Bronze, reflejan INSERT, UPDATE y DELETE, y el pipeline se reanuda solo tras un reinicio.

- [ ] **F5-01** Escribir `flink/Dockerfile` con Flink CDC y sus JAR. _(diseño §14)_
- [ ] **F5-02** Escribir la configuración de Flink: checkpoint de 30 s y checkpoints retenidos. _(diseño §14)_
- [ ] **F5-03** Escribir el pipeline `flink/jobs/postgres-to-bronze.yaml`. _(diseño §14)_
- [ ] **F5-04** Añadir `flink-jobmanager` al Compose. _(diseño §39)_
- [ ] **F5-05** Añadir `flink-taskmanager` al Compose. _(diseño §39)_
- [ ] **F5-06** Escribir el script de envío: no enviar si el job ya está en ejecución. _(diseño §14)_
- [ ] **F5-07** Escribir el script de envío: reanudar desde el último checkpoint. _(diseño §14)_
- [ ] **F5-08** Escribir el script de envío: detenerse con error si no hay checkpoint y Bronze ya tiene tablas. _(diseño §14)_
- [ ] **F5-09** Añadir el job `flink-cdc-submit` al Compose. _(diseño §39)_
- [ ] **F5-10** Comprobar que las 20 tablas llegan a Bronze. _(diseño §17)_
- [ ] **F5-11** Comprobar un INSERT en Bronze. _(diseño §17)_
- [ ] **F5-12** Comprobar un UPDATE en Bronze. _(diseño §17)_
- [ ] **F5-13** Comprobar un DELETE en Bronze. _(diseño §17)_
- [ ] **F5-14** Comprobar que repetir `docker compose up` no crea un segundo job. _(diseño §14)_
- [ ] **F5-15** Comprobar que el pipeline se reanuda tras reiniciar el JobManager. _(diseño §14)_
- [ ] **F5-16** Escribir el script que elimina las tablas Bronze para reconstruirlas. _(diseño §38)_

### F6 · Event Simulator

- **Objetivo:** Tener el simulador Java 25 generando transacciones reales, con su interfaz de consola.
- **Depende de:** F3 y las actividades F0-14 y F0-15
- **Terminada cuando:** El simulador cumple los requisitos RF-01 a RF-12 y su interfaz se abre con `docker compose attach`.

- [ ] **F6-01** Crear el proyecto Maven con sus dependencias. _(diseño §9.8)_
- [ ] **F6-02** Leer la configuración desde variables de entorno. _(diseño §9.6)_
- [ ] **F6-03** Cargar los 20 CSV en memoria. _(RF-01)_
- [ ] **F6-04** Conectar con PostgreSQL usando `elastiflix_app`. _(diseño §45.3)_
- [ ] **F6-05** Dar de alta una película en una sola transacción. _(RF-02)_
- [ ] **F6-06** Insertar catálogos y entidades la primera vez que se necesitan. _(diseño §9.5)_
- [ ] **F6-07** Implementar el UPDATE descriptivo. _(RF-03)_
- [ ] **F6-08** Implementar el UPDATE de medidas. _(RF-03)_
- [ ] **F6-09** Implementar el UPDATE de relaciones. _(RF-03)_
- [ ] **F6-10** Implementar el DELETE de una película. _(RF-03)_
- [ ] **F6-11** Implementar la reinserción de una película borrada. _(RF-03)_
- [ ] **F6-12** Elegir la siguiente operación según los pesos y la semilla. _(RF-04 y RF-05)_
- [ ] **F6-13** Implementar el modo continuo. _(diseño §9.5)_
- [ ] **F6-14** Ante un dato inconsistente: revertir, registrar y continuar. _(RF-12)_
- [ ] **F6-15** Escribir una línea de log por transacción. _(RF-11)_
- [ ] **F6-16** Implementar el modo de líneas, que es como arranca el simulador. _(RF-10 y diseño §9.4)_
- [ ] **F6-17** Dibujar la cabecera de la pantalla. _(diseño §9.3)_
- [ ] **F6-18** Dibujar la zona de avance. _(diseño §9.3)_
- [ ] **F6-19** Dibujar la zona de operaciones. _(diseño §9.3)_
- [ ] **F6-20** Dibujar la lista de últimas transacciones. _(diseño §9.3)_
- [ ] **F6-21** Dibujar la zona de detalle. _(diseño §9.3)_
- [ ] **F6-33** Abrir la interfaz con la primera tecla y cerrarla con `Q`. _(diseño §9.4)_
- [ ] **F6-34** Atrapar `Ctrl-C` para que no detenga el simulador. _(diseño §9.8)_
- [ ] **F6-35** Repintar la pantalla completa cada 2 segundos y al cambiar de tamaño. _(diseño §9.8)_
- [ ] **F6-22** Implementar pausar y reanudar. _(RF-07)_
- [ ] **F6-23** Implementar el cambio de velocidad. _(RF-07)_
- [ ] **F6-24** Implementar el diálogo de pesos. _(RF-07)_
- [ ] **F6-25** Implementar el diálogo de operación manual. _(RF-08)_
- [ ] **F6-26** Implementar el seguimiento del cambio hasta Bronze. _(RF-09)_
- [ ] **F6-27** Escribir pruebas unitarias de la lectura de CSV. _(diseño §9.1)_
- [ ] **F6-28** Escribir pruebas unitarias de la selección de operaciones. _(RF-05)_
- [ ] **F6-29** Escribir `java-simulator/Dockerfile` con el usuario `simulator`. _(diseño §45.2)_
- [ ] **F6-30** Añadir `java-simulator` al Compose, después de `flink-cdc-submit`. _(diseño §40)_
- [ ] **F6-36** Limitar el tamaño del log del servicio en el Compose. _(diseño §9.8)_
- [ ] **F6-31** Comprobar la interfaz con `docker compose attach java-simulator`. _(diseño §9.2)_
- [ ] **F6-32** Comprobar que la misma semilla repite la misma secuencia. _(RF-05)_

### F7 · Spark y capa Silver

- **Objetivo:** Construir el modelo dimensional con historial a partir de Bronze.
- **Depende de:** F5 y la actividad F0-13
- **Terminada cuando:** Silver tiene sus 14 dimensiones, 2 hechos y 6 bridges, y una corrida sin cambios no escribe nada.

- [ ] **F7-01** Escribir `pyspark/Dockerfile` con Iceberg y Python 3.12. _(diseño §18)_
- [ ] **F7-02** Escribir `pyspark/conf/spark-defaults.conf`. _(validaciones, parte 2)_
- [ ] **F7-03** Añadir `spark-master` al Compose. _(diseño §39)_
- [ ] **F7-04** Añadir `spark-worker` al Compose. _(diseño §39)_
- [ ] **F7-05** Crear los seis archivos de referencia en `pyspark/reference/`. _(diseño §24)_
- [ ] **F7-06** Crear el esqueleto de `bronze_to_silver.py`. _(diseño §19)_
- [ ] **F7-07** Cargar `dim_date`. _(diseño §26)_
- [ ] **F7-08** Crear las filas especiales 0 y -1 de cada dimensión. _(diseño §30)_
- [ ] **F7-09** Cargar `dim_original_language`. _(diseño §24)_
- [ ] **F7-10** Cargar `dim_status`. _(diseño §24)_
- [ ] **F7-11** Cargar `dim_rating`. _(diseño §24)_
- [ ] **F7-12** Cargar `dim_genre`. _(diseño §25)_
- [ ] **F7-13** Cargar `dim_person`. _(diseño §25)_
- [ ] **F7-14** Cargar `dim_production_company`. _(diseño §25)_
- [ ] **F7-15** Cargar `dim_production_country`. _(diseño §25)_
- [ ] **F7-16** Cargar `dim_spoken_language`. _(diseño §25)_
- [ ] **F7-17** Cargar `dim_enrichment_field`. _(diseño §29)_
- [ ] **F7-18** Cargar `dim_enrichment_code`. _(diseño §29)_
- [ ] **F7-19** Cargar `dim_movie` con SCD2. _(diseño §21 y §22)_
- [ ] **F7-20** Cargar `dim_collection` con SCD2. _(diseño §23)_
- [ ] **F7-21** Cargar `dim_keyword` con SCD2. _(diseño §25)_
- [ ] **F7-22** Cargar `bridge_movie_genre`. _(diseño §28)_
- [ ] **F7-23** Cargar `bridge_movie_keyword`. _(diseño §28)_
- [ ] **F7-24** Cargar `bridge_movie_cast`. _(diseño §28)_
- [ ] **F7-25** Cargar `bridge_movie_production_company`. _(diseño §28)_
- [ ] **F7-26** Cargar `bridge_movie_production_country`. _(diseño §28)_
- [ ] **F7-27** Cargar `bridge_movie_spoken_language`. _(diseño §28)_
- [ ] **F7-28** Cargar `fact_movie_snapshot`. _(diseño §27)_
- [ ] **F7-29** Cargar `fact_movie_enrichment`. _(diseño §29)_
- [ ] **F7-30** Reparar las referencias que quedaron con clave 0. _(diseño §19 y §30)_
- [ ] **F7-31** Comprobar que una segunda corrida sin cambios no escribe nada. _(diseño §19)_
- [ ] **F7-32** Comprobar un INSERT, un UPDATE, un DELETE y una reinserción en Silver. _(diseño §31)_
- [ ] **F7-33** Cerrar las versiones vigentes cuya clave ya no aparece en Bronze. _(diseño §19 y §38)_

### F8 · Capa Gold

- **Objetivo:** Materializar los productos analíticos que consultará Superset.
- **Depende de:** F7
- **Terminada cuando:** Los siete productos Gold existen, se reemplazan completos en cada corrida y DuckDB los lee.

- [ ] **F8-01** Definir las columnas y los indicadores de los siete productos. _(diseño §33)_
- [ ] **F8-02** Crear el esqueleto de `silver_to_gold.py`. _(diseño §32)_
- [ ] **F8-03** Crear `gold.movie_current_overview`. _(diseño §33)_
- [ ] **F8-04** Crear `gold.genre_performance`. _(diseño §33)_
- [ ] **F8-05** Crear `gold.collection_performance`. _(diseño §33)_
- [ ] **F8-06** Crear `gold.financial_performance`. _(diseño §33)_
- [ ] **F8-07** Crear `gold.release_trends`. _(diseño §33)_
- [ ] **F8-08** Crear `gold.cast_analysis`. _(diseño §33)_
- [ ] **F8-09** Crear `gold.data_quality_coverage`. _(diseño §33)_
- [ ] **F8-10** Comprobar que cada corrida reemplaza las tablas completas. _(diseño §32)_
- [ ] **F8-11** Comprobar que DuckDB lee los siete productos. _(diseño §34)_

### F9 · Orquestación con Airflow

- **Objetivo:** Ejecutar y validar los jobs de Silver y Gold desde un DAG.
- **Depende de:** F8 y las actividades F0-16 y F0-17
- **Terminada cuando:** Una corrida del DAG `elastiflix_medallion` termina en `success` y deja Silver y Gold actualizados.

- [ ] **F9-01** Añadir `metadata-db` con las bases `airflow` y `superset`. _(diseño §45.3)_
- [ ] **F9-02** Escribir `airflow/Dockerfile` con Java, PySpark y los JAR de Iceberg. _(diseño §18)_
- [ ] **F9-03** Añadir el job `airflow-init`. _(diseño §39)_
- [ ] **F9-04** Añadir `airflow-apiserver` al Compose. _(diseño §18)_
- [ ] **F9-05** Añadir `airflow-scheduler` al Compose. _(diseño §18)_
- [ ] **F9-06** Añadir `airflow-dag-processor` al Compose. _(diseño §18)_
- [ ] **F9-07** Crear el administrador de Airflow con `airflow users create`. _(diseño §45.4)_
- [ ] **F9-08** Escribir el job de mantenimiento de Iceberg. _(diseño §38)_
- [ ] **F9-09** Crear el DAG `elastiflix_medallion`. _(diseño §18)_
- [ ] **F9-10** Añadir la tarea `validate_bronze`. _(diseño §18)_
- [ ] **F9-11** Añadir la tarea `bronze_to_silver`. _(diseño §18)_
- [ ] **F9-12** Añadir la tarea `validate_silver`. _(diseño §18)_
- [ ] **F9-13** Añadir la tarea `silver_to_gold`. _(diseño §18)_
- [ ] **F9-14** Añadir la tarea `validate_gold`. _(diseño §18)_
- [ ] **F9-15** Añadir la tarea `iceberg_maintenance`. _(diseño §38)_
- [ ] **F9-16** Comprobar una corrida completa del DAG. _(diseño §18)_
- [ ] **F9-17** Comprobar que una validación fallida detiene el DAG. _(diseño §18)_

### F10 · DuckDB y Superset

- **Objetivo:** Mostrar los productos Gold en dashboards.
- **Depende de:** F8
- **Terminada cuando:** Los dashboards se crean solos al levantar el laboratorio y muestran datos de Gold.

- [ ] **F10-01** Escribir `duckdb/init/attach_lakehouse.sql` con una vista por producto Gold. _(diseño §34)_
- [ ] **F10-02** Escribir `duckdb/Dockerfile` para la línea de comandos opcional. _(diseño §34)_
- [ ] **F10-03** Escribir `superset/Dockerfile` con DuckDB y sus extensiones. _(diseño §35)_
- [ ] **F10-04** Escribir `superset_config.py` con el hook de conexión. _(diseño §35)_
- [ ] **F10-05** Añadir el job `superset-init`: migrar la base de metadatos. _(diseño §39)_
- [ ] **F10-06** Añadir a `superset-init` la creación del administrador. _(diseño §45.4)_
- [ ] **F10-07** Añadir a `superset-init` el registro de la base de datos DuckDB. _(diseño §35)_
- [ ] **F10-08** Añadir el servicio `superset` al Compose. _(diseño §39)_
- [ ] **F10-09** Crear un dataset por producto Gold. _(diseño §35)_
- [ ] **F10-10** Definir los dashboards y sus gráficos. _(diseño §35)_
- [ ] **F10-11** Construir los dashboards. _(diseño §35)_
- [ ] **F10-12** Exportar datasets y dashboards a `superset/config/`. _(diseño §35)_
- [ ] **F10-13** Importar datasets y dashboards desde `superset-init`. _(diseño §35)_
- [ ] **F10-14** Comprobar que los dashboards muestran datos. _(diseño §35)_

### F11 · Integración de extremo a extremo

- **Objetivo:** Comprobar que el laboratorio completo arranca con un comando y que un cambio recorre todas las capas.
- **Depende de:** F1, F5, F6, F9 y F10
- **Terminada cuando:** Se cumple el criterio de éxito de la sección 44 del diseño y no queda ningún defecto abierto.

- [ ] **F11-01** Completar los healthchecks y las dependencias entre servicios. _(diseño §40)_
- [ ] **F11-02** Comprobar que todos los servicios declaran su límite de memoria. _(diseño §39)_
- [ ] **F11-03** Levantar todo desde cero con `docker compose up -d --build`. _(diseño §39)_
- [ ] **F11-04** Seguir un INSERT desde el simulador hasta Superset. _(diseño §42)_
- [ ] **F11-05** Seguir un UPDATE desde el simulador hasta Superset. _(diseño §42)_
- [ ] **F11-06** Seguir un DELETE desde el simulador hasta Superset. _(diseño §42)_
- [ ] **F11-07** Repetir `docker compose up` y comprobar que nada se duplica. _(diseño §40)_
- [ ] **F11-08** Detener y volver a levantar el laboratorio, y comprobar que retoma. _(diseño §14)_
- [ ] **F11-09** Medir la memoria usada con todo en marcha. _(diseño §39)_
- [ ] **F11-10** Probar el arranque en una máquina Linux. _(diseño §45.2)_
- [ ] **F11-11** Anotar los defectos encontrados y corregirlos. _(sección 6 de este plan)_

### F12 · Documentación y cierre

- **Objetivo:** Dejar el laboratorio listo para que otra persona lo clone, lo levante y lo entienda.
- **Depende de:** F11
- **Terminada cuando:** Un clon limpio del repositorio levanta el laboratorio siguiendo solo el README.

- [ ] **F12-01** Actualizar el README con las instrucciones reales de ejecución. _(README §8)_
- [ ] **F12-02** Escribir la guía de la demostración paso a paso. _(diseño §42)_
- [ ] **F12-03** Actualizar el diseño con lo que cambió al implementar. _(diseño)_
- [ ] **F12-04** Actualizar los diagramas al estado final. _(diseño §4, §6, §12, §18 y §40)_
- [ ] **F12-05** Cerrar las decisiones que sigan abiertas. _(decisiones, parte 1.3)_
- [ ] **F12-06** Verificar el criterio de éxito con un clon limpio. _(diseño §44)_
- [ ] **F12-07** Publicar la versión final con una etiqueta de Git. _(—)_

## 4. Definición de terminado

Una actividad se marca como hecha solo si se cumple todo lo que le aplique:

- Su resultado existe en el repositorio y hace lo que dice la referencia.
- Se ejecutó de verdad. «Comprobar» significa haberlo visto funcionar, no haber leído el código.
- No rompe nada que ya funcionaba: las comprobaciones de las fases anteriores siguen pasando.
- No deja contraseñas ni claves escritas en ningún archivo versionado.

Además, toda actividad que añade un servicio al Compose deja ese servicio con:

- la imagen fijada a una versión exacta (diseño §3.1);
- su healthcheck, si es un servicio con estado (diseño §40);
- su límite de memoria (diseño §39);
- sus puertos del host declarados como variables ligadas a `127.0.0.1` (diseño §39);
- un usuario sin privilegios (diseño §45.2).

## 5. Bitácora de avance

Una línea por cada actividad o grupo de actividades terminado. La más reciente va arriba.

| Fecha | Actividades | Quién | Nota |
|---|---|---|---|
| 2026-11-22 | Riesgos | Agente | Tabla de riesgos separada en abiertos y cerrados; se cierran R1, R2, R4 y R7. Lectura de los 20 CSV con Commons CSV comprobada |
| 2026-11-22 | F0-14 | Agente | Validación 10 superada desde terminales de Linux y de Windows; deja cuatro ajustes en el diseño del simulador |
| 2026-11-22 | F1-04 a F1-09 | Responsable, agente y GrokBot | Dataset regenerado recibido, validado, cargado en PostgreSQL 19 y confirmado como definitivo. Fase F1 terminada |
| 2026-11-22 | F0-19 a F0-21 | Agente | Reconstrucción de Bronze comprobada con las 20 tablas; leyenda del linaje corregida y diagramas de arquitectura y de arranque regenerados |
| 2026-11-22 | F0-16 y F0-17 | Responsable y agente | Validación 12 superada con los dos gestores de autenticación; se elige el de Flask AppBuilder |
| 2026-11-22 | F0-12, F0-13 y F0-18 | Responsable y agente | Decisiones tomadas: reconstruir Bronze, `updated_at` como primer origen de `effective_from` y una sola clave de RustFS. Diseño en Revisión 6 |
| 2026-11-22 | F1-01 a F1-03 | Agente y GrokBot | Primera versión del dataset generada y validada; se pidió regenerarla |
| 2026-11-22 | F0-01 a F0-11 | Agente | Diseño en Revisión 5; validaciones 1 a 9, de volumen y de Silver ejecutadas |

## 6. Bloqueos, defectos y dudas

Lo que impide avanzar o lo que se encontró roto. Cada fila necesita una acción de la persona responsable o una corrección. Se borra la fila cuando se resuelve.

| Fecha | Actividad | Qué pasa | Qué se necesita |
|---|---|---|---|
| — | — | Sin bloqueos abiertos | — |

## 7. Riesgos

Lo que todavía no ha ocurrido pero puede retrasar el plan. Se revisa al cerrar cada fase. Un número de riesgo no se reutiliza: cuando un riesgo deja de serlo pasa a la tabla de cerrados, con el motivo.

### Riesgos abiertos

| # | Riesgo | Qué lo reduce | Si ocurre | Señal de alerta |
|---|---|---|---|---|
| R3 | Todo el stack junto no cabe en la memoria prevista | Declarar el límite de cada servicio al añadirlo | Detener el simulador o Superset mientras corre el DAG | F11-09 supera 15 GB |
| R5 | El trabajo generado por un agente funciona a medias y se marca como hecho | Aplicar la definición de terminado y las actividades «Comprobar» | Desmarcar la actividad y anotarla en la sección 6 | Una comprobación posterior falla |
| R6 | DuckDB JDBC no adjunta el catálogo o no lee Bronze desde Java 25 | Ejecutar F0-15 antes de empezar el seguimiento en F6 | Usar la alternativa de la validación 11 | F0-15 falla |
| R8 | Una corrida del DAG lee Bronze a medio reconstruir y cierra versiones de filas que siguen existiendo | Pausar el DAG antes de reconstruir, como pide el procedimiento | Restaurar Silver al snapshot anterior de Iceberg | El DAG corre mientras `flink-cdc-submit` está repitiendo el snapshot |

### Riesgos cerrados

| # | Riesgo | Fecha de cierre | Por qué se cerró |
|---|---|---|---|
| R1 | La consola Lanterna no funciona a través de `docker compose attach` | 2026-11-22 | La validación 10 pasó desde una terminal de Linux y otra de Windows (F0-14) |
| R2 | El dataset regenerado llega tarde o no cumple | 2026-11-22 | El dataset regenerado se recibió, se validó y quedó como definitivo (F1-04 a F1-09) |
| R4 | Una decisión abierta de F0 frena una fase del camino más largo | 2026-11-22 | No queda ninguna decisión abierta |
| R7 | El lector CSV del simulador no interpreta bien las celdas con comas, comillas y saltos de línea | 2026-11-22 | Apache Commons CSV 1.14.1 lee los 20 CSV desde Java 25 con el mismo contenido, celda por celda, que una lectura de referencia |
