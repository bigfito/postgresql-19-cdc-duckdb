# 🗓️ Plan de trabajo del laboratorio ElastiFlix

Este documento es el **único plan de actividades** del laboratorio, de principio a fin. Dice qué hay que hacer y en qué orden. El cómo está en el diseño:

- [LAB-DESIGN.md](../lab-design/LAB-DESIGN.md): el diseño vigente. Cada actividad cita la sección que la explica.
- [DECISIONS-AND-VALIDATIONS.md](../lab-design/DECISIONS-AND-VALIDATIONS.md): las decisiones y las validaciones.

El plan no lleva fechas ni estimaciones de duración: no hay una fecha comprometida. El avance se mide en actividades terminadas.

## 1. Tablero de avance

**Estado global: 🟢 Verde.** No hay bloqueos, defectos ni dudas abiertas: la sección 6 está vacía.

<!-- tablero:inicio -->
| Fase | Nombre | Actividades | Hechas | Avance | Estado |
|---|---|---:|---:|---:|---|
| F0 | Diseño y validaciones previas | 21 | 21 | 100 % | ✅ Terminada |
| F1 | Dataset de entrada | 9 | 9 | 100 % | ✅ Terminada |
| F2 | Base del proyecto | 9 | 9 | 100 % | ✅ Terminada |
| F3 | PostgreSQL operacional | 15 | 15 | 100 % | ✅ Terminada |
| F4 | Almacenamiento y catálogo | 7 | 7 | 100 % | ✅ Terminada |
| F5 | Flink CDC hacia Bronze | 20 | 20 | 100 % | ✅ Terminada |
| F6 | Event Simulator | 45 | 45 | 100 % | ✅ Terminada |
| F7 | Spark y capa Silver | 35 | 35 | 100 % | ✅ Terminada |
| F8 | Capa Gold | 10 | 10 | 100 % | ✅ Terminada |
| F9 | Orquestación con Airflow | 19 | 19 | 100 % | ✅ Terminada |
| F10 | DuckDB y Superset | 13 | 13 | 100 % | ✅ Terminada |
| F11 | Integración de extremo a extremo | 12 | 12 | 100 % | ✅ Terminada |
| F12 | Documentación y cierre | 7 | 6 | 86 % | 🔄 En curso |
| | **Global** | **222** | **221** | **99 %** | 🔄 En curso |

Actualizado el 2026-11-23.
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

![Dependencias entre las 13 fases del plan, de F0 a F12: en la columna central, de arriba abajo, el camino más largo (F2, F3, F5, F7, F8, F9, F10, F11 y F12); a los lados, F0, que no lleva flechas, y F1, F4 y F6 con las fases que dependen de ellas](../lab-design/diagrams/plan-phases.svg)

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

- [x] **F4-01** Añadir el servicio `rustfs` con su healthcheck. _(diseño §15)_
- [x] **F4-02** Añadir el job `rustfs-init` que crea el bucket `warehouse`. _(diseño §15)_
- [x] **F4-03** Añadir el servicio `iceberg-rest` con su catálogo guardado en `iceberg/data/`. _(diseño §16)_
- [x] **F4-04** Añadir el job `iceberg-init` que crea los tres namespaces. _(diseño §16)_
- [x] **F4-05** Comprobar que el bucket y los namespaces existen. _(diseño §15 y §16)_
- [x] **F4-06** Comprobar que los namespaces siguen ahí tras recrear `iceberg-rest`. _(diseño §16)_
- [x] **F4-07** Comprobar que se entra a la consola web de RustFS con la clave del servicio. _(diseño §45.4)_

### F5 · Flink CDC hacia Bronze

- **Objetivo:** Replicar en Bronze, de forma continua, cada cambio de PostgreSQL.
- **Depende de:** F3, F4 y la actividad F0-12
- **Skill:** `/solution-architect`
- **Terminada cuando:** Las 20 tablas están en Bronze, reflejan INSERT, UPDATE y DELETE, y el pipeline se reanuda al repetir `docker compose up` tras reiniciar Flink.

- [x] **F5-01** Escribir `flink/Dockerfile` con Flink CDC y sus JAR. _(diseño §14)_
- [x] **F5-02** Escribir la configuración de Flink: checkpoint de 30 s y checkpoints retenidos. _(diseño §14)_
- [x] **F5-03** Escribir el pipeline `flink/jobs/postgres-to-bronze.yaml`. _(diseño §14)_
- [x] **F5-04** Añadir `flink-jobmanager` al Compose. _(diseño §39)_
- [x] **F5-05** Añadir `flink-taskmanager` al Compose. _(diseño §39)_
- [x] **F5-06** Escribir el script de envío: no enviar si el job ya está en ejecución. _(diseño §14)_
- [x] **F5-07** Escribir el script de envío: reanudar desde el último checkpoint. _(diseño §14)_
- [x] **F5-08** Escribir el script de envío: detenerse con error si no hay checkpoint y Bronze ya tiene tablas. _(diseño §14)_
- [x] **F5-17** Escribir el script de envío: generar el YAML con la contraseña de `.env`. _(diseño §14)_
- [x] **F5-18** Escribir el script de envío: esperar a que el job esté en `RUNNING` antes de terminar. _(diseño §14)_
- [x] **F5-09** Añadir el job `flink-cdc-submit` al Compose. _(diseño §39)_
- [x] **F5-10** Comprobar que las 20 tablas llegan a Bronze. _(diseño §17)_
- [x] **F5-11** Comprobar un INSERT en Bronze. _(diseño §17)_
- [x] **F5-12** Comprobar un UPDATE en Bronze. _(diseño §17)_
- [x] **F5-13** Comprobar un DELETE en Bronze. _(diseño §17)_
- [x] **F5-14** Comprobar que repetir `docker compose up` no crea un segundo job. _(diseño §14)_
- [x] **F5-15** Comprobar que, tras reiniciar el JobManager, repetir `docker compose up` reanuda el pipeline desde su checkpoint. _(diseño §14)_
- [x] **F5-19** Comprobar que el script de envío se detiene sin borrar nada si no hay checkpoint y Bronze ya tiene tablas. _(diseño §14)_
- [x] **F5-16** Escribir el script que elimina las tablas Bronze para reconstruirlas. _(diseño §38)_
- [x] **F5-20** Comprobar la reconstrucción de Bronze con el script de borrado. _(diseño §38)_

### F6 · Event Simulator

- **Objetivo:** Tener el simulador Java 25 generando transacciones reales, con su interfaz de consola.
- **Depende de:** F1, F5 y las actividades F0-14 y F0-15
- **Skill:** `/java-developer`; `/solution-architect` para el Dockerfile y el Compose
- **Terminada cuando:** El simulador cumple los requisitos RF-01 a RF-13 y su interfaz se abre con `docker compose attach`.

- [x] **F6-01** Crear el proyecto Maven con sus dependencias. _(diseño §9.8)_
- [x] **F6-02** Leer la configuración desde variables de entorno. _(diseño §9.6)_
- [x] **F6-03** Cargar los 20 CSV en memoria. _(RF-01)_
- [x] **F6-04** Conectar con PostgreSQL usando `elastiflix_app`. _(diseño §45.3)_
- [x] **F6-05** Dar de alta una película en una sola transacción. _(RF-02)_
- [x] **F6-06** Insertar catálogos y entidades la primera vez que se necesitan. _(diseño §9.5)_
- [x] **F6-42** Al arrancar, leer de PostgreSQL lo ya insertado y continuar con la primera película pendiente. _(RF-13 y diseño §9.5)_
- [x] **F6-07** Implementar el UPDATE descriptivo. _(RF-03)_
- [x] **F6-08** Implementar el UPDATE de medidas. _(RF-03)_
- [x] **F6-09** Implementar el UPDATE de relaciones, que actualiza también `updated_at` de la película. _(RF-03 y diseño §9.5)_
- [x] **F6-41** Implementar el UPDATE de catálogo: renombrar una colección o una keyword con el sufijo `(rev N)`. _(RF-03 y diseño §9.5)_
- [x] **F6-10** Implementar el DELETE de una película. _(RF-03)_
- [x] **F6-11** Implementar la reinserción de una película borrada. _(RF-03)_
- [x] **F6-12** Elegir la siguiente operación según los pesos y la semilla. _(RF-04 y RF-05)_
- [x] **F6-43** Elegir el tipo de UPDATE con la semilla, entre los que la película admite. _(diseño §9.5)_
- [x] **F6-13** Implementar el modo continuo, con la reinserción automática cuando ya no quedan películas pendientes. _(diseño §9.5)_
- [x] **F6-14** Ante un dato inconsistente: revertir, registrar y continuar. _(RF-12)_
- [x] **F6-15** Registrar cada transacción, cada cambio de configuración y cada operación manual, también en `/tmp/simulator.log`. _(RF-11 y diseño §9.8)_
- [x] **F6-16** Implementar el modo de líneas, que es como arranca el simulador. _(RF-10 y diseño §9.4)_
- [x] **F6-17** Dibujar la cabecera de la pantalla. _(diseño §9.3)_
- [x] **F6-18** Dibujar la zona de avance. _(diseño §9.3)_
- [x] **F6-19** Dibujar la zona de operaciones. _(diseño §9.3)_
- [x] **F6-20** Dibujar la lista de últimas transacciones. _(diseño §9.3)_
- [x] **F6-21** Dibujar la zona de detalle. _(diseño §9.3)_
- [x] **F6-33** Abrir la interfaz con la primera tecla y cerrarla con `Q`. _(diseño §9.4)_
- [x] **F6-34** Atrapar `Ctrl-C` para que no detenga el simulador. _(diseño §9.8)_
- [x] **F6-35** Repintar la pantalla completa cada 2 segundos y al cambiar de tamaño. _(diseño §9.8)_
- [x] **F6-40** Mostrar un aviso cuando la terminal mida menos de 100×30. _(diseño §9.2)_
- [x] **F6-22** Implementar pausar y reanudar. _(RF-07)_
- [x] **F6-23** Implementar el cambio de velocidad. _(RF-07)_
- [x] **F6-24** Implementar el diálogo de pesos. _(RF-07)_
- [x] **F6-25** Implementar el diálogo de operación manual. _(RF-08)_
- [x] **F6-37** Abrir DuckDB en un hilo propio, con hilos y memoria limitados, y reabrirlo si una consulta falla. _(diseño §9.8)_
- [x] **F6-26** Implementar el seguimiento del cambio hasta Bronze, con el instante de referencia truncado. _(RF-09 y diseño §9.3)_
- [x] **F6-38** Marcar como demorada la transacción que no llega a Bronze en 120 segundos. _(diseño §9.3)_
- [x] **F6-27** Escribir pruebas unitarias de la lectura de CSV. _(diseño §9.1)_
- [x] **F6-28** Escribir pruebas unitarias de la selección de operaciones. _(RF-05)_
- [x] **F6-29** Escribir `java-simulator/Dockerfile` con el usuario `simulator` y las opciones de la JVM. _(diseño §9.8 y §45.2)_
- [x] **F6-39** Instalar las extensiones de DuckDB durante el build de la imagen. _(diseño §34)_
- [x] **F6-30** Añadir `java-simulator` al Compose, con `tty` y `stdin_open`, después de `flink-cdc-submit`. _(diseño §9.8 y §40)_
- [x] **F6-36** Limitar el tamaño del log del servicio en el Compose. _(diseño §9.8)_
- [x] **F6-44** Volver el laboratorio a cero antes de las comprobaciones del simulador. _(diseño §39)_
- [x] **F6-31** Comprobar la interfaz con `docker compose attach java-simulator`. _(diseño §9.8)_
- [x] **F6-32** Comprobar que la misma semilla repite la misma secuencia. _(RF-05)_
- [x] **F6-45** Comprobar que, tras detener y arrancar el contenedor, el simulador continúa sin repetir altas. _(RF-13)_

### F7 · Spark y capa Silver

- **Objetivo:** Construir el modelo dimensional con historial a partir de Bronze.
- **Depende de:** F5 y la actividad F0-13
- **Skill:** `/python-developer`; `/solution-architect` para el Dockerfile, la configuración de Spark y el Compose
- **Terminada cuando:** Silver tiene sus 14 dimensiones, 2 hechos y 6 bridges, y una corrida sin cambios no escribe nada.

- [x] **F7-01** Escribir `pyspark/Dockerfile` con Iceberg y Python 3.12. _(diseño §18)_
- [x] **F7-02** Escribir `pyspark/conf/spark-defaults.conf`. _(validaciones, parte 2)_
- [x] **F7-03** Añadir `spark-master` al Compose. _(diseño §39)_
- [x] **F7-04** Añadir `spark-worker` al Compose. _(diseño §39)_
- [x] **F7-05** Crear los seis archivos de referencia en `pyspark/reference/`. _(diseño §24)_
- [x] **F7-06** Crear el esqueleto de `bronze_to_silver.py`. _(diseño §19)_
- [x] **F7-07** Cargar `dim_date`. _(diseño §26)_
- [x] **F7-08** Crear las filas especiales 0 y -1 de cada dimensión. _(diseño §30)_
- [x] **F7-09** Cargar `dim_original_language`. _(diseño §24)_
- [x] **F7-10** Cargar `dim_status`. _(diseño §24)_
- [x] **F7-11** Cargar `dim_rating`. _(diseño §24)_
- [x] **F7-12** Cargar `dim_genre`. _(diseño §25)_
- [x] **F7-13** Cargar `dim_person`. _(diseño §25)_
- [x] **F7-14** Cargar `dim_production_company`. _(diseño §25)_
- [x] **F7-15** Cargar `dim_production_country`. _(diseño §25)_
- [x] **F7-16** Cargar `dim_spoken_language`. _(diseño §25)_
- [x] **F7-17** Cargar `dim_enrichment_field`. _(diseño §29)_
- [x] **F7-18** Cargar `dim_enrichment_code`. _(diseño §29)_
- [x] **F7-19** Cargar `dim_movie` con SCD2. _(diseño §21 y §22)_
- [x] **F7-20** Cargar `dim_collection` con SCD2. _(diseño §23)_
- [x] **F7-21** Cargar `dim_keyword` con SCD2. _(diseño §25)_
- [x] **F7-22** Cargar `bridge_movie_genre`. _(diseño §28)_
- [x] **F7-23** Cargar `bridge_movie_keyword`. _(diseño §28)_
- [x] **F7-24** Cargar `bridge_movie_cast`. _(diseño §28)_
- [x] **F7-25** Cargar `bridge_movie_production_company`. _(diseño §28)_
- [x] **F7-26** Cargar `bridge_movie_production_country`. _(diseño §28)_
- [x] **F7-27** Cargar `bridge_movie_spoken_language`. _(diseño §28)_
- [x] **F7-28** Cargar `fact_movie_snapshot`, con `record_hash` sobre las claves de negocio. _(diseño §27)_
- [x] **F7-29** Cargar `fact_movie_enrichment`. _(diseño §29)_
- [x] **F7-30** Reparar las referencias que quedaron con clave 0. _(diseño §19 y §30)_
- [x] **F7-31** Comprobar que una segunda corrida sin cambios no escribe nada. _(diseño §19)_
- [x] **F7-32** Comprobar un INSERT, un UPDATE, un DELETE y una reinserción en Silver. _(diseño §31)_
- [x] **F7-33** Cerrar las versiones vigentes cuya clave ya no aparece en Bronze. _(diseño §19 y §38)_
- [x] **F7-35** Comprobar que renombrar una colección o una keyword crea su versión nueva sin crear snapshot. _(diseño §31)_
- [x] **F7-34** Comprobar que un tombstone sin versión previa no crea versión ni snapshot. _(diseño §31)_

### F8 · Capa Gold

- **Objetivo:** Materializar los productos analíticos que consultará Superset.
- **Depende de:** F7
- **Skill:** `/python-developer`
- **Terminada cuando:** Los siete productos Gold existen y se reemplazan completos en cada corrida.

- [x] **F8-01** Definir las columnas y los indicadores de los siete productos. _(diseño §33)_
- [x] **F8-02** Crear el esqueleto de `silver_to_gold.py`. _(diseño §32)_
- [x] **F8-03** Crear `gold.movie_current_overview`. _(diseño §33)_
- [x] **F8-04** Crear `gold.genre_performance`. _(diseño §33)_
- [x] **F8-05** Crear `gold.collection_performance`. _(diseño §33)_
- [x] **F8-06** Crear `gold.financial_performance`. _(diseño §33)_
- [x] **F8-07** Crear `gold.release_trends`. _(diseño §33)_
- [x] **F8-08** Crear `gold.cast_analysis`. _(diseño §33)_
- [x] **F8-09** Crear `gold.data_quality_coverage`. _(diseño §33)_
- [x] **F8-10** Comprobar que cada corrida reemplaza las tablas completas. _(diseño §32)_

### F9 · Orquestación con Airflow

- **Objetivo:** Ejecutar y validar los jobs de Silver y Gold desde un DAG.
- **Depende de:** F8 y las actividades F0-16 y F0-17
- **Skill:** `/python-developer`; `/solution-architect` para el Dockerfile y el Compose
- **Terminada cuando:** Una corrida del DAG `elastiflix_medallion` termina en `success` y deja Silver y Gold actualizados.

- [x] **F9-02** Escribir `airflow/Dockerfile` con Java, PySpark y los JAR de Iceberg. _(diseño §18)_
- [x] **F9-03** Añadir el job `airflow-init`. _(diseño §39)_
- [x] **F9-04** Añadir `airflow-apiserver` al Compose. _(diseño §18)_
- [x] **F9-05** Añadir `airflow-scheduler` al Compose. _(diseño §18)_
- [x] **F9-06** Añadir `airflow-dag-processor` al Compose. _(diseño §18)_
- [x] **F9-07** Crear el administrador de Airflow con `airflow users create`. _(diseño §45.4)_
- [x] **F9-08** Escribir el job `iceberg_maintenance.py`. _(diseño §38)_
- [x] **F9-09** Crear el DAG `elastiflix_medallion`. _(diseño §18)_
- [x] **F9-19** Programar el DAG cada 10 minutos, activo desde que se crea, sin `catchup` y con una sola corrida a la vez. _(diseño §18)_
- [x] **F9-10** Escribir `validate_bronze.py`, que comprueba las tablas y el job de Flink, y añadir su tarea. _(diseño §18)_
- [x] **F9-11** Añadir la tarea `bronze_to_silver`, que pasa `dag_run.run_after` al job. _(diseño §18 y §21)_
- [x] **F9-12** Escribir `validate_silver.py` y añadir la tarea `validate_silver`. _(diseño §18)_
- [x] **F9-13** Añadir la tarea `silver_to_gold`. _(diseño §18)_
- [x] **F9-14** Escribir `validate_gold.py` y añadir la tarea `validate_gold`. _(diseño §18)_
- [x] **F9-15** Añadir la tarea `iceberg_maintenance`, que corre siempre al final (`trigger_rule = all_done`). _(diseño §18 y §38)_
- [x] **F9-16** Comprobar una corrida completa del DAG. _(diseño §18)_
- [x] **F9-17** Comprobar que una validación fallida detiene el DAG, salvo el mantenimiento. _(diseño §18)_
- [x] **F9-18** Comprobar la reconstrucción de Bronze con el DAG pausado y reanudado después. _(diseño §38, decisión 39)_
- [x] **F9-20** Comprobar que el DAG empieza a correr solo, sin activarlo a mano. _(diseño §18)_

### F10 · DuckDB y Superset

- **Objetivo:** Dejar Superset listo para que quien use el laboratorio conecte Gold y cree sus visualizaciones.
- **Depende de:** F8 y F9
- **Skill:** `/python-developer` para la configuración de Superset; `/solution-architect` para el SQL de DuckDB, el Dockerfile y el Compose
- **Terminada cuando:** Siguiendo la guía del diseño, se conecta la base DuckDB, se crea un dataset sobre un producto Gold y un gráfico muestra sus datos.

- [x] **F10-01** Escribir `duckdb/init/attach_lakehouse.sql` y `duckdb/init/gold_views.sql`. El primero existe desde la fase F6. _(diseño §34)_
- [x] **F10-02** Escribir `duckdb/Dockerfile` para la línea de comandos opcional. _(diseño §34)_
- [x] **F10-15** Añadir el servicio `duckdb` al Compose, bajo el perfil `tools`. _(diseño §34 y §39)_
- [x] **F10-03** Escribir `superset/Dockerfile` con DuckDB y sus extensiones. _(diseño §35)_
- [x] **F10-04** Escribir `superset_config.py` con el hook de conexión, que crea solo las vistas de las tablas Gold que existen. _(diseño §35)_
- [x] **F10-05** Añadir el job `superset-init`: migrar la base de metadatos. _(diseño §39)_
- [x] **F10-06** Añadir a `superset-init` la creación del administrador. _(diseño §45.4)_
- [x] **F10-08** Añadir el servicio `superset` al Compose. _(diseño §39)_
- [x] **F10-16** Comprobar que Superset abre conexiones sin errores antes de la primera corrida del DAG y que, después, el hook crea las vistas de las tablas Gold que existen. _(diseño §34 y §35)_
- [x] **F10-17** Comprobar que DuckDB lee los siete productos Gold. _(diseño §34)_
- [x] **F10-20** Seguir la guía de Superset paso a paso: conectar la base, crear un dataset sobre un producto Gold y un gráfico. _(diseño §35)_
- [x] **F10-21** Corregir la guía con lo que difiera en la interfaz real. _(diseño §35)_
- [x] **F10-14** Comprobar que el gráfico refleja un cambio tras la siguiente corrida del DAG. _(diseño §35)_

### F11 · Integración de extremo a extremo

- **Objetivo:** Comprobar que el laboratorio completo arranca con un comando y que un cambio recorre todas las capas.
- **Depende de:** F1, F5, F6, F9 y F10
- **Skill:** `/solution-architect`
- **Terminada cuando:** Se cumple el criterio de éxito de la sección 44 del diseño y no queda ningún defecto abierto.

- [x] **F11-01** Completar los healthchecks y las dependencias entre servicios. _(diseño §40)_
- [x] **F11-02** Comprobar que todos los servicios declaran su límite de memoria. _(diseño §39)_
- [x] **F11-12** Volver el laboratorio a cero con el procedimiento del diseño. _(diseño §39)_
- [x] **F11-03** Levantar todo desde cero con `docker compose up -d --build`. _(diseño §39)_
- [x] **F11-13** Conectar la base y crear un gráfico en Superset con la guía, para seguir los cambios. _(diseño §35)_
- [x] **F11-04** Seguir un INSERT desde el simulador hasta Superset. _(diseño §42)_
- [x] **F11-05** Seguir un UPDATE desde el simulador hasta Superset. _(diseño §42)_
- [x] **F11-06** Seguir un DELETE desde el simulador hasta Superset. _(diseño §42)_
- [x] **F11-07** Repetir `docker compose up` y comprobar que nada se duplica. _(diseño §40)_
- [x] **F11-08** Detener y volver a levantar el laboratorio, y comprobar que el pipeline y el simulador retoman. _(diseño §9.5, §14 y §39)_
- [x] **F11-09** Medir la memoria usada con todo en marcha. _(diseño §39)_
- [x] **F11-11** Anotar los defectos encontrados y corregirlos. _(sección 6 de este plan)_

### F12 · Documentación y cierre

- **Objetivo:** Dejar el laboratorio listo para que otra persona lo clone, lo levante y lo entienda.
- **Depende de:** F11
- **Skill:** `/solution-architect`
- **Terminada cuando:** Un clon limpio del repositorio levanta el laboratorio siguiendo solo el README.

- [x] **F12-01** Actualizar el README con las instrucciones reales de ejecución. _(README §8)_
- [x] **F12-02** Escribir la guía de la demostración paso a paso. _(diseño §42)_
- [x] **F12-03** Actualizar el diseño con lo que cambió al implementar. _(diseño)_
- [x] **F12-04** Actualizar los diagramas al estado final. _(diseño §4, §6, §9.3, §12, §18, §35, §36, §40 y §44; plan §3)_
- [x] **F12-05** Cerrar las decisiones que sigan abiertas. _(decisiones, parte 1.3)_
- [x] **F12-06** Verificar el criterio de éxito con un clon limpio. _(diseño §44)_
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
| 2026-11-23 | Documentación | Responsable y agente | — | Wiki para lectores de negocio, fuera de las actividades del plan. Estructura de doce páginas acordada con la persona responsable; escritas las cinco primeras (inicio, el problema, el recorrido de un cambio, bronce, plata y oro, y qué preguntas responde) y la barra lateral, en `wiki/`. Cada página lleva un dibujo sencillo hecho con Archify, que pasa sus comprobaciones y se revisó a la vista. `wiki/publish.sh` las copia al wiki de GitHub, ajustando enlaces e imágenes; se probó en modo de simulación. Todavía no se ha publicado en el wiki, y falta comprobar allí que las imágenes se ven |
| 2026-11-23 | Documentación | Responsable y agente | — | Revisión de coherencia de toda la documentación y de los diez diagramas contra el código, hecha por un revisor independiente: 35 hallazgos (1 de gravedad alta, 11 media y 23 baja), todos corregidos. El grave estaba en el diseño: decía que, si falla `validate_gold`, Superset sigue mostrando la carga anterior, cuando Gold ya se sobrescribió. Cuatro correcciones tocan código: el simulador deja de recibir `AWS_REGION`, que no usaba; el tablero ya no muestra 100 % mientras falte una actividad; el generador del dataset lista sus validaciones en orden; y el diagrama de linaje corrige de dónde salen los conteos del hecho |
| 2026-11-23 | F12-06 | Agente | F12 86 % · Global 100 % | Criterio de éxito comprobado desde un clon limpio. El árbol de trabajo se clonó con git clone en otra carpeta y otra unidad, a partir de un commit temporal que no tocó main y ya está borrado, y se siguió solo el README. Los 191 archivos se extrajeron con LF, con core.autocrlf=true en el equipo. Construir las cinco imágenes sin caché: 2 min 37 s, código 0. docker compose up -d --build: 102 s, código 0, 13 servicios en marcha y seis jobs en Exited (0). La primera corrida del DAG terminó bien a los 6 minutos. Seguidos antes y después de la segunda corrida: el INSERT de la película 14616, el UPDATE de medidas de la 431 y el DELETE de la 652 llegaron a Superset. Las seis direcciones del README responden, la línea de comandos de DuckDB lee Gold, repetir el comando no recrea nada y el laboratorio no deja archivos sin ignorar. Corregido el README: el comando construye cinco imágenes, no seis. Límites: mismo equipo, imágenes base ya descargadas, y la base y el dataset de Superset registrados por su API. Después el laboratorio principal se volvió a cero con los comandos del README y arrancó en 92 s |
| 2026-11-23 | F12-05 | Agente | F12 71 % · Global 99 % | Las siete filas abiertas de la sección 6 se cerraron con la persona responsable, que eligió en todas la opción recomendada. Decisiones 68 a 73: las vistas de memory.main se mantienen; rustfs/data se retira del repositorio, con sus dos líneas de .gitignore; flink-taskmanager sigue sin reinicio automático; y se aceptan como están las columnas de Gold, la regla de reanudación RF-13 y la ausencia de pruebas versionadas para los jobs. El fallo intermitente de initdb deja de seguirse como defecto y pasa al riesgo R10. La parte 1.3 del documento de decisiones no tenía ninguna abierta. Ningún cambio toca cómo se ejecuta el laboratorio: en el Compose solo cambian dos comentarios |
| 2026-11-23 | F12-04 | Agente | F12 57 % · Global 99 % | Los diez diagramas repasados contra lo implementado, leyendo los textos de cada fuente .json. Siete siguen siendo correctos, entre ellos el orden de arranque, cuyas 16 flechas coinciden con los depends_on del Compose. Tres se actualizaron con Archify y pasan sus comprobaciones: el del DAG gana la tarea mark_run_failed, en un carril propio, con su flecha y su entrada en la leyenda; el de la ruta de consumo dice memory.main en vez de main; y el de fases cambia la tarjeta de fases terminadas, que hablaba de F0 y F1, por una que remite al tablero del plan. El del DAG se revisó a la vista. En los otros dos el cambio está en una tarjeta de la página interactiva, así que su .svg no cambia. El boceto de la consola del simulador no se comparó con la consola real |
| 2026-11-23 | F12-03 | Agente | F12 43 % · Global 98 % | Diseño repasado contra lo implementado. Las fases F5 a F11 ya lo habían ido actualizando, cada una con su apartado «Cómo está implementado», así que quedaban pocos puntos: la sección 3.2 gana la imagen base debian:trixie-20261104-slim de la línea de comandos de DuckDB, comprobada en Docker Hub para amd64 y arm64, y nombra los seis jobs one-shot; el árbol de la sección 7 incluye duckdb/entrypoint.sh; y la cabecera dice que el laboratorio ya está implementado. Comparados uno a uno: las imágenes base con los seis Dockerfile y el Compose, y el árbol de directorios con los archivos versionados. No se reescribió el tiempo futuro del documento |
| 2026-11-23 | F12-02 | Agente | F12 29 % · Global 98 % | Guía de la demostración escrita en la sección 42 del diseño: siete bloques que recorren los quince pasos del flujo, con el comando de cada uno y lo que se debe ver. Todos los comandos se ejecutaron tal cual contra el laboratorio. El bloque de seguir un cambio se probó de principio a fin con un cambio de título real del simulador, el de la película 174288: PostgreSQL y Bronze lo tenían al momento; tras la corrida siguiente del DAG, Silver quedó con la versión 1 cerrada en el instante del cambio y la versión 2 vigente, y Gold y Superset con el título nuevo. Con eso queda seguido también el UPDATE descriptivo que faltaba en F11. No se probó la tecla M de la consola en esta fase; se comprobó en F6 |
| 2026-11-23 | F12-01 | Agente | F12 14 % · Global 97 % | README §8 reescrito con las instrucciones reales: primer arranque en dos pasos, con la variante de PowerShell para copiar .env; qué esperar y cuándo; cómo ver el estado; una tabla de direcciones y cuentas de las ocho entradas al laboratorio; cómo detener, reanudar y volver a cero, con los comandos; y qué mirar si algo no arranca. Las seis direcciones web responden 200 y la cuenta elastiflix_app entra a PostgreSQL. Los tiempos son los medidos en F11; el de la primera construcción de las imágenes se mide en F12-06, que además sigue este README desde un clon limpio |
| 2026-11-23 | F11 | Agente | F11 100 % · Global 97 % | Fase terminada. El criterio de éxito del diseño (§44) se cumple en este equipo: con el laboratorio vuelto a cero, `docker compose up -d --build` lo levanta en 97 s y un INSERT, un UPDATE y un DELETE del simulador se siguieron por PostgreSQL, Bronze, Silver y Gold hasta un gráfico de Superset creado con la guía. También se comprobó que repetir el comando no duplica nada y que, tras detener y levantar, el pipeline y el simulador retoman con PostgreSQL y Bronze iguales en las 20 tablas. Dos defectos encontrados y corregidos (F11-11). Del criterio de cierre queda una salvedad: el fallo intermitente de initdb de la sección 6 sigue en observación; no apareció en esta fase. Sin probar: detener el laboratorio en mitad de una corrida del DAG, la memoria con el dataset completo cargado, y el arranque desde un clon limpio, que es F12-06 |
| 2026-11-23 | F11-11 | Agente | F11 100 % · Global 97 % | Defectos encontrados en la fase, los dos corregidos. Uno: a flink-jobmanager le faltaba la dependencia de postgresql que dibuja el diseño (§40); añadida en F11-01 y probada en el arranque desde cero. Dos: el mantenimiento de Iceberg dejaba en el log tres avisos con su traza por tabla y corrida, porque nombraba las tablas sin el catálogo; ahora las nombra lake.<capa>.<tabla>, y la corrida siguiente del DAG terminó en success con 49 tablas mantenidas y ningún aviso. Revisados los logs de los 13 servicios tras el reinicio: ningún error propio, ningún contenedor detenido por memoria ni reiniciado. Queda ruido conocido que no es defecto: el catálogo anota como error los 409 de los namespaces que ya existen y las búsquedas de la tabla de metadatos refs. No apareció el fallo intermitente de initdb de la sección 6, que sigue en observación |
| 2026-11-23 | F11-09 | Agente | F11 92 % · Global 96 % | Memoria medida con todo en marcha durante una corrida completa del DAG (35 muestras en 5 minutos, con el simulador y Flink escribiendo). El laboratorio usó entre 4.71 y 7.41 GiB; los límites suman 15. Máximos: airflow-scheduler 1.87 de 2 GiB, spark-worker 1.79 de 3, flink-taskmanager 1.09 de 2, superset 0.83 de 2, flink-jobmanager 0.50 de 1, airflow-dag-processor 0.46 de 0.5, airflow-apiserver 0.31, spark-master, iceberg-rest, rustfs y java-simulator por debajo de 0.2, y los dos PostgreSQL 0.08. Dos servicios quedan a menos de un 10 % de su límite: airflow-scheduler, ya conocido (R12), y airflow-dag-processor, que es nuevo. Ninguno se detuvo por memoria |
| 2026-11-23 | F11-08 | Agente | F11 83 % · Global 96 % | Laboratorio detenido con docker compose down (7 s) y levantado con docker compose up -d (40 s), con el simulador y Flink trabajando. El pipeline se reanudó solo desde su último checkpoint, el 36, con un job nuevo en RUNNING y el mismo slot de replicación activo. El simulador encontró 2,570 películas presentes, dio 206 por borradas y siguió con la pendiente siguiente, sin repetir altas. Con el simulador en pausa 50 s para poder comparar: PostgreSQL y Bronze coinciden en las 20 tablas, 212,916 filas, y las cuatro últimas transacciones anteriores a la parada están en Bronze. El DAG lanzó su corrida siguiente a su hora y Superset conserva la base, el dataset, el gráfico y el dashboard. Se detuvo entre dos corridas del DAG; pararlo en mitad de una no se probó |
| 2026-11-23 | F11-07 | Agente | F11 75 % · Global 95 % | docker compose up -d repetido con todo en marcha: termina con código 0 en 23 s y no recrea ningún contenedor; los 13 de larga duración conservan su identificador y su hora de arranque. Los seis jobs one-shot vuelven a ejecutarse y terminan con código 0 sin cambiar nada: el bucket y los tres namespaces ya existen, el pipeline ya está en ejecución y no se envía de nuevo, y los administradores de Airflow y de Superset ya existen. Comparado antes y después: un solo job de Flink con el mismo identificador, un slot de replicación activo, una publicación, 20, 22 y 7 tablas en el catálogo, un usuario en cada base de metadatos, un DAG con sus dos corridas, y la base, el dataset, el gráfico y el dashboard de Superset. Lo único que cambia es lo que el simulador siguió insertando |
| 2026-11-23 | F11-06 | Agente | F11 67 % · Global 95 % | DELETE seguido de punta a punta. El simulador borró la película 1282, «Sleeping Enemy», a las 21:31:29 UTC (TX 1121). PostgreSQL: la fila ya no está. Bronze: queda como tombstone, con operación -D. Antes de la corrida, Silver, Gold y Superset la seguían mostrando. Tras la corrida de las 21:36:49: Silver cierra su versión en dim_movie (deja de estar vigente, con fin a las 21:31:29) y añade una foto con is_deleted en fact_movie_snapshot; Gold ya no la tiene y Superset no la devuelve. Repetido con las películas 1119 y 1317 |
| 2026-11-23 | F11-05 | Agente | F11 58 % · Global 95 % | UPDATE seguido de punta a punta. El simulador cambió las medidas de la película 746, «Closed Lilies», a las 21:33:57 UTC (TX 1679): popularidad de 83.513 a 76.012 y votos de 5,582 a 5,826. PostgreSQL y Bronze (operación +U) tenían los valores nuevos al momento. Antes de la corrida, Silver, Gold y Superset mostraban los antiguos. Tras la corrida de las 21:36:49: Silver añade una foto nueva en fact_movie_snapshot, fechada a las 21:33:57, y conserva la anterior; dim_movie no cambia, porque las medidas no son atributos de la dimensión; Gold y Superset muestran 76.012 y 5,826. Repetido con la película 1212. Queda sin seguir un UPDATE descriptivo en esta fase; su versión nueva en dim_movie se comprobó en F7 |
| 2026-11-23 | F11-04 | Agente | F11 50 % · Global 94 % | INSERT seguido de punta a punta. El simulador insertó la película 71001, «Gilded Songs», a las 21:35:54 UTC (TX 2117). PostgreSQL: la fila está en catalog.movie. Bronze: la misma fila con operación +I, a los pocos segundos. La corrida del DAG de las 21:36:49 la llevó a Silver, con su versión 1 vigente en dim_movie desde las 21:35:54 y su foto en fact_movie_snapshot, y a Gold, en movie_current_overview. Superset: antes de la corrida la película no estaba; después, el dataset del gráfico la devuelve y el gráfico pasó de 111 a 1,528 películas |
| 2026-11-23 | F11-13 | Agente | F11 42 % · Global 94 % | Tras la vuelta a cero y la primera corrida del DAG, la guía del diseño (§35) se siguió otra vez en el navegador, ya corregida y sin desviarse de ella: base «ElastiFlix Gold» conectada con duckdb:///:memory:, dataset sobre memory.main.movie_current_overview con sus columnas y tipos, gráfico de barras de COUNT(movie_id) por primary_genre (17 géneros, 111 películas) y dashboard nuevo «ElastiFlix». La sesión del día anterior seguía valiendo tras recrear los metadatos, porque la clave de sesión es la misma |
| 2026-11-23 | F11-03 | Agente | F11 33 % · Global 93 % | docker compose up -d --build desde cero: termina con código 0 en 97 s, con las seis imágenes en caché. Los seis jobs one-shot acaban con código 0 y los 13 servicios quedan en marcha, 12 de ellos sanos y el simulador sin healthcheck. Orden observado, en segundos desde el primer contenedor: postgresql, metadata-db y rustfs a 0; el catálogo a 7; Spark a 9; Flink a 41, cuando postgresql está sano; el pipeline enviado a 57; el simulador a 58; Airflow a 67 y Superset a 90. A los dos minutos: pipeline en RUNNING, 101 películas en PostgreSQL, 20 tablas en Bronze, el DAG activo con su primera corrida en marcha sin que nadie lo activara, y Superset sano y sin bases. No apareció el fallo de initdb de la sección 6 |
| 2026-11-23 | F11-12 | Agente | F11 25 % · Global 93 % | Vuelta a cero con el procedimiento del diseño (§39), paso a paso: docker compose down (8 s, sin contenedores ni red), los seis directorios de datos vaciados conservando su .gitkeep (1 s) y el volumen rustfs-data eliminado con docker volume rm. Las seis imágenes construidas y el .env siguen. El paso 3, levantar de nuevo, es F11-03 y dejó el laboratorio funcionando desde vacío: 0 películas, catálogo sin tablas y Superset sin bases |
| 2026-11-23 | F11-02 | Agente | F11 17 % · Global 92 % | Los 20 servicios del Compose, incluidos los seis jobs one-shot y el opcional duckdb, declaran mem_limit. Los 13 de larga duración suman 15 GiB, lo que dice el diseño (§39). Todos los puertos publicados están en 127.0.0.1 |
| 2026-11-23 | F11-01 | Agente | F11 8 % · Global 92 % | Healthchecks y dependencias revisados contra el orden de arranque del diseño (§40), sobre la configuración que resuelve docker compose config. Los 12 servicios de larga duración con estado o interfaz tienen healthcheck: 11 en el Compose y el de iceberg-rest, que lo trae su imagen. No lo llevan los seis jobs one-shot, que se esperan con service_completed_successfully, ni java-simulator, del que no depende nadie. Las 16 flechas del diagrama existen como depends_on con su condición; faltaba una, de postgresql a Flink, y se añadió a flink-jobmanager. Ningún servicio lleva restart ni container_name. El arranque real con estas dependencias se comprueba en F11-03 |
| 2026-11-23 | F10 | Agente | F10 100 % · Global 91 % | Fase terminada. Su criterio de cierre está comprobado: siguiendo la guía del diseño, en un navegador, se conectó la base DuckDB, se creó un dataset sobre `genre_performance` y un gráfico de barras mostró sus 19 géneros; tras la corrida siguiente del DAG, el gráfico reflejó un cambio hecho en PostgreSQL. Dos hallazgos: en la interfaz el esquema de las vistas se llama `memory.main`, y un dataset físico sobre `lake.gold` sí funciona, al contrario de lo que vio la validación 7; las vistas se mantienen y la duda queda en la sección 6. Para entrar a Superset se usaron las credenciales de ejemplo de `.env.example`, que son las que tiene el `.env` de este equipo. Quedan sin probar: otros tipos de gráfico, los filtros de un dashboard, la consola de DuckDB tecleando en una terminal y las imágenes en `arm64`. El arranque completo desde un clon limpio es de la fase F11 |
| 2026-11-23 | F10-14 | Agente | F10 100 % · Global 91 % | El gráfico refleja los cambios tras la siguiente corrida del DAG. Cambio controlado: el género Western se renombró en PostgreSQL a las 21:01:07 UTC; a los 45 s estaba en Bronze y la corrida de las 21:08 lo llevó a Gold a las 21:10:59. Al recargar el dashboard, sin forzar el refresco, el gráfico «Películas por género» mostró el nombre nuevo con 225 películas (antes 218) y los cambios del simulador en otros 17 géneros; la suma pasó de 19,318 a 19,360. Superset no guarda resultados: no hay caché configurada y la API lo confirma. El género se devolvió a su nombre a las 21:11:47 |
| 2026-11-23 | F10-21 | Agente | F10 92 % · Global 91 % | Guía de la sección 35 del diseño corregida con lo visto en la interfaz de Superset 6.1.0: el formulario de DuckDB es el de MotherDuck y hay que pasar a la cadena SQLAlchemy; el esquema de las vistas se llama memory.main; tras crear el dataset se abre el selector de tipo de gráfico; el eje y la métrica se eligen en la pestaña Simple; y el gráfico se añade a un dashboard nuevo escribiendo su nombre al guardar. De paso se corrigen tres afirmaciones de la sección: el hook ya está comprobado, superset-init ya tolera repetirse, y un dataset físico sobre lake.gold sí funcionó en F10-20 (18 columnas con tipo y gráfico correcto), al contrario que en la validación 7. Las vistas se mantienen; la duda queda en la sección 6 |
| 2026-11-23 | F10-20 | Agente | F10 85 % · Global 91 % | Guía de Superset seguida en el navegador, de principio a fin, entrando como el administrador. Conexión: menú +, Data, Connect database, DuckDB en la lista, enlace a la cadena SQLAlchemy, duckdb:///:memory:, Test connection («Connection looks good!») y Connect («Database connected»). Dataset: genre_performance, con sus 16 columnas y tipos. Gráfico de barras de SUM(movie_count) por genre_name: 19 géneros en 0.29 s; guardado como «Películas por género» y añadido a un dashboard nuevo, «ElastiFlix». SQL Lab lee main.<producto> y lake.gold.<producto>, y rechaza CREATE TABLE y DELETE (DML_NOT_ALLOWED_ERROR). Diferencias con la guía, que corrige F10-21: el esquema se llama memory.main, no main; tras crear el dataset se abre el selector de tipo de gráfico; y el eje y la métrica se eligen en una ventana con pestaña Simple. Sin errores en el log salvo el 404 de /favicon.ico |
| 2026-11-23 | F10-17 | Agente | F10 77 % · Global 90 % | DuckDB lee los siete productos de Gold desde el servicio duckdb del perfil tools. Las filas coinciden con las del snapshot vigente del catálogo, que no cambió durante la lectura: movie_current_overview 6,899, genre_performance 19, collection_performance 1,039, financial_performance 4,067, release_trends 531, cast_analysis 95,050 y data_quality_coverage 41. Tabla y vista devuelven lo mismo; las 124 columnas se leen completas con SUMMARIZE y ninguna viene toda nula; cada producto trae una sola carga (gold_processed_at) |
| 2026-11-23 | F10-16 | Agente | F10 69 % · Global 90 % | El hook, visto desde Superset. Antes de la primera corrida: contra un catálogo REST de prueba con el namespace gold vacío, la conexión abre sin errores, adjunta lake y no crea ninguna vista. Con Gold cargado: test_connection de la API responde OK tres veces seguidas sin registrar nada; y un motor creado por el modelo Database de Superset (NullPool) ve las siete vistas en main y lee 6,899 filas de movie_current_overview. El inspector nombra los esquemas con su catálogo (memory.main, lake.gold). Los únicos errores del log fueron de mi script de prueba (token CSRF sin cookie), ya corregido |
| 2026-11-23 | F10-08 | Agente | F10 62 % · Global 89 % | Servicio `superset` en el Compose, publicado en `127.0.0.1:8088`, con cuatro procesos y 2 GB de límite. Arrancado: sano a los 9 s; `/health` responde 200; la API sin credenciales devuelve 401; con las del administrador se obtiene un token y responde, con 0 bases registradas; una contraseña incorrecta se rechaza. 824 MiB en reposo. Sin errores ni secretos en sus logs. No se inició sesión desde un navegador todavía; llega en F10-20 |
| 2026-11-23 | F10-06 | Agente | F10 54 % · Global 89 % | `superset-init` crea el administrador con `superset fab create-admin`, a partir de `SUPERSET_ADMIN_USER` y `SUPERSET_ADMIN_PASSWORD`, y carga los roles y permisos con `superset init`. Ejecutado dos veces: la primera crea al administrador (33 s) y la segunda detecta con `superset fab list-users` que ya existe y termina igual, con código 0 (23 s). La contraseña queda cifrada con `scrypt` en `ab_user` y no aparece en los logs. No registra ninguna base de datos ni ningún dashboard: 0 y 0 en los metadatos |
| 2026-11-23 | F10-05 | Agente | F10 46 % · Global 88 % | Job `superset-init` en el Compose, con los campos comunes de Superset (imagen, variables y montajes). Ejecutado: `superset db upgrade` aplica las 344 migraciones sobre la base `superset` de `metadata-db` en 17 s y termina con código 0. Repetido sobre la base ya migrada: termina igual, sin aplicar ninguna. Ni la contraseña de la base ni las claves aparecen en sus logs |
| 2026-11-23 | F10-04 | Agente | F10 38 % · Global 88 % | `superset/config/superset_config.py`: la clave de sesión y la URI de los metadatos llegan por el entorno, y un listener del evento `connect` de SQLAlchemy prepara cada conexión de DuckDB: ejecuta `attach_lakehouse.sql` con la clave de RustFS y, de `gold_views.sql`, solo las vistas cuya tabla existe según `information_schema.tables`. Probado dentro de la imagen, fuera de Superset, con 11 comprobaciones correctas: una conexión nueva sin pool trae las siete vistas con sus columnas en 126 a 196 ms; con dos tablas en Gold crea dos vistas y con Gold vacío ninguna, sin fallar; una conexión de otro motor no se toca; y si falta una variable el error dice cuál. Su uso desde Superset se comprueba en F10-16 |
| 2026-11-23 | F10-03 | Agente | F10 31 % · Global 87 % | `superset/Dockerfile` sobre `apache/superset:6.1.0-py312`: añade `duckdb` 1.5.6, `duckdb-engine` 0.17.0 y `psycopg2-binary` 2.9.13 al entorno virtual de la imagen, e instala las extensiones `httpfs`, `iceberg` y `avro` en `/opt/duckdb_extensions`. Construida en 11 s (1.48 GB; la base, 1.26 GB). Comprobado dentro de la imagen, sin red: las tres extensiones cargan con la instalación automática desactivada, SQLAlchemy crea un motor `duckdb`, no hay dependencias en conflicto y corre como `superset` (1000). No se construyó para `arm64` |
| 2026-11-23 | F10-15 | Agente | F10 23 % · Global 87 % | Servicio `duckdb` en el Compose, bajo el perfil `tools`, con `duckdb/init` montado en solo lectura y la clave de RustFS en su entorno. Comprobado: sin el perfil no figura entre los servicios y `docker compose up -d` no lo toca; `docker compose --profile tools run --rm duckdb` lee `lake.gold`, ve las 20 tablas de Bronze y crea las siete vistas con `.read`; no deja contenedores al terminar. La consola se probó pasándole las órdenes por la entrada estándar, no tecleando en una terminal |
| 2026-11-23 | F10-02 | Agente | F10 15 % · Global 86 % | `duckdb/Dockerfile`, `duckdb/entrypoint.sh` y `duckdb/.dockerignore`. La imagen oficial de DuckDB no trae shell, así que su binario se copia a una Debian mínima (`trixie-20261104-slim`); corre como el usuario `duckdb` (10003) y lleva las extensiones `httpfs`, `iceberg` y `avro` instaladas en `/opt/duckdb_extensions`. El script de arranque ejecuta `attach_lakehouse.sql` con las credenciales del entorno antes de abrir la consola. Construida en 11 s (316 MB). Probada contra el laboratorio: lee Gold en 1 s, ve las 20, 22 y 7 tablas de las tres capas, crea las siete vistas con `.read`, y da un error claro si faltan las credenciales o el montaje; la clave no aparece en su salida |
| 2026-11-23 | F10-01 | Agente | F10 8 % · Global 86 % | `duckdb/init/gold_views.sql`, con una vista por producto de Gold en `memory.main`; `attach_lakehouse.sql` existía desde la fase F6. Ejecutado con DuckDB 1.5.6 como lo hará quien lo use, quitando los comentarios y partiendo por punto y coma: crea las siete vistas, cada una con las columnas de su tabla, y las siete devuelven filas. Ningún comentario de los dos archivos lleva punto y coma. De paso se comprobó lo que el diseño daba por pendiente: `information_schema.tables` de DuckDB sí lista las siete tablas de `lake.gold` |
| 2026-11-23 | Plan y documentación | Responsable y agente | — | RustFS se queda con sus datos en el volumen con nombre de Docker (decisión 67). SeaweedFS, evaluado como sustituto y con sus pruebas superadas, no se adopta |
| 2026-11-23 | F9 | Agente | F9 100 % · Global 86 % | Fase terminada. Su criterio de cierre está comprobado: una corrida del DAG `elastiflix_medallion`, lanzada por el propio planificador, termina en `success` en 4 o 5 minutos y deja Silver y Gold al día. Tres hallazgos: RustFS no aguantaba la carga sobre el directorio de Windows y sus datos pasaron a un volumen de Docker (decisión 67); el catálogo Iceberg necesita una sola conexión a SQLite; y `expire_snapshots` no expiraba nada sin `older_than`. Quedan abiertos la decisión sobre SeaweedFS, el reinicio de `flink-taskmanager` y el margen de memoria del scheduler (R12) |
| 2026-11-23 | F9-20 | Agente | F9 100 % · Global 86 % | Con el DAG completo se borró su registro en Airflow (`airflow dags delete`). `airflow-dag-processor` lo volvió a registrar a los 33 s, sin pausa y con su programación de 10 minutos, y el scheduler creó por su cuenta una corrida programada, una sola, que terminó en `success` en 265 s con las seis tareas al primer intento. Nadie la activó ni la lanzó. El arranque desde un laboratorio vacío llega en F11-03 |
| 2026-11-23 | F9-18 | Agente | F9 95 % · Global 85 % | Reconstrucción de Bronze con el procedimiento de la sección 38, con RustFS sobre el volumen de Docker: simulador detenido, Silver al día y DAG en pausa; job de Flink cancelado, checkpoints borrados, las 20 tablas de Bronze eliminadas en 19 s con `drop-bronze-tables.sh` y envío nuevo con `flink-cdc-submit`. Bronze volvió a coincidir con PostgreSQL en las 20 tablas (439,937 filas, sin tombstones) a los 187 s; 210 s en total. Silver no cambió durante la reconstrucción. Al reanudar el DAG, su corrida terminó en `success` y `bronze_to_silver` no escribió nada: las 22 tablas de Silver conservan su snapshot y sus filas. No se probó con borrados ocurridos durante la parada, que es el caso del cierre por ausencia |
| 2026-11-23 | F9-17 | Agente | F9 89 % · Global 85 % | Con el TaskManager de Flink detenido, una corrida lanzada a mano: `validate_bronze` falló con `VBRONZE-002`, las cuatro tareas siguientes quedaron en `upstream_failed` sin ejecutarse, `iceberg_maintenance` corrió y terminó bien en 93 s, y `mark_run_failed` dejó la corrida en `failed`. Silver conservó sus filas y Gold sus snapshots. Al arrancar de nuevo el TaskManager el pipeline volvió a `RUNNING`. Solo se provocó el fallo de la primera validación; las de Silver y Gold comparten el mismo mecanismo y no se forzaron |
| 2026-11-23 | F9-16 | Agente | F9 84 % · Global 84 % | Corrida completa del DAG, programada y no lanzada a mano: `success` en 298 s, las seis tareas al primer intento y `mark_run_failed` omitida; cabe en el intervalo de 10 minutos. Silver y Gold quedaron al día y el pipeline de Flink siguió en `RUNNING`. Memoria máxima: 1.88 GiB en `airflow-scheduler`, de un límite de 2 GiB, y 2.03 GiB en `spark-worker`. El margen del scheduler es muy justo y queda como riesgo. Medido con RustFS sobre el volumen de Docker |
| 2026-11-23 | F9-15 | Agente | F9 79 % · Global 84 % | Tarea `iceberg_maintenance`, la última, con `trigger_rule = all_done`. En la corrida completa mantuvo las 49 tablas en 98 s. Se añade una séptima tarea que no estaba en el diseño, `mark_run_failed`: solo corre si alguna tarea falló y deja la corrida en error; sin ella, como el mantenimiento corre siempre y suele terminar bien, una corrida con una validación fallida figuraría como correcta. Con todo bien, se omite |
| 2026-11-23 | F9-14 | Agente | F9 74 % · Global 83 % | `validate_gold.py` y su tarea: cada producto existe, tiene filas y sus claves no traen nulos ni repetidos. En la corrida completa pasó en los siete productos en 29 s |
| 2026-11-23 | F9-13 | Agente | F9 68 % · Global 83 % | Tarea `silver_to_gold`, con dos reintentos y el mismo `--run-ts`. En la corrida completa recargó los siete productos en 42 s; `gold_processed_at` tiene un único valor, el `run_after` de la corrida, y cada tabla ganó un snapshot |
| 2026-11-23 | F9-12 | Agente | F9 63 % · Global 82 % | `validate_silver.py` y su tarea: versión vigente única, rangos sin solapes ni invertidos y claves sin huérfanas, 24 comprobaciones en total; las claves en 0 se anotan sin hacer fallar. En la corrida completa pasó las 24 en 35 s. Su fallo no se ha provocado todavía; llega en F9-17 |
| 2026-11-23 | F9-11 | Agente | F9 58 % · Global 82 % | Tarea `bronze_to_silver`, con dos reintentos. Pasa `dag_run.run_after` como `--run-ts`: el log del job muestra el mismo instante que la corrida y `silver_processed_at` de las filas nuevas coincide con él. En la corrida completa tardó 70 s (58 s el job, 20 s de ellos leyendo Bronze ya compactado) |
| 2026-11-23 | F9-10 | Agente | F9 53 % · Global 82 % | `validate_bronze.py` y su tarea, la primera del DAG. Comprobado desde Airflow, con el driver de Spark dentro de `airflow-scheduler`, en los dos sentidos: con el pipeline de Flink en `RESTARTING` falló con `VBRONZE-002` y un mensaje que dice qué hacer; con el pipeline en `RUNNING` encontró las 20 tablas y terminó bien en 18 s |
| 2026-11-23 | F9-08 | Agente | F9 47 % · Global 81 % | `iceberg_maintenance.py`: compacta las 20 tablas de Bronze y expira snapshots en las tres capas, conservando los 5 últimos. Dos correcciones respecto al diseño: `expire_snapshots` necesita además `older_than`, porque por defecto solo expira snapshots de más de cinco días; y reintenta la compactación cuando Flink confirma un checkpoint a la vez. Comprobado con RustFS sobre el volumen de Docker y con Flink y el simulador escribiendo: 193 s la primera corrida (2,445 archivos de datos compactados en 19) y 123 s la segunda, sin errores 503 ni lotes de borrado fallidos; Bronze pasó de 2,088 archivos de datos y 3,447 de borrado a 67 y 82, y ninguna tabla de Silver conserva más de 5 snapshots. Sobre el directorio de Windows no terminaba y tumbaba a Flink |
| 2026-11-23 | F9-19 | Agente | F9 42 % · Global 81 % | El DAG lleva `schedule=timedelta(minutes=10)`, `catchup=False`, `max_active_runs=1` e `is_paused_upon_creation=False`. Comprobado por la API: programación `0:10:00` y una corrida activa como máximo. Para comprobar que nace activo se borró su registro (`airflow dags delete`): al volver a registrarlo quedó sin pausa y el scheduler creó solo una corrida programada, que terminó en `success`; no creó corridas atrasadas. Después se dejó en pausa a mano mientras se le añaden las tareas |
| 2026-11-23 | F9-09 | Agente | F9 37 % · Global 80 % | `airflow/dags/elastiflix_medallion.py` con el DAG `elastiflix_medallion`, todavía sin tareas ni programación. `airflow-dag-processor` lo registró en su siguiente lectura del directorio, que hace cada 5 minutos, sin errores de importación; la API lo devuelve con su descripción y su etiqueta. Nace en pausa, que es el valor por defecto; lo cambia F9-19. F9-08 queda abierta: el job de mantenimiento está escrito y compacta bien, pero sus borrados chocan con RustFS y se sigue probando |
| 2026-11-23 | F9-07 | Agente | F9 32 % · Global 80 % | `airflow-init` crea el administrador con `airflow users create --role Admin`, a partir de `AIRFLOW_ADMIN_USER` y `AIRFLOW_ADMIN_PASSWORD`. Ejecutado dos veces: la primera lo crea y la segunda detecta que existe y termina igual, con código 0. La contraseña queda cifrada con `scrypt` en `ab_user` y no aparece en los logs. Comprobado por la API: con sus credenciales se obtiene un token y `/api/v2/dags` responde 200; con una contraseña incorrecta, 401. No se inició sesión desde un navegador |
| 2026-11-23 | F9-06 | Agente | F9 26 % · Global 79 % | `airflow-dag-processor` en el Compose. Arrancado: sano a los 16 s y la comprobación de salud de la API lo da por sano; 178 MiB de sus 512. Sin errores ni secretos en sus logs. Todavía no hay ningún DAG que leer; eso se comprueba al crear el DAG (F9-09) |
| 2026-11-23 | F9-05 | Agente | F9 21 % · Global 79 % | `airflow-scheduler` en el Compose, con `LocalExecutor` y 2 GB de límite. Arrancado: sano a los 16 s (su latido en la base de metadatos es reciente) y la comprobación de salud de la API lo da por sano. 370 MiB en reposo. Sin errores ni secretos en sus logs. Falta ejercitarlo como driver de Spark, que llega con las tareas del DAG |
| 2026-11-23 | F9-04 | Agente | F9 16 % · Global 78 % | `airflow-apiserver` en el Compose, publicado en `127.0.0.1:8080`. Arrancado: sano a los 17 s; su comprobación de salud responde sin credenciales y da la base de metadatos por sana; la API sin credenciales devuelve 401. 270 MiB de sus 512. Sin errores ni secretos en sus logs |
| 2026-11-23 | F9-03 | Agente | F9 11 % · Global 78 % | Job `airflow-init` en el Compose, con los campos comunes de Airflow (imagen, variables y montajes). Ejecutado: `airflow db migrate` crea en 15 s las tablas de la base `airflow` de `metadata-db`, las del gestor de autenticación incluidas, y termina con código 0. Repetido sobre la base ya migrada: termina igual, sin cambios. Ni la contraseña de la base ni los secretos de Airflow aparecen en sus logs |
| 2026-11-23 | F9-02 | Agente | F9 5 % · Global 77 % | `airflow/Dockerfile` sobre `apache/airflow:3.4.0-python3.12`: añade Java 21, `pyspark` y `pyspark-client` 4.1.4, el proveedor de Spark 6.3.4 y los dos JAR de Iceberg 1.12.0, con su SHA-1 comprobado. Construida en 89 s (4.77 GB; la base, 3.25 GB). Comprobado dentro de la imagen: Airflow sigue en 3.4.0, `SparkSubmitOperator` importa, `spark-submit` reporta 4.1.4, `pip check` no encuentra conflictos y corre como `airflow` (50000). No se construyó para `arm64` |
| 2026-11-23 | F8 | Agente | F8 100 % · Global 77 % | Fase terminada. Su criterio de cierre está comprobado: los siete productos de Gold existen y cada corrida los reemplaza completos, en un snapshot de operación `overwrite` y sin archivos de borrado. 38 comprobaciones contra Silver, leídas con DuckDB, en cero. Las columnas de los productos las definió el agente y quedan a revisión de la persona responsable (sección 6). La duda sobre `has_homepage` queda resuelta: Gold lo toma de la versión vigente de `dim_movie` |
| 2026-11-23 | F8-10 | Agente | F8 100 % · Global 77 % | Segunda corrida, tras poner Silver al día: cada tabla gana un snapshot con operación `overwrite` que borra todas las filas anteriores y escribe las nuevas, en un solo archivo de datos y sin archivos de borrado; las filas no se duplican y `gold_processed_at` tiene un único valor. 125 s con RustFS recién arrancado y 238 s la primera vez. No se probó con consultas concurrentes durante la recarga |
| 2026-11-23 | F8-03, F8-04, F8-05, F8-06, F8-07, F8-08 y F8-09 | Agente | F8 90 % · Global 77 % | Los siete productos: 6,899 películas vivas, 19 géneros, 1,039 colecciones, 4,067 películas con presupuesto y recaudación, 531 meses de estreno, 95,050 personas y 41 métricas de cobertura. Comprobados contra Silver con DuckDB, 38 de 38 en cero: títulos, colecciones y géneros vigentes, medidas iguales al último snapshot, conteos y totales de cada agregado, y cifras repartidas por peso que suman el total salvo 12.53 USD de redondeo sobre 954 mil millones |
| 2026-11-23 | F8-01 y F8-02 | Agente | F8 20 % · Global 73 % | Definidas las columnas de los siete productos, que el diseño solo nombraba; quedan en la sección 33 y pendientes de que la persona responsable las ajuste. Todos describen las películas vivas con sus nombres vigentes y solo usan tipos simples. `silver_to_gold.py`, sin UDF de Python, con `--run-ts` y los errores `GOLD-001` y `GOLD-002`; pasa `ruff check` |
| 2026-11-23 | F7 | Agente | F7 100 % · Global 73 % | Fase terminada. Su criterio de cierre está comprobado: Silver tiene sus 14 dimensiones, 2 hechos y 6 bridges, con las columnas del diseño, y una corrida sin cambios no escribe nada. Verificación aparte de la del agente que la implementó, leyendo Silver con DuckDB: los casos de la sección 31 sobre películas reales y 117 comprobaciones de calidad, 115 en cero y 2 informativas. Dos hallazgos, en la sección 6: RustFS se degrada a los 60 minutos de arrancar y multiplica por cinco la duración del job, y el job no sobrevive a la pérdida del ejecutor |
| 2026-11-23 | F7-34 | Agente | F7 100 % · Global 73 % | Comprobación propia: una película insertada y borrada entre dos corridas queda en Bronze como tombstone y no deja ninguna fila en `dim_movie` ni en el hecho; el job termina bien |
| 2026-11-23 | F7-35 | Agente | F7 97 % · Global 72 % | Comprobación propia: al renombrar una keyword y una colección solo cambian `dim_keyword` y `dim_collection`. Los 9 bridges que usan la keyword conservan su versión anterior, y las películas afectadas no reciben versión ni snapshot |
| 2026-11-23 | F7-33 | Agente | F7 94 % · Global 72 % | Cierre por ausencia. Comprobado por el agente de Python quitando de Bronze, con Spark SQL, las filas de claves de prueba: versión, bridges, keyword y colección quedaron cerrados con el timestamp de la corrida, y el snapshot `is_deleted` lleva esa fecha. No se probó con una reconstrucción real de Bronze, que llega en F9-18 |
| 2026-11-23 | F7-31 y F7-32 | Agente | F7 91 % · Global 71 % | Comprobación propia. Sin cambios en Bronze, la corrida deja las 22 tablas con el mismo snapshot vigente, el mismo número de snapshots y las mismas filas (335 s). Sobre películas reales: UPDATE descriptivo, de medidas y de relaciones (el género quitado se cierra y los pesos pasan de 0.20 a 0.25), DELETE (versión, 92 bridges y procedencia cerrados, snapshot `is_deleted`) y reinserción (versión 2, bridges nuevos y snapshot vivo). Una corrida falló al congelarse Docker un minuto; no dejó escrituras y su repetición pasó |
| 2026-11-23 | F7-30 | Agente | F7 86 % · Global 70 % | Reparación de claves 0 en bridges, hecho y procedencia. Comprobada por el agente de Python, que ocultó en Bronze las filas de las dimensiones y las devolvió después: las claves pasaron de 0 a su valor sin cambiar el `movie_snapshot_sk` ni el `effective_from` de los bridges. No la repetí; leí el código de las tres ramas |
| 2026-11-23 | F7-28 y F7-29 | Agente | F7 83 % · Global 70 % | Los dos hechos. `record_hash` usa claves de negocio, medidas y conteos: un cambio de título no crea snapshot y uno de popularidad sí (comprobación propia). El último snapshot de cada película viva coincide con Bronze, y `profit_usd` y `roi_percentage` están bien calculados en todas las filas. 974 snapshots tienen `rating_sk = 0`: son películas sin rating en origen |
| 2026-11-23 | F7-22, F7-23, F7-24, F7-25, F7-26 y F7-27 | Agente | F7 77 % · Global 69 % | Los seis bridges, anclados en `movie_id`. Comprobación propia, con Bronze quieto: las filas vigentes coinciden con las relaciones vivas de Bronze en los dos sentidos, hay una sola fila vigente por película y posición, y todos los pesos vigentes valen 1/n. Sin claves huérfanas ni en 0 |
| 2026-11-23 | F7-19, F7-20 y F7-21 | Agente | F7 60 % · Global 66 % | `dim_movie`, `dim_collection` y `dim_keyword` con SCD2. Comprobación propia sobre datos reales: un cambio de título cierra la versión 1 y crea la 2; al deshacerlo, la 3. Lo mismo al renombrar una keyword y una colección, que conserva su imagen canónica. Sin claves con más de una versión vigente, sin rangos solapados y con `version_number` consecutivo en las tres |
| 2026-11-23 | F7-09, F7-10, F7-11, F7-12, F7-13, F7-14, F7-15, F7-16, F7-17 y F7-18 | Agente | F7 51 % · Global 65 % | Las diez dimensiones Tipo 1, con sus columnas iguales a las del diseño en nombre y orden. Primera carga: 43 idiomas originales, 1 estado, 7 ratings, 19 géneros, 95,050 personas, 8,061 compañías, 98 países, 68 idiomas hablados, 21 campos y 77 códigos de procedencia. Sin claves sustitutas ni de negocio repetidas (comprobación propia). No se ejercitó la rama que actualiza un atributo |
| 2026-11-23 | F7-06, F7-07 y F7-08 | Agente | F7 23 % · Global 60 % | `bronze_to_silver.py`, 1,485 líneas, sin UDF de Python, con `--run-ts`, `--reference-dir` y errores `SILVER-001` a `SILVER-003`. Código leído completo contra el diseño (§19 a §31), sin desviaciones. `dim_date` con 73,051 filas y cada dimensión con sus filas 0 y -1 (comprobación propia con DuckDB: 0 incidencias en las 14) |
| 2026-11-23 | F7-05 | Agente | F7 14 % · Global 59 % | Seis CSV en `pyspark/reference/`: 43 idiomas, 1 estado, 7 ratings, 96 países, 68 idiomas hablados y 21 campos de procedencia, en UTF-8. `Soviet Union` y `Czechoslovakia` quedan como `unmapped`, sin código ISO vigente |
| 2026-11-23 | F7-01, F7-02, F7-03 y F7-04 | Agente | F7 11 % · Global 59 % | Imagen `elastiflix-spark:4.1.4-iceberg1.12.0` (2.55 GB) con los dos JAR de Iceberg 1.12.0 y Python 3.12.16 instalado con `uv`; corre como `spark` (185). `spark-defaults.conf` con el catálogo `lake`, y `spark-master` y `spark-worker` en el Compose, sanos y con el worker registrado (1500 MB, 4 núcleos). Revisado aparte: `docker compose config` pasa, la imagen trae lo dicho y no queda `uv` en ella. Memoria máxima, medida por el agente de Python: 0.29 GiB el master y 2.18 GiB el worker |
| 2026-11-23 | F6 | Agente | F6 100 % · Global 57 % | Fase terminada. Su criterio de cierre está comprobado: el simulador cumple los requisitos RF-01 a RF-13 y su interfaz se abre con `docker compose attach`. El código lo escribió el agente de Java; lo verifiqué aparte antes de registrar nada. Quedan sin probar, por no ser necesarias o por coste: el umbral de demora con sus 120 s reales, la rotación del log de Docker, la imagen en `arm64` y un teclado real en Windows Terminal. `duckdb/init/attach_lakehouse.sql`, la primera mitad de F10-01, se creó ya porque el simulador lo necesita |
| 2026-11-23 | F6-44, F6-31, F6-32 y F6-45 | Agente | F6 100 % · Global 57 % | Con el laboratorio a cero: `docker compose up -d` deja el simulador emitiendo a los 51 s. Dos ejecuciones con la semilla 42 dan las mismas 300 primeras transacciones. Tras `stop` y `start` continúa en la película siguiente a la última insertada. En reposo, PostgreSQL y Bronze coinciden en las 20 tablas. Las claves no aparecen en ningún log |
| 2026-11-23 | F6-29, F6-39, F6-30 y F6-36 | Agente | F6 91 % · Global 55 % | Imagen `elastiflix-simulator:1.0.0` de dos etapas (661 MB), usuario `simulator` 10002, extensiones de DuckDB instaladas en el build y servicio `java-simulator` en el Compose con `tty`, `stdin_open`, 512 MB y log limitado a 3 archivos de 10 MB. Memoria medida: 170 a 240 MiB; 336 MiB como máximo tras 10,000 transacciones |
| 2026-11-23 | F6-27 y F6-28 | Agente | F6 82 % · Global 53 % | 71 pruebas unitarias en siete clases: lectura de CSV con comillas, saltos de línea y UTF-8, carga del dataset real, selección de operaciones, registro de películas, contenido de los UPDATE, configuración y regla de llegada a Bronze |
| 2026-11-23 | F6-37, F6-26 y F6-38 | Agente | F6 78 % · Global 52 % | Seguimiento hasta Bronze con DuckDB en un hilo propio (`threads=2`, `memory_limit=128MB`) y reapertura tras un fallo. La columna pasa de «pendiente» a ✓ con 11 a 50 s de retraso. La demora la probó el agente de Java con el umbral bajado a 8 s, no con los 120 s del diseño |
| 2026-11-23 | F6-22, F6-23, F6-24 y F6-25 | Agente | F6 71 % · Global 51 % | Pausa y reanudación, cambio de velocidad, diálogo de pesos y diálogo de operación manual con búsqueda por `movie_id` o título. Un DELETE manual lanzado en pausa quedó marcado `M`, en el log como `MANUAL` y confirmado en Bronze a los 32 s. La aplicación de pesos nuevos la comprobó el agente de Java |
| 2026-11-23 | F6-17, F6-18, F6-19, F6-20, F6-21, F6-33, F6-34, F6-35 y F6-40 | Agente | F6 62 % · Global 49 % | Pantalla de cinco zonas comprobada con `tmux` a 130×40: se abre con una tecla, `Q` vuelve al modo de líneas, dos `Ctrl-C` no detienen el contenedor, y a 90×28 muestra el aviso de tamaño mínimo y se repinta al volver |
| 2026-11-23 | F6-12, F6-43, F6-13, F6-14, F6-15 y F6-16 | Agente | F6 42 % · Global 45 % | Selección por pesos y semilla, tipo de UPDATE entre los admisibles, modo continuo con reinserción automática, y modo de líneas con copia en `/tmp/simulator.log`. RF-12 comprobado plantando una fila en conflicto: la transacción se revierte con `ERROR` y código `SIM-021`, y la simulación sigue. El agotamiento completo de `movie.csv` lo comprobó el agente de Java a 10 ms |
| 2026-11-23 | F6-07, F6-08, F6-09, F6-41, F6-10 y F6-11 | Agente | F6 29 % · Global 42 % | Los cuatro tipos de UPDATE, el DELETE y la reinserción. Contrastado en PostgreSQL: todo UPDATE deja `updated_at` posterior a `created_at` en la película, y en la keyword o colección renombrada; ningún nombre acumula sufijos `(rev N)`; el DELETE borra las relaciones por cascada |
| 2026-11-23 | F6-01, F6-02, F6-03, F6-04, F6-05, F6-06 y F6-42 | Agente | F6 16 % · Global 40 % | Proyecto Maven con las cuatro librerías del diseño; `mvn verify` pasa 71 pruebas en el host y dentro de la imagen. Carga los 20 CSV (438,925 filas) en unos 3.5 s, se conecta como `elastiflix_app`, da de alta cada película en una transacción con sus catálogos y entidades nuevos, y al arrancar sobre una base con datos continúa con la primera pendiente |
| 2026-11-23 | F5 | Agente | F5 100 % · Global 36 % | Fase terminada. Su criterio de cierre está comprobado: las 20 tablas están en Bronze, reflejan INSERT, UPDATE y DELETE, y el pipeline se reanuda al repetir `docker compose up` tras reiniciar Flink. Dos hallazgos, anotados en el diseño: la carga de desarrollo no puede ir en una sola transacción, y DuckDB 1.5.6 falla con `UNION ALL` sobre tablas con borrados |
| 2026-11-23 | F5-20 | Agente | F5 100 % · Global 36 % | Reconstrucción completa tras perder los checkpoints, con una película borrada entretanto: el script elimina las 20 tablas en 49 s sin dejar objetos en RustFS, `flink-cdc-submit` hace un envío nuevo y a los 110 s Bronze vuelve a coincidir con PostgreSQL en las 20 tablas, todo en `+I` |
| 2026-11-23 | F5-16 | Agente | F5 95 % · Global 36 % | `flink/jobs/drop-bronze-tables.sh`: sin `--confirm` solo lista lo que borraría; se niega si el pipeline está vivo o si recibe otro argumento; con `--confirm` borra las tablas de `bronze` con purga |
| 2026-11-23 | F5-19 | Agente | F5 90 % · Global 36 % | Sin checkpoints y con 20 tablas en Bronze, `flink-cdc-submit` termina con código 1 y un mensaje que remite a la reconstrucción; no hay job nuevo y Bronze queda intacto |
| 2026-11-23 | F5-15 | Agente | F5 85 % · Global 35 % | Tras reiniciar JobManager y TaskManager el clúster queda sin jobs y el slot, inactivo. Un UPDATE y un DELETE hechos durante la parada llegan a Bronze al repetir `docker compose up`, que reanuda desde el último checkpoint; no se repite el snapshot: las demás filas conservan su `cdc_op_ts` |
| 2026-11-23 | F5-14 | Agente | F5 80 % · Global 35 % | Repetir `docker compose up` con el pipeline en marcha: `flink-cdc-submit` informa de que ya corre, el job es el mismo y las marcas de Bronze no cambian |
| 2026-11-23 | F5-13 | Agente | F5 75 % · Global 34 % | Un DELETE deja la película como tombstone `-D` con el título y el `plot` completos, y 62 tombstones en sus ocho tablas de relación; PostgreSQL y Bronze siguen coincidiendo en filas vivas |
| 2026-11-23 | F5-12 | Agente | F5 70 % · Global 34 % | Un UPDATE del título deja la fila en `+U` con el valor nuevo y una sola fila para esa clave |
| 2026-11-23 | F5-11 | Agente | F5 65 % · Global 33 % | Un alta con dos géneros y una keyword en una transacción llega a Bronze como cuatro filas `+I` con el mismo `cdc_op_ts`, posterior al instante de referencia leído en PostgreSQL |
| 2026-11-23 | F5-10 | Agente | F5 60 % · Global 33 % | Con PostgreSQL vacío, el conector crea ya las 20 tablas de `bronze`. Con el dataset cargado después, en streaming, las 20 coinciden con PostgreSQL: 438,925 filas. La carga en una sola transacción no servía: PostgreSQL la volcaba a disco y Bronze no recibía nada; el script de carga pasa a una transacción por archivo |
| 2026-11-23 | F5-09 | Agente | F5 55 % · Global 32 % | Job `flink-cdc-submit` (512 MB) tras Flink, `postgresql` sano e `iceberg-init`. Desde cero, todo el proyecto arranca y deja el pipeline en `RUNNING` en 52 a 58 s |
| 2026-11-23 | F5-18 | Agente | F5 50 % · Global 32 % | Tras enviar o reanudar, el script espera hasta 120 s a que el job esté en `RUNNING` y solo entonces termina con 0 |
| 2026-11-23 | F5-17 | Agente | F5 45 % · Global 32 % | El script genera con `envsubst` una copia temporal del YAML con la contraseña de `.env`, con permisos solo para su usuario, y la borra al terminar. La contraseña no aparece en los logs de los tres servicios ni en la API REST de Flink |
| 2026-11-23 | F5-08 | Agente | F5 40 % · Global 31 % | Sin job ni checkpoint, el script cuenta las tablas de `bronze` en el catálogo; si hay alguna, termina con error sin enviar ni borrar |
| 2026-11-23 | F5-07 | Agente | F5 35 % · Global 31 % | El script busca el checkpoint retenido más reciente y reanuda con `--from-savepoint`; con dos directorios de job retenidos eligió el último |
| 2026-11-23 | F5-06 | Agente | F5 30 % · Global 30 % | `flink/jobs/submit-pipeline.sh`: consulta la API de Flink y, si el pipeline ya corre, termina sin enviar nada |
| 2026-11-23 | F5-05 | Agente | F5 25 % · Global 30 % | Servicio `flink-taskmanager` (2 GB), sano cuando el JobManager lo ve registrado. Bajo carga usó 1.05 GB |
| 2026-11-23 | F5-04 | Agente | F5 20 % · Global 29 % | Servicio `flink-jobmanager` (1 GB, interfaz en `127.0.0.1:8081`, healthcheck contra su API) tras `volumes-init`, con `flink/data` montado para los checkpoints. Sano en unos 10 s |
| 2026-11-23 | F5-03 | Agente | F5 15 % · Global 29 % | `flink/jobs/postgres-to-bronze.yaml`, igual al borrador del diseño, con el marcador de la contraseña. Flink lo acepta y el job queda en `RUNNING` |
| 2026-11-23 | F5-02 | Agente | F5 10 % · Global 28 % | `flink/config/flink-properties.conf`, que el Dockerfile aplica sobre la configuración de la imagen: checkpoint cada 30 s en `/opt/flink/state/checkpoints`, retenido al cancelar; 900 MB para el JobManager y 1800 MB para el TaskManager. Los checkpoints se completan en menos de 100 ms |
| 2026-11-23 | F5-01 | Agente | F5 5 % · Global 28 % | `flink/Dockerfile` sobre `flink:2.2.1-java21`: Flink CDC 3.7.0 para Flink 2.2 con los conectores `postgres` e `iceberg`, Iceberg 1.10.2 (runtime y `aws-bundle`), cliente de Hadoop 3.3.6, Commons Logging 1.2 y `jq`. Cada descarga se comprueba contra su suma publicada. La imagen se construye en 81 s y corre como `flink` |
| 2026-11-22 | F4 | Agente | F4 100 % · Global 27 % | Fase terminada. Su criterio de cierre quedó comprobado en F4-05 y F4-06: el bucket `warehouse` y los namespaces `bronze`, `silver` y `gold` existen y sobreviven a recrear los contenedores. Sigue en observación el defecto de la sección 6 |
| 2026-11-22 | F4-07 | Agente | F4 100 % · Global 27 % | En un navegador, en `http://127.0.0.1:9001/rustfs/console/`: con la clave del servicio se entra y la consola muestra el bucket `warehouse`, privado y vacío; con un secreto erróneo responde 403 y se queda en la pantalla de inicio de sesión |
| 2026-11-22 | F4-06 | Agente | F4 86 % · Global 27 % | Con una tabla de prueba en `bronze`: tras recrear solo `iceberg-rest`, solo `rustfs`, y tras `docker compose down` y un arranque completo, siguen el bucket, los tres namespaces y la tabla, que se carga bien; los dos jobs informan de que todo existía. En ese arranque completo `postgresql` falló una vez al inicializarse; anotado en la sección 6 |
| 2026-11-22 | F4-05 | Agente | F4 71 % · Global 27 % | Con la cadena levantada desde cero: RustFS lista el bucket `warehouse` y el catálogo, los namespaces `bronze`, `silver` y `gold`, vacíos, tanto desde el host como desde otro contenedor de la red. En el host aparecen `rustfs/data/warehouse` e `iceberg/data/iceberg_catalog.db` |
| 2026-11-22 | F4-04 | Agente | F4 57 % · Global 26 % | Job `iceberg-init` con la imagen de RustFS y `curl`, tras `iceberg-rest` sano. Desde cero crea `bronze`, `silver` y `gold` con `POST /v1/namespaces`; la segunda ejecución recibe 409 en los tres y termina igualmente con 0. Toda la cadena, desde `volumes-init`, tarda 10 s |
| 2026-11-22 | F4-03 | Agente | F4 43 % · Global 26 % | Servicio `iceberg-rest` (`apache/iceberg-rest-fixture:1.10.1`, 512 MB, usuario 1000, puerto 8181 en `127.0.0.1`) tras `rustfs-init`, con el healthcheck de la imagen y el SQLite en `iceberg/data/`. Sano a los 2 s de arrancar. Crea un namespace y una tabla en formato v2 cuyo `metadata.json` aparece en `s3://warehouse/`; los conserva tras recrear el contenedor; el borrado con purga limpia RustFS; un namespace repetido devuelve 409 |
| 2026-11-22 | F4-02 | Agente | F4 29 % · Global 25 % | Job `rustfs-init` con la imagen de RustFS y `curl --aws-sigv4`, tras `rustfs` sano. La primera ejecución crea el bucket `warehouse` y la segunda informa de que ya existe; las dos terminan con 0. Con una clave errónea falla con 403 y código distinto de cero |
| 2026-11-22 | F4-01 | Agente | F4 14 % · Global 25 % | Servicio `rustfs` (`rustfs/rustfs:1.0.6`, 1 GB, usuario 10001, puertos 9000 y 9001 en `127.0.0.1`) tras `volumes-init`, con healthcheck contra `/health/ready`. Sano en 7 s; acepta la clave y rechaza peticiones sin firma o con secreto erróneo; guarda y devuelve objetos y los conserva tras recrear el contenedor. La consola está en `/rustfs/console/`. Avisa de que el montaje de Windows (V9FS) no está soportado para producción: se abre el riesgo R10 |
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

Hoy no hay ninguna fila abierta. Las siete que hubo se cerraron en la actividad F12-05, con las decisiones 68 a 73.

| Fecha | Actividad | Qué pasa | Qué se necesita |
|---|---|---|---|

## 7. Riesgos

Lo que todavía no ha ocurrido pero puede retrasar el plan. Se revisa al cerrar cada fase. Un número de riesgo no se reutiliza: cuando un riesgo deja de serlo pasa a la tabla de cerrados, con el motivo.

### Riesgos abiertos

| # | Riesgo | Qué lo reduce | Si ocurre | Señal de alerta |
|---|---|---|---|---|
| R5 | El trabajo generado por un agente funciona a medias y se marca como hecho | Aplicar la definición de terminado y las actividades «Comprobar» | Desmarcar la actividad y anotarla en la sección 6 | Una comprobación posterior falla |
| R8 | Una corrida del DAG lee Bronze a medio reconstruir y cierra versiones de filas que siguen existiendo | Pausar el DAG antes de reconstruir, como pide el procedimiento | Restaurar Silver al snapshot anterior de Iceberg | El DAG corre mientras `flink-cdc-submit` está repitiendo el snapshot |
| R10 | El fallo intermitente de `initdb` con un falso «sin espacio», que se siguió como defecto hasta F12-05, forma parte de este riesgo: no apareció en el arranque desde cero de F11 y repetir `docker compose up -d` lo recupera. Los directorios de datos montados desde Windows fallan bajo carga: a los contenedores les llegan como V9FS, RustFS los declara no soportados para producción, y `postgresql` falló una vez al inicializarse con un falso «sin espacio» y tardó minutos en volcar a disco una transacción grande. En F5, RustFS y los checkpoints de Flink aguantaron el dataset completo sin errores. En F7 se vio que RustFS se degrada a los 60 minutos de arrancar, cuando su `scanner` empieza a recorrer el directorio, y que el motor de Docker se congeló una vez cerca de un minuto con dos lecturas pesadas a la vez. En F9 el riesgo se materializó: RustFS devolvió 503 bajo carga y tumbó tres veces el TaskManager de Flink. Mitigado para RustFS, que desde F9-08 guarda sus datos en un volumen de Docker; sigue abierto para PostgreSQL, el catálogo y los checkpoints, que continúan en el montaje: el PostgreSQL operacional se detuvo una vez con «Cannot allocate memory» mientras se copiaban 18,447 archivos y había dos laboratorios en marcha, y se recuperó solo | Los datos de RustFS ya están en un volumen. Para lo demás no hay una mitigación activa: se vigiló en F5-10 a F5-13, en el arranque desde cero de F11-03, en F11-09 y en el clon de F12-06, sin que reapareciera | Guardar los datos en volúmenes con nombre de Docker, lo que cambia la regla de persistencia del diseño (§7) | Errores de lectura o escritura en los logs, un servicio que no se inicializa, o commits de Iceberg que fallan |
| R12 | `airflow-scheduler` se queda sin memoria: con el driver de Spark dentro llegó a 1.88 GiB de su límite de 2 GiB en una corrida completa del DAG | Medido de nuevo en F11-09 con todo el stack: 1.87 GiB, sin fallar. `airflow-dag-processor` también queda justo, con 0.46 de 0.5 GiB. No hay nada que lo reduzca sin cambiar el presupuesto | Subir su límite o bajar `spark.driver.memory`, lo que cambia el presupuesto de memoria del diseño (§39) | El contenedor termina con `OOMKilled` o las tareas del DAG quedan a medias |

### Riesgos cerrados

| # | Riesgo | Fecha de cierre | Por qué se cerró |
|---|---|---|---|
| R1 | La consola Lanterna no funciona a través de `docker compose attach` | 2026-11-22 | La validación 10 pasó desde una terminal de Linux y otra de Windows (F0-14) |
| R2 | El dataset regenerado llega tarde o no cumple | 2026-11-22 | El dataset regenerado se recibió, se validó y quedó como definitivo (F1-04 a F1-09) |
| R3 | Todo el stack junto no cabe en la memoria prevista | 2026-11-22 | Los 13 servicios corrieron a la vez con sus límites: 7.9 GB de máximo bajo carga, sin ningún contenedor detenido por memoria. F11-09 repitió la medición con el laboratorio construido: 7.41 GiB de máximo |
| R4 | Una decisión abierta de F0 frena una fase del camino más largo | 2026-11-22 | No queda ninguna decisión abierta |
| R6 | DuckDB JDBC no adjunta el catálogo o no lee Bronze desde Java 25 | 2026-11-22 | La validación 11 pasó: adjunta el catálogo, lee `bronze.movie` y detecta los cambios (F0-15) |
| R7 | El lector CSV del simulador no interpreta bien las celdas con comas, comillas y saltos de línea | 2026-11-22 | Apache Commons CSV 1.14.1 lee los 20 CSV desde Java 25 con el mismo contenido, celda por celda, que una lectura de referencia |
| R9 | La importación de la base y los dashboards en Superset no funciona como está diseñada | 2026-11-22 | La importación se retiró del diseño: los dashboards los crea quien usa el laboratorio |
| R11 | Una corrida del DAG no cabe en su intervalo de 10 minutos | 2026-11-23 | Con RustFS sobre el volumen de Docker y Bronze compactado en cada corrida, la corrida completa tarda entre 4 y 5 minutos (F9-16) |
