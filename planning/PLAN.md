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
| F0 | Diseño y validaciones previas | 21 | 21 | 100 % | ✅ Terminada |
| F1 | Dataset de entrada | 9 | 9 | 100 % | ✅ Terminada |
| F2 | Base del proyecto | 9 | 9 | 100 % | ✅ Terminada |
| F3 | PostgreSQL operacional | 15 | 15 | 100 % | ✅ Terminada |
| F4 | Almacenamiento y catálogo | 7 | 0 | 0 % | ⏳ Pendiente |
| F5 | Flink CDC hacia Bronze | 20 | 0 | 0 % | ⏳ Pendiente |
| F6 | Event Simulator | 45 | 0 | 0 % | ⏳ Pendiente |
| F7 | Spark y capa Silver | 35 | 0 | 0 % | ⏳ Pendiente |
| F8 | Capa Gold | 10 | 0 | 0 % | ⏳ Pendiente |
| F9 | Orquestación con Airflow | 19 | 0 | 0 % | ⏳ Pendiente |
| F10 | DuckDB y Superset | 13 | 0 | 0 % | ⏳ Pendiente |
| F11 | Integración de extremo a extremo | 12 | 0 | 0 % | ⏳ Pendiente |
| F12 | Documentación y cierre | 7 | 0 | 0 % | ⏳ Pendiente |
| | **Global** | **222** | **54** | **24 %** | 🔄 En curso |

Actualizado el 2026-11-22.
<!-- tablero:fin -->

El tablero no se edita a mano: lo recalcula `python planning/update_progress.py` a partir de las casillas marcadas. El mismo script, con `--done`, registra cada actividad terminada e imprime el avance de su fase y el global (regla 6 de la sección 2).

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
6. **Registra y reporta el avance al terminar cada actividad**, en el mismo cambio que el trabajo:
   - ejecuta `python planning/update_progress.py --done F3-04 --note "qué se hizo y cómo se comprobó"`. El script marca la actividad, recalcula el tablero, añade la línea a la bitácora de la sección 5 con el avance y lo imprime;
   - **comunica ese avance a la persona responsable** en tu mensaje de cierre, tal como lo imprime el script: el de la fase y el global, en actividades y en porcentaje. Por ejemplo: «F3 · PostgreSQL operacional: 3 de 15 actividades (20 %). Global: 42 de 222 actividades (19 %)»;
   - si terminas varias actividades seguidas, repórtalo tras cada una o, como mínimo, al final con el avance de cada fase tocada.
7. **Al cerrar una fase**, comprueba su «Terminada cuando». Si no se cumple, la fase sigue abierta aunque todas sus casillas estén marcadas: añade la actividad que falte.
8. **Si aparece trabajo que el plan no prevé**, añádelo como actividad nueva dentro de su fase, en la posición en que deba hacerse, con el siguiente número libre. No renumeres las existentes: el número identifica la actividad, no indica su orden.
9. **Activa la skill de la actividad antes de empezarla.** Cada fase indica la suya; el detalle y la forma de activarla en cada agente están en [AGENTS.md](../AGENTS.md).

Cada actividad tiene un identificador fijo, como `F3-04`: fase 3, actividad 4. Úsalo en la bitácora y en los mensajes de commit.

## 3. Fases y dependencias

![Dependencias entre las 13 fases del plan, de F0 a F12: en la columna central, de arriba abajo, el camino más largo (F2, F3, F5, F7, F8, F9, F10, F11 y F12); a los lados, las fases F0, F1, F4 y F6 con las fases que dependen de ellas](../lab-design/diagrams/plan-phases.svg)

> Versión interactiva: [`../lab-design/diagrams/plan-phases.html`](../lab-design/diagrams/plan-phases.html) · Fuente editable: [`../lab-design/diagrams/plan-phases.json`](../lab-design/diagrams/plan-phases.json).

Cada flecha es una dependencia entre fases completas; las verdes, además, forman el camino más largo, que ocupa la columna central. No se dibujan las dependencias que ya se deducen de otras, ni las esperas a actividades de F0, que está terminada.

| Fase | Depende de | Puede avanzar en paralelo con |
|---|---|---|
| F0 · Diseño y validaciones previas | Nada | F1 y F2 |
| F1 · Dataset de entrada | Nada | F0 y F2 |
| F2 · Base del proyecto | Nada | F0 y F1 |
| F3 · PostgreSQL operacional | F2 | F4 |
| F4 · Almacenamiento y catálogo | F2 | F3 |
| F5 · Flink CDC hacia Bronze | F3, F4 y la actividad F0-12 | Ninguna |
| F6 · Event Simulator | F1, F5 y las actividades F0-14 y F0-15 | F7, F8, F9 y F10 |
| F7 · Spark y capa Silver | F5 y la actividad F0-13 | F6 |
| F8 · Capa Gold | F7 | F6 |
| F9 · Orquestación con Airflow | F8 y las actividades F0-16 y F0-17 | F6 |
| F10 · DuckDB y Superset | F8 y F9 | F6 |
| F11 · Integración de extremo a extremo | F1, F5, F6, F9 y F10 | Ninguna |
| F12 · Documentación y cierre | F11 | Ninguna |

**Camino más largo:** F2 → F3 → F5 → F7 → F8 → F9 → F10 → F11 → F12. Un retraso en cualquiera de esas fases retrasa el final. F6 es la fase con más actividades, pero puede hacerse en paralelo desde que termina F5.

**Hitos:**

| Hito | Se alcanza al terminar | Qué se puede enseñar |
|---|---|---|
| H1 · Bronze en vivo | F5 | Un cambio en PostgreSQL aparece en Bronze segundos después |
| H2 · Simulador en marcha | F6 | Transacciones generadas y dirigidas desde la consola |
| H3 · Lakehouse completo | F8 | Silver con historial y los siete productos Gold |
| H4 · Superset listo | F10 | Un gráfico creado a mano en Superset sobre un producto Gold |
| H5 · Laboratorio completo | F11 | Un cambio recorre todo el camino con un único `docker compose up` |

### F0 · Diseño y validaciones previas

- **Objetivo:** Tener un diseño completo y probado antes de escribir el laboratorio.
- **Depende de:** Nada
- **Skill:** No aplica: fase terminada
- **Terminada cuando:** Las validaciones 1 a 12 están ejecutadas y todas sus actividades, marcadas.

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
- [x] **F0-15** Ejecutar la validación 11: DuckDB JDBC lee Bronze desde Java 25. _(validaciones, parte 2)_
- [x] **F0-16** Ejecutar la validación 12: inicio de sesión del administrador de Airflow. _(validaciones, parte 2)_
- [x] **F0-17** Decidir el gestor de autenticación de Airflow. _(decisión 30)_
- [x] **F0-18** Decidir si DuckDB usa una clave de RustFS de solo lectura. _(decisión 28)_
- [x] **F0-19** Corregir la leyenda del diagrama de linaje. _(decisión 29)_
- [x] **F0-20** Regenerar los diagramas de arquitectura y de orden de arranque. _(diseño §4 y §40)_
- [x] **F0-21** Comprobar la reconstrucción de Bronze tras perder los checkpoints. _(diseño §38)_

### F1 · Dataset de entrada

- **Objetivo:** Tener en `raw_data/` los 20 CSV definitivos, validados.
- **Depende de:** Nada
- **Skill:** No aplica: fase terminada
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
- **Skill:** `/solution-architect`
- **Terminada cuando:** `docker compose config` valida sin errores, `volumes-init` termina con código 0 y `metadata-db` arranca sano.

- [x] **F2-01** Crear `.env.example` con todas las variables. _(diseño §45.5, §39, §9.6, §14 y §16)_
- [x] **F2-02** Crear el `.env` local a partir de `.env.example`. _(diseño §45.5)_
- [x] **F2-03** Crear `docker-compose.yml` con el nombre del proyecto. _(diseño §39)_
- [x] **F2-04** Declarar los puertos del host como variables ligadas a `127.0.0.1`. _(diseño §39)_
- [x] **F2-05** Añadir el job `volumes-init`. _(diseño §45.2)_
- [x] **F2-06** Comprobar que `docker compose config` valida sin errores. _(diseño §39)_
- [x] **F2-07** Comprobar que `volumes-init` deja cada directorio con su usuario. _(diseño §45.2)_
- [x] **F2-08** Añadir `metadata-db` con las bases `airflow` y `superset`. _(diseño §45.3)_
- [x] **F2-09** Comprobar que `metadata-db` arranca sano con sus dos bases. _(diseño §45.3)_

### F3 · PostgreSQL operacional

- **Objetivo:** Tener la base `elastiflix` con su esquema `catalog` lista para capturar cambios.
- **Depende de:** F2
- **Skill:** `/solution-architect`
- **Terminada cuando:** El servicio arranca sano, crea las 20 tablas y la publicación, y los 20 CSV cargan con `COPY` sin errores.

- [x] **F3-01** Escribir el DDL de los 4 catálogos. _(diseño §12)_
- [x] **F3-02** Escribir el DDL de las 7 entidades compartidas. _(diseño §12)_
- [x] **F3-03** Escribir el DDL de `movie` y `movie_collection`. _(diseño §12)_
- [x] **F3-04** Escribir el DDL de las 6 tablas de relación y de `movie_enrichment`. _(diseño §12)_
- [x] **F3-05** Revisar el DDL con las observaciones de la validación del dataset. _(validaciones, parte 2)_
- [x] **F3-06** Crear el rol `elastiflix_app`. _(diseño §45.3)_
- [x] **F3-07** Crear el rol `elastiflix_cdc`. _(diseño §45.3)_
- [x] **F3-08** Tomar las contraseñas de los roles desde variables de entorno. _(diseño §45.5)_
- [x] **F3-09** Configurar `REPLICA IDENTITY FULL` en las 20 tablas. _(diseño §10)_
- [x] **F3-10** Crear la publicación `elastiflix_pub`. _(diseño §10)_
- [x] **F3-11** Añadir el servicio `postgresql` al Compose con sus parámetros de replicación. _(diseño §10)_
- [x] **F3-12** Añadir el healthcheck de `postgresql`. _(diseño §40)_
- [x] **F3-13** Comprobar que el esquema se crea al arrancar. _(diseño §10)_
- [x] **F3-15** Escribir `postgresql/scripts/load_dev_data.sql`, que carga los 20 CSV para el desarrollo. _(diseño §39)_
- [x] **F3-14** Comprobar que los 20 CSV cargan sin errores con ese script. _(diseño §8.3 y §39)_

### F4 · Almacenamiento y catálogo

- **Objetivo:** Tener RustFS y el Iceberg REST Catalog listos para recibir tablas.
- **Depende de:** F2
- **Skill:** `/solution-architect`
- **Terminada cuando:** El bucket `warehouse` y los namespaces `bronze`, `silver` y `gold` existen y sobreviven a recrear los contenedores.

- [ ] **F4-01** Añadir el servicio `rustfs` con su healthcheck. _(diseño §15)_
- [ ] **F4-02** Añadir el job `rustfs-init` que crea el bucket `warehouse`. _(diseño §15)_
- [ ] **F4-03** Añadir el servicio `iceberg-rest` con su catálogo guardado en `iceberg/data/`. _(diseño §16)_
- [ ] **F4-04** Añadir el job `iceberg-init` que crea los tres namespaces. _(diseño §16)_
- [ ] **F4-05** Comprobar que el bucket y los namespaces existen. _(diseño §15 y §16)_
- [ ] **F4-06** Comprobar que los namespaces siguen ahí tras recrear `iceberg-rest`. _(diseño §16)_
- [ ] **F4-07** Comprobar que se entra a la consola web de RustFS con la clave del servicio. _(diseño §45.4)_

### F5 · Flink CDC hacia Bronze

- **Objetivo:** Replicar en Bronze, de forma continua, cada cambio de PostgreSQL.
- **Depende de:** F3, F4 y la actividad F0-12
- **Skill:** `/solution-architect`
- **Terminada cuando:** Las 20 tablas están en Bronze, reflejan INSERT, UPDATE y DELETE, y el pipeline se reanuda al repetir `docker compose up` tras reiniciar Flink.

- [ ] **F5-01** Escribir `flink/Dockerfile` con Flink CDC y sus JAR. _(diseño §14)_
- [ ] **F5-02** Escribir la configuración de Flink: checkpoint de 30 s y checkpoints retenidos. _(diseño §14)_
- [ ] **F5-03** Escribir el pipeline `flink/jobs/postgres-to-bronze.yaml`. _(diseño §14)_
- [ ] **F5-04** Añadir `flink-jobmanager` al Compose. _(diseño §39)_
- [ ] **F5-05** Añadir `flink-taskmanager` al Compose. _(diseño §39)_
- [ ] **F5-06** Escribir el script de envío: no enviar si el job ya está en ejecución. _(diseño §14)_
- [ ] **F5-07** Escribir el script de envío: reanudar desde el último checkpoint. _(diseño §14)_
- [ ] **F5-08** Escribir el script de envío: detenerse con error si no hay checkpoint y Bronze ya tiene tablas. _(diseño §14)_
- [ ] **F5-17** Escribir el script de envío: generar el YAML con la contraseña de `.env`. _(diseño §14)_
- [ ] **F5-18** Escribir el script de envío: esperar a que el job esté en `RUNNING` antes de terminar. _(diseño §14)_
- [ ] **F5-09** Añadir el job `flink-cdc-submit` al Compose. _(diseño §39)_
- [ ] **F5-10** Comprobar que las 20 tablas llegan a Bronze. _(diseño §17)_
- [ ] **F5-11** Comprobar un INSERT en Bronze. _(diseño §17)_
- [ ] **F5-12** Comprobar un UPDATE en Bronze. _(diseño §17)_
- [ ] **F5-13** Comprobar un DELETE en Bronze. _(diseño §17)_
- [ ] **F5-14** Comprobar que repetir `docker compose up` no crea un segundo job. _(diseño §14)_
- [ ] **F5-15** Comprobar que, tras reiniciar el JobManager, repetir `docker compose up` reanuda el pipeline desde su checkpoint. _(diseño §14)_
- [ ] **F5-19** Comprobar que el script de envío se detiene sin borrar nada si no hay checkpoint y Bronze ya tiene tablas. _(diseño §14)_
- [ ] **F5-16** Escribir el script que elimina las tablas Bronze para reconstruirlas. _(diseño §38)_
- [ ] **F5-20** Comprobar la reconstrucción de Bronze con el script de borrado. _(diseño §38)_

### F6 · Event Simulator

- **Objetivo:** Tener el simulador Java 25 generando transacciones reales, con su interfaz de consola.
- **Depende de:** F1, F5 y las actividades F0-14 y F0-15
- **Skill:** `/java-developer`; `/solution-architect` para el Dockerfile y el Compose
- **Terminada cuando:** El simulador cumple los requisitos RF-01 a RF-13 y su interfaz se abre con `docker compose attach`.

- [ ] **F6-01** Crear el proyecto Maven con sus dependencias. _(diseño §9.8)_
- [ ] **F6-02** Leer la configuración desde variables de entorno. _(diseño §9.6)_
- [ ] **F6-03** Cargar los 20 CSV en memoria. _(RF-01)_
- [ ] **F6-04** Conectar con PostgreSQL usando `elastiflix_app`. _(diseño §45.3)_
- [ ] **F6-05** Dar de alta una película en una sola transacción. _(RF-02)_
- [ ] **F6-06** Insertar catálogos y entidades la primera vez que se necesitan. _(diseño §9.5)_
- [ ] **F6-42** Al arrancar, leer de PostgreSQL lo ya insertado y continuar con la primera película pendiente. _(RF-13 y diseño §9.5)_
- [ ] **F6-07** Implementar el UPDATE descriptivo. _(RF-03)_
- [ ] **F6-08** Implementar el UPDATE de medidas. _(RF-03)_
- [ ] **F6-09** Implementar el UPDATE de relaciones, que actualiza también `updated_at` de la película. _(RF-03 y diseño §9.5)_
- [ ] **F6-41** Implementar el UPDATE de catálogo: renombrar una colección o una keyword con el sufijo `(rev N)`. _(RF-03 y diseño §9.5)_
- [ ] **F6-10** Implementar el DELETE de una película. _(RF-03)_
- [ ] **F6-11** Implementar la reinserción de una película borrada. _(RF-03)_
- [ ] **F6-12** Elegir la siguiente operación según los pesos y la semilla. _(RF-04 y RF-05)_
- [ ] **F6-43** Elegir el tipo de UPDATE con la semilla, entre los que la película admite. _(diseño §9.5)_
- [ ] **F6-13** Implementar el modo continuo, con la reinserción automática cuando ya no quedan películas pendientes. _(diseño §9.5)_
- [ ] **F6-14** Ante un dato inconsistente: revertir, registrar y continuar. _(RF-12)_
- [ ] **F6-15** Registrar cada transacción, cada cambio de configuración y cada operación manual, también en `/tmp/simulator.log`. _(RF-11 y diseño §9.8)_
- [ ] **F6-16** Implementar el modo de líneas, que es como arranca el simulador. _(RF-10 y diseño §9.4)_
- [ ] **F6-17** Dibujar la cabecera de la pantalla. _(diseño §9.3)_
- [ ] **F6-18** Dibujar la zona de avance. _(diseño §9.3)_
- [ ] **F6-19** Dibujar la zona de operaciones. _(diseño §9.3)_
- [ ] **F6-20** Dibujar la lista de últimas transacciones. _(diseño §9.3)_
- [ ] **F6-21** Dibujar la zona de detalle. _(diseño §9.3)_
- [ ] **F6-33** Abrir la interfaz con la primera tecla y cerrarla con `Q`. _(diseño §9.4)_
- [ ] **F6-34** Atrapar `Ctrl-C` para que no detenga el simulador. _(diseño §9.8)_
- [ ] **F6-35** Repintar la pantalla completa cada 2 segundos y al cambiar de tamaño. _(diseño §9.8)_
- [ ] **F6-40** Mostrar un aviso cuando la terminal mida menos de 100×30. _(diseño §9.2)_
- [ ] **F6-22** Implementar pausar y reanudar. _(RF-07)_
- [ ] **F6-23** Implementar el cambio de velocidad. _(RF-07)_
- [ ] **F6-24** Implementar el diálogo de pesos. _(RF-07)_
- [ ] **F6-25** Implementar el diálogo de operación manual. _(RF-08)_
- [ ] **F6-37** Abrir DuckDB en un hilo propio, con hilos y memoria limitados, y reabrirlo si una consulta falla. _(diseño §9.8)_
- [ ] **F6-26** Implementar el seguimiento del cambio hasta Bronze, con el instante de referencia truncado. _(RF-09 y diseño §9.3)_
- [ ] **F6-38** Marcar como demorada la transacción que no llega a Bronze en 120 segundos. _(diseño §9.3)_
- [ ] **F6-27** Escribir pruebas unitarias de la lectura de CSV. _(diseño §9.1)_
- [ ] **F6-28** Escribir pruebas unitarias de la selección de operaciones. _(RF-05)_
- [ ] **F6-29** Escribir `java-simulator/Dockerfile` con el usuario `simulator` y las opciones de la JVM. _(diseño §9.8 y §45.2)_
- [ ] **F6-39** Instalar las extensiones de DuckDB durante el build de la imagen. _(diseño §34)_
- [ ] **F6-30** Añadir `java-simulator` al Compose, con `tty` y `stdin_open`, después de `flink-cdc-submit`. _(diseño §9.8 y §40)_
- [ ] **F6-36** Limitar el tamaño del log del servicio en el Compose. _(diseño §9.8)_
- [ ] **F6-44** Volver el laboratorio a cero antes de las comprobaciones del simulador. _(diseño §39)_
- [ ] **F6-31** Comprobar la interfaz con `docker compose attach java-simulator`. _(diseño §9.8)_
- [ ] **F6-32** Comprobar que la misma semilla repite la misma secuencia. _(RF-05)_
- [ ] **F6-45** Comprobar que, tras detener y arrancar el contenedor, el simulador continúa sin repetir altas. _(RF-13)_

### F7 · Spark y capa Silver

- **Objetivo:** Construir el modelo dimensional con historial a partir de Bronze.
- **Depende de:** F5 y la actividad F0-13
- **Skill:** `/python-developer`; `/solution-architect` para el Dockerfile, la configuración de Spark y el Compose
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
- [ ] **F7-28** Cargar `fact_movie_snapshot`, con `record_hash` sobre las claves de negocio. _(diseño §27)_
- [ ] **F7-29** Cargar `fact_movie_enrichment`. _(diseño §29)_
- [ ] **F7-30** Reparar las referencias que quedaron con clave 0. _(diseño §19 y §30)_
- [ ] **F7-31** Comprobar que una segunda corrida sin cambios no escribe nada. _(diseño §19)_
- [ ] **F7-32** Comprobar un INSERT, un UPDATE, un DELETE y una reinserción en Silver. _(diseño §31)_
- [ ] **F7-33** Cerrar las versiones vigentes cuya clave ya no aparece en Bronze. _(diseño §19 y §38)_
- [ ] **F7-35** Comprobar que renombrar una colección o una keyword crea su versión nueva sin crear snapshot. _(diseño §31)_
- [ ] **F7-34** Comprobar que un tombstone sin versión previa no crea versión ni snapshot. _(diseño §31)_

### F8 · Capa Gold

- **Objetivo:** Materializar los productos analíticos que consultará Superset.
- **Depende de:** F7
- **Skill:** `/python-developer`
- **Terminada cuando:** Los siete productos Gold existen y se reemplazan completos en cada corrida.

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

### F9 · Orquestación con Airflow

- **Objetivo:** Ejecutar y validar los jobs de Silver y Gold desde un DAG.
- **Depende de:** F8 y las actividades F0-16 y F0-17
- **Skill:** `/python-developer`; `/solution-architect` para el Dockerfile y el Compose
- **Terminada cuando:** Una corrida del DAG `elastiflix_medallion` termina en `success` y deja Silver y Gold actualizados.

- [ ] **F9-02** Escribir `airflow/Dockerfile` con Java, PySpark y los JAR de Iceberg. _(diseño §18)_
- [ ] **F9-03** Añadir el job `airflow-init`. _(diseño §39)_
- [ ] **F9-04** Añadir `airflow-apiserver` al Compose. _(diseño §18)_
- [ ] **F9-05** Añadir `airflow-scheduler` al Compose. _(diseño §18)_
- [ ] **F9-06** Añadir `airflow-dag-processor` al Compose. _(diseño §18)_
- [ ] **F9-07** Crear el administrador de Airflow con `airflow users create`. _(diseño §45.4)_
- [ ] **F9-08** Escribir el job `iceberg_maintenance.py`. _(diseño §38)_
- [ ] **F9-09** Crear el DAG `elastiflix_medallion`. _(diseño §18)_
- [ ] **F9-19** Programar el DAG cada 10 minutos, activo desde que se crea, sin `catchup` y con una sola corrida a la vez. _(diseño §18)_
- [ ] **F9-10** Escribir `validate_bronze.py`, que comprueba las tablas y el job de Flink, y añadir su tarea. _(diseño §18)_
- [ ] **F9-11** Añadir la tarea `bronze_to_silver`, que pasa `dag_run.run_after` al job. _(diseño §18 y §21)_
- [ ] **F9-12** Escribir `validate_silver.py` y añadir la tarea `validate_silver`. _(diseño §18)_
- [ ] **F9-13** Añadir la tarea `silver_to_gold`. _(diseño §18)_
- [ ] **F9-14** Escribir `validate_gold.py` y añadir la tarea `validate_gold`. _(diseño §18)_
- [ ] **F9-15** Añadir la tarea `iceberg_maintenance`, que corre siempre al final (`trigger_rule = all_done`). _(diseño §18 y §38)_
- [ ] **F9-16** Comprobar una corrida completa del DAG. _(diseño §18)_
- [ ] **F9-17** Comprobar que una validación fallida detiene el DAG, salvo el mantenimiento. _(diseño §18)_
- [ ] **F9-18** Comprobar la reconstrucción de Bronze con el DAG pausado y reanudado después. _(diseño §38, decisión 39)_
- [ ] **F9-20** Comprobar que el DAG empieza a correr solo, sin activarlo a mano. _(diseño §18)_

### F10 · DuckDB y Superset

- **Objetivo:** Dejar Superset listo para que quien use el laboratorio conecte Gold y cree sus visualizaciones.
- **Depende de:** F8 y F9
- **Skill:** `/python-developer` para la configuración de Superset; `/solution-architect` para el SQL de DuckDB, el Dockerfile y el Compose
- **Terminada cuando:** Siguiendo la guía del diseño, se conecta la base DuckDB, se crea un dataset sobre un producto Gold y un gráfico muestra sus datos.

- [ ] **F10-01** Escribir `duckdb/init/attach_lakehouse.sql` y `duckdb/init/gold_views.sql`. _(diseño §34)_
- [ ] **F10-02** Escribir `duckdb/Dockerfile` para la línea de comandos opcional. _(diseño §34)_
- [ ] **F10-15** Añadir el servicio `duckdb` al Compose, bajo el perfil `tools`. _(diseño §34 y §39)_
- [ ] **F10-03** Escribir `superset/Dockerfile` con DuckDB y sus extensiones. _(diseño §35)_
- [ ] **F10-04** Escribir `superset_config.py` con el hook de conexión, que crea solo las vistas de las tablas Gold que existen. _(diseño §35)_
- [ ] **F10-05** Añadir el job `superset-init`: migrar la base de metadatos. _(diseño §39)_
- [ ] **F10-06** Añadir a `superset-init` la creación del administrador. _(diseño §45.4)_
- [ ] **F10-08** Añadir el servicio `superset` al Compose. _(diseño §39)_
- [ ] **F10-16** Comprobar que Superset abre conexiones sin errores antes de la primera corrida del DAG y que, después, el hook crea las vistas de las tablas Gold que existen. _(diseño §34 y §35)_
- [ ] **F10-17** Comprobar que DuckDB lee los siete productos Gold. _(diseño §34)_
- [ ] **F10-20** Seguir la guía de Superset paso a paso: conectar la base, crear un dataset sobre un producto Gold y un gráfico. _(diseño §35)_
- [ ] **F10-21** Corregir la guía con lo que difiera en la interfaz real. _(diseño §35)_
- [ ] **F10-14** Comprobar que el gráfico refleja un cambio tras la siguiente corrida del DAG. _(diseño §35)_

### F11 · Integración de extremo a extremo

- **Objetivo:** Comprobar que el laboratorio completo arranca con un comando y que un cambio recorre todas las capas.
- **Depende de:** F1, F5, F6, F9 y F10
- **Skill:** `/solution-architect`
- **Terminada cuando:** Se cumple el criterio de éxito de la sección 44 del diseño y no queda ningún defecto abierto.

- [ ] **F11-01** Completar los healthchecks y las dependencias entre servicios. _(diseño §40)_
- [ ] **F11-02** Comprobar que todos los servicios declaran su límite de memoria. _(diseño §39)_
- [ ] **F11-12** Volver el laboratorio a cero con el procedimiento del diseño. _(diseño §39)_
- [ ] **F11-03** Levantar todo desde cero con `docker compose up -d --build`. _(diseño §39)_
- [ ] **F11-13** Conectar la base y crear un gráfico en Superset con la guía, para seguir los cambios. _(diseño §35)_
- [ ] **F11-04** Seguir un INSERT desde el simulador hasta Superset. _(diseño §42)_
- [ ] **F11-05** Seguir un UPDATE desde el simulador hasta Superset. _(diseño §42)_
- [ ] **F11-06** Seguir un DELETE desde el simulador hasta Superset. _(diseño §42)_
- [ ] **F11-07** Repetir `docker compose up` y comprobar que nada se duplica. _(diseño §40)_
- [ ] **F11-08** Detener y volver a levantar el laboratorio, y comprobar que el pipeline y el simulador retoman. _(diseño §9.5, §14 y §39)_
- [ ] **F11-09** Medir la memoria usada con todo en marcha. _(diseño §39)_
- [ ] **F11-11** Anotar los defectos encontrados y corregirlos. _(sección 6 de este plan)_

### F12 · Documentación y cierre

- **Objetivo:** Dejar el laboratorio listo para que otra persona lo clone, lo levante y lo entienda.
- **Depende de:** F11
- **Skill:** `/solution-architect`
- **Terminada cuando:** Un clon limpio del repositorio levanta el laboratorio siguiendo solo el README.

- [ ] **F12-01** Actualizar el README con las instrucciones reales de ejecución. _(README §8)_
- [ ] **F12-02** Escribir la guía de la demostración paso a paso. _(diseño §42)_
- [ ] **F12-03** Actualizar el diseño con lo que cambió al implementar. _(diseño)_
- [ ] **F12-04** Actualizar los diagramas al estado final. _(diseño §4, §6, §9.3, §12, §18, §35, §36, §40 y §44; plan §3)_
- [ ] **F12-05** Cerrar las decisiones que sigan abiertas. _(decisiones, parte 1.3)_
- [ ] **F12-06** Verificar el criterio de éxito con un clon limpio. _(diseño §44)_
- [ ] **F12-07** Publicar la versión final con una etiqueta de Git. _(—)_

## 4. Definición de terminado

Una actividad se marca como hecha solo si se cumple todo lo que le aplique:

- Su resultado existe en el repositorio y hace lo que dice la referencia.
- Se ejecutó de verdad. «Comprobar» significa haberlo visto funcionar, no haber leído el código.
- No rompe nada que ya funcionaba: las comprobaciones de las fases anteriores siguen pasando.
- No deja contraseñas ni claves escritas en ningún archivo versionado. La única excepción es `.env.example`, que lleva valores de laboratorio para que el entorno arranque tal cual (diseño §45.5, decisión 66).

Además, toda actividad que añade un servicio al Compose deja ese servicio con:

- la imagen fijada a una versión exacta (diseño §3.1);
- su healthcheck, si es un servicio con estado (diseño §40);
- su límite de memoria (diseño §39);
- sus puertos del host declarados como variables ligadas a `127.0.0.1` (diseño §39);
- un usuario sin privilegios (diseño §45.2); la única excepción es `volumes-init`, que corre como `root`.

Los jobs one-shot no llevan healthcheck: el Compose espera a que terminen con `service_completed_successfully` (diseño §40).

## 5. Bitácora de avance

Una línea por cada actividad o grupo de actividades terminado. La más reciente va arriba. La columna «Avance» guarda el avance de la fase y el global al cerrar esa línea; la escribe `update_progress.py --done`. Las líneas con «—» son anteriores a esta columna o no cierran ninguna actividad.

| Fecha | Actividades | Quién | Avance | Nota |
|---|---|---|---|---|
| 2026-11-22 | F3 | Agente | F3 100 % · Global 24 % | Fase terminada. Comprobación desde cero en el Compose: `postgresql` y `metadata-db` quedan sanos en 46 s, 20 tablas con identidad completa y publicadas, y los 20 CSV cargan con el script de desarrollo en 24 s (438,925 filas). Lo de F2 sigue funcionando y ningún secreto sale de `.env.example` |
| 2026-11-22 | F3-14 | Agente | F3 100 % · Global 24 % | Con el servicio del Compose recién creado, el comando documentado, lanzado desde PowerShell, carga los 20 CSV sin errores: 438,925 filas, las mismas que los archivos tabla por tabla. Una segunda ejecución se detiene con un mensaje y no toca nada |
| 2026-11-22 | F3-15 | Agente | F3 93 % · Global 24 % | `postgresql/scripts/load_dev_data.sql` carga los 20 CSV con `\copy` en orden de claves foráneas y en una sola transacción, con la cuenta `elastiflix_app`; se niega si `catalog` ya tiene datos y termina con el conteo por tabla. Su cabecera lleva el comando para lanzarlo desde un contenedor temporal |
| 2026-11-22 | F3-13 | Agente | F3 87 % · Global 23 % | Arranque desde cero en el Compose: los nueve archivos de `postgresql/init/` se ejecutan sin errores y dejan el esquema `catalog` con 20 tablas vacías y 74 columnas, 20 claves primarias, 19 foráneas (8 con cascada), 11 únicas y 17 `CHECK`, identidad de réplica completa en las 20, las dos cuentas con contraseña y la publicación con las 20 tablas |
| 2026-11-22 | F3-12 | Agente | F3 80 % · Global 23 % | Healthcheck `pg_isready` por TCP contra la base `elastiflix`: solo da sano cuando la inicialización terminó. Con `docker compose up -d --wait postgresql` queda sano en 36 s desde cero |
| 2026-11-22 | F3-11 | Agente | F3 73 % · Global 23 % | Servicio `postgresql` (`postgres:19.0`, 1 GB, puerto en `127.0.0.1`) con `wal_level=logical`, 10 slots, 10 emisores de WAL y `max_slot_wal_keep_size=2GB`. Arranca desde cero, ejecuta los nueve archivos de `postgresql/init/` y deja 20 tablas vacías; las dos cuentas entran desde otro contenedor solo con su contraseña; al reiniciar conserva los datos |
| 2026-11-22 | F3-10 | Agente | F3 67 % · Global 22 % | `postgresql/init/09-publication.sql` crea `elastiflix_pub` con `FOR TABLES IN SCHEMA catalog`. En el Compose publica las 20 tablas; con un slot `pgoutput` creado por `elastiflix_cdc` se leyeron 5 INSERT, 1 UPDATE y 2 DELETE (uno por cascada) hechos por `elastiflix_app` |
| 2026-11-22 | F3-09 | Agente | F3 60 % · Global 22 % | `postgresql/init/08-replica-identity.sql` aplica `REPLICA IDENTITY FULL` a las 20 tablas y termina con una comprobación que detiene la inicialización si alguna tabla de `catalog` queda sin ella. Probado con decodificación lógica: un UPDATE y un DELETE de `movie` llevan las 25 columnas, y los 62 borrados en cascada llevan su fila completa |
| 2026-11-22 | F3-08 | Agente | F3 53 % · Global 21 % | `postgresql/init/07-role-passwords.sh` pone la contraseña a `elastiflix_app` y `elastiflix_cdc` desde `ELASTIFLIX_APP_PASSWORD` y `ELASTIFLIX_CDC_PASSWORD`, como variables de `psql`. Probado: quedan en `scram-sha-256`, cada cuenta entra desde la red solo con la suya, no aparecen en el log y, si falta una variable, la inicialización se detiene con un mensaje |
| 2026-11-22 | F3-07 | Agente | F3 47 % · Global 21 % | El mismo archivo crea `elastiflix_cdc` con `REPLICATION` y `SELECT` en las 20 tablas, sin superusuario. Probado con `wal_level=logical`: lee, crea y borra un slot lógico con `pgoutput`; no puede modificar datos ni crear publicaciones |
| 2026-11-22 | F3-06 | Agente | F3 40 % · Global 20 % | `postgresql/init/06-roles.sql` crea `elastiflix_app`, sin contraseña todavía (F3-08), con `SELECT`, `INSERT`, `UPDATE` y `DELETE` en las 20 tablas. Probado: carga los 20 CSV, actualiza y borra; no puede vaciar, crear ni alterar tablas, ni usar slots; desde la red se le rechaza |
| 2026-11-22 | F3-05 | Agente | F3 33 % · Global 20 % | Repasadas las seis observaciones de la validación del dataset y sus defectos intencionales contra el DDL, con el dataset cargado en PostgreSQL 19.0: ninguna pide cambios. La keyword `none` se guarda como texto, los 666 títulos en alfabeto no latino entran en UTF8, y conviven los 18 pares de compañías «X» / «X Ltd.» y los nombres compartidos de keyword y colección. Solo se añade un comentario sobre `none` |
| 2026-11-22 | F3-04 | Agente | F3 27 % · Global 19 % | `postgresql/init/05-relations.sql` con las 6 tablas de relación y `movie_enrichment`: clave compuesta, posición única desde 1 y `ON DELETE CASCADE` solo hacia `movie`. Con las 20 tablas cargan los 20 CSV (438,925 filas, igual que los archivos); borrar una película elimina sus 62 filas de relación y deja intactas las entidades compartidas |
| 2026-11-22 | F3-03 | Agente | F3 20 % · Global 19 % | `postgresql/init/04-movie.sql` con `movie` (tres claves foráneas a catálogos, las diez reglas de la sección 12.2 como `CHECK` e índice único parcial en `imdb_id`) y `movie_collection`. En un PostgreSQL 19.0 desechable cargan sus CSV (6,899 y 1,934 filas) y cada regla rechaza su caso inválido |
| 2026-11-22 | Plan | Responsable y agente | — | El avance no se estaba reportando al terminar cada actividad: el tablero lo registraba, pero el script solo imprimía el global y ninguna regla pedía comunicarlo. `update_progress.py` gana `--done`, que marca, registra en la bitácora e imprime el avance de la fase y el global; la bitácora gana la columna «Avance» y la regla 6 obliga a reportarlo |
| 2026-11-22 | F3-02 | Agente | F3 13 % · Global 18 % | `postgresql/init/03-shared-entities.sql` con las 7 entidades compartidas: claves del dataset sin secuencias, nombre único salvo en `collection` y `keyword`, y fechas con `now()` en `collection`, `keyword` y `person`. Cargan sus 7 CSV (116,097 filas) y las restricciones responden como pide el diseño |
| 2026-11-22 | F3-01 | Agente | F3 7 % · Global 18 % | `postgresql/init/01-schema.sql` crea el esquema `catalog` y `02-catalogs.sql` los 4 catálogos, con la restricción de dos letras en `original_language`. Aplicados en un PostgreSQL 19.0 desechable: cargan sus 4 CSV (72 filas) y rechazan claves repetidas y códigos de idioma mal formados |
| 2026-11-22 | F2 | Agente | F2 100 % · Global 18 % | Fase terminada. Revisión desde cero: `docker compose config` valida, `volumes-init` termina con 0, `metadata-db` queda sano en 32 s con sus dos bases, ningún secreto fuera de `.env.example`. `docker compose up --wait` sin nombrar servicio devuelve error al terminar un job one-shot; anotado en el diseño (§40) |
| 2026-11-22 | F2-09 | Agente | F2 100 % · Global 18 % | Sano en 35 s con PostgreSQL 19.0. Bases `airflow` y `superset`, cada una de su cuenta; desde otro contenedor de la red cada cuenta entra solo en la suya y se rechaza una contraseña errónea. Al reiniciar no repite la inicialización y conserva las bases |
| 2026-11-22 | F2-08 | Agente | F2 89 % · Global 17 % | Servicio `metadata-db` (`postgres:19.0`, 512 MB, sin puertos) y `metadata-db/init/01-create-databases.sh`, que crea las cuentas `airflow` y `superset` con su base cada una y retira a PUBLIC la conexión; contraseñas desde `.env`. Healthcheck `pg_isready` por TCP |
| 2026-11-22 | F2-07 | Agente | F2 78 % · Global 17 % | Tras `volumes-init`, cada uno de los cinco directorios tiene el UID:GID de su servicio y ese usuario puede escribir en él (`stat` y `test -w` desde un contenedor con ese usuario). Probado solo en Docker Desktop sobre Windows |
| 2026-11-22 | F2-06 | Agente | F2 67 % · Global 16 % | `docker compose config` valida el Compose sin errores, con `.env` y sin él (valores por defecto) |
| 2026-11-22 | F2-05 | Agente | F2 56 % · Global 16 % | Job `volumes-init` en el Compose: imagen de RustFS como root, `chown` de los cinco directorios de la sección 45.2 y límite de 64 MB. Ejecutado dos veces con `docker compose up`: termina con código 0, sin política de reinicio, y no deja cambios en Git |
| 2026-11-22 | F2-04 | Agente | F2 44 % · Global 15 % | Los ocho puertos del host, en el campo de extensión `x-host-ports` del Compose, ligados a `127.0.0.1` y con un ancla por servicio (`*ports-<servicio>`) que cada servicio usará al añadirse. Comprobado con servicios de prueba fuera del repositorio: toman los valores de `.env`, los valores por defecto sin él y un cambio de variable |
| 2026-11-22 | F2-03 | Agente | F2 33 % · Global 15 % | `docker-compose.yml` con `name: elastiflix-cdc-lakehouse`, las reglas de la sección 39 en su cabecera y aún sin servicios. `docker compose config` lo valida y el nombre se mantiene al lanzarlo desde otro directorio |
| 2026-11-22 | Plan | Responsable y agente | — | Resuelta la duda de F2-01: `.env.example` puede llevar valores de laboratorio (decisión 66). Se ajustan la definición de terminado y `AGENTS.md` |
| 2026-11-22 | F2-01 y F2-02 | Agente | F2 22 % · Global 14 % | `.env.example` con las 37 variables de las secciones 45.5, 39 y 9.6 del diseño, con secretos de laboratorio generados al azar; `.env` local copiado de él e ignorado por Git. Queda una duda en la sección 6 |
| 2026-11-22 | Plan y documentación | Responsable y agente | — | Superset se entrega vacío: quien usa el laboratorio conecta la base y crea sus gráficos con la guía del diseño §35. Se retiran la validación 13 (F0-22), F10-07, F10-09 a F10-13, F10-18 y F10-19; F0 vuelve a estar terminada. Nuevas: F10-20, F10-21 y F11-13. Se cierra el riesgo R9 |
| 2026-11-22 | Plan y documentación | Responsable y agente | — | Decididos los ocho puntos de la segunda revisión y el arranque del simulador tras un reinicio (decisiones 57 a 65). F0 se reabre con la validación 13 (F0-22), que F10 espera. Nuevas: F0-22, F3-15, F6-42 a F6-45, F9-19, F9-20, F10-19 y F11-12. Se abre el riesgo R9 |
| 2026-11-22 | Plan y documentación | Agente | — | Segunda revisión de coherencia: se corrigen 23 hallazgos. Nuevas: F2-09 y F10-18; F6-37 pasa antes de F6-26. Quedan ocho puntos para decidir |
| 2026-11-22 | Plan | Responsable y agente | — | Decisiones D-8 a D-16 tomadas (vigentes 48 a 56). F6 depende de F1 y F5 y F10 de F8 y F9; `metadata-db` pasa a F2 (F2-08, se retira F9-01) y la comprobación de DuckDB a F10 (F10-17, se retira F8-11). Nuevas: F6-41, F7-35 y F10-16 |
| 2026-11-22 | Plan y documentación | Agente | — | Revisión de coherencia de la documentación: se corrigen los hallazgos que no dependían de una decisión y quedan nueve decisiones abiertas (D-8 a D-16). Ocho actividades nuevas: F5-17 a F5-20, F6-40, F7-34, F9-18 y F10-15 |
| 2026-11-22 | Plan | Responsable y agente | — | Cada fase indica su skill. Se añade F4-07 (consola de RustFS) y se retira F11-10 (arranque en Linux): el laboratorio corre en un solo equipo. Decisiones 41 a 43 |
| 2026-11-22 | Riesgos | Agente | — | Medición de memoria con los 13 servicios a la vez: 7.9 GB de máximo. Se cierra R3; Airflow reparte sus 3 GB en 0.5, 2 y 0.5 |
| 2026-11-22 | F0-15 | Responsable y agentes | — | Validación 11 superada con ajustes al diseño; decisiones 33 y 34. Fase F0 terminada. Se cierra el riesgo R6 |
| 2026-11-22 | Riesgos | Agente | — | Tabla de riesgos separada en abiertos y cerrados; se cierran R1, R2, R4 y R7. Lectura de los 20 CSV con Commons CSV comprobada |
| 2026-11-22 | F0-14 | Agente | — | Validación 10 superada desde terminales de Linux y de Windows; deja cuatro ajustes en el diseño del simulador |
| 2026-11-22 | F1-04 a F1-09 | Responsable, agente y GrokBot | — | Dataset regenerado recibido, validado, cargado en PostgreSQL 19 y confirmado como definitivo. Fase F1 terminada |
| 2026-11-22 | F0-19 a F0-21 | Agente | — | Reconstrucción de Bronze comprobada con las 20 tablas; leyenda del linaje corregida y diagramas de arquitectura y de arranque regenerados |
| 2026-11-22 | F0-16 y F0-17 | Responsable y agente | — | Validación 12 superada con los dos gestores de autenticación; se elige el de Flask AppBuilder |
| 2026-11-22 | F0-12, F0-13 y F0-18 | Responsable y agente | — | Decisiones tomadas: reconstruir Bronze, `updated_at` como primer origen de `effective_from` y una sola clave de RustFS. Diseño en Revisión 6 |
| 2026-11-22 | F1-01 a F1-03 | Agente y GrokBot | — | Primera versión del dataset generada y validada; se pidió regenerarla |
| 2026-11-22 | F0-01 a F0-11 | Agente | — | Diseño en Revisión 5; validaciones 1 a 9, de volumen y de Silver ejecutadas |

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
| R5 | El trabajo generado por un agente funciona a medias y se marca como hecho | Aplicar la definición de terminado y las actividades «Comprobar» | Desmarcar la actividad y anotarla en la sección 6 | Una comprobación posterior falla |
| R8 | Una corrida del DAG lee Bronze a medio reconstruir y cierra versiones de filas que siguen existiendo | Pausar el DAG antes de reconstruir, como pide el procedimiento | Restaurar Silver al snapshot anterior de Iceberg | El DAG corre mientras `flink-cdc-submit` está repitiendo el snapshot |

### Riesgos cerrados

| # | Riesgo | Fecha de cierre | Por qué se cerró |
|---|---|---|---|
| R1 | La consola Lanterna no funciona a través de `docker compose attach` | 2026-11-22 | La validación 10 pasó desde una terminal de Linux y otra de Windows (F0-14) |
| R2 | El dataset regenerado llega tarde o no cumple | 2026-11-22 | El dataset regenerado se recibió, se validó y quedó como definitivo (F1-04 a F1-09) |
| R3 | Todo el stack junto no cabe en la memoria prevista | 2026-11-22 | Los 13 servicios corrieron a la vez con sus límites: 7.9 GB de máximo bajo carga, sin ningún contenedor detenido por memoria. F11-09 repetirá la medición con el laboratorio construido |
| R4 | Una decisión abierta de F0 frena una fase del camino más largo | 2026-11-22 | No queda ninguna decisión abierta |
| R6 | DuckDB JDBC no adjunta el catálogo o no lee Bronze desde Java 25 | 2026-11-22 | La validación 11 pasó: adjunta el catálogo, lee `bronze.movie` y detecta los cambios (F0-15) |
| R7 | El lector CSV del simulador no interpreta bien las celdas con comas, comillas y saltos de línea | 2026-11-22 | Apache Commons CSV 1.14.1 lee los 20 CSV desde Java 25 con el mismo contenido, celda por celda, que una lectura de referencia |
| R9 | La importación de la base y los dashboards en Superset no funciona como está diseñada | 2026-11-22 | La importación se retiró del diseño: los dashboards los crea quien usa el laboratorio |
