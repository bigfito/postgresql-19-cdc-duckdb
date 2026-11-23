"""DAG `elastiflix_medallion`: lleva los datos de Bronze a Silver y a Gold.

Es el procesamiento por lotes del laboratorio (diseño, sección 18). Flink CDC
mantiene Bronze al día por su cuenta; este DAG toma lo que haya en Bronze y
actualiza el modelo dimensional de Silver y los productos de Gold que consulta
Superset.

Cada tarea lanza un job de PySpark con `spark-submit` en modo cliente: el
driver corre aquí, en el contenedor del scheduler, y los ejecutores en
`spark-worker`.

Corre cada 10 minutos desde que se crea, sin que nadie lo active, y nunca hay
dos corridas a la vez. También se puede lanzar a mano en cualquier momento.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.sdk import DAG, TriggerRule, task
from airflow.sdk.exceptions import AirflowFailException

# Los jobs están montados aquí, en la misma ruta que en los contenedores de
# Spark: en modo cliente spark-submit lee el archivo en la máquina que lo lanza.
JOBS_DIR = "/opt/spark/jobs"

# El driver corre en este contenedor. Los ejecutores, en spark-worker, se
# conectan de vuelta a él: tienen que encontrarlo por el nombre del servicio, y
# el driver tiene que escuchar en todas sus interfaces.
DRIVER_CONF = {
    "spark.driver.host": "airflow-scheduler",
    "spark.driver.bindAddress": "0.0.0.0",
}

# Timestamp lógico de la corrida, que los jobs usan como fecha de proceso y
# como fecha de los cierres por ausencia. Es `run_after` y no `logical_date`
# porque una corrida lanzada a mano no tiene `logical_date` (decisión 36).
RUN_TIMESTAMP = ["--run-ts", "{{ dag_run.run_after.isoformat() }}"]

# Las transformaciones se reintentan: son idempotentes, y un fallo pasajero,
# como perder el ejecutor de Spark, se resuelve repitiendo el job.
RETRY = {"retries": 2, "retry_delay": timedelta(minutes=1)}


def spark_job(task_id: str, *, arguments: list[str] | None = None, **task_options: object) -> SparkSubmitOperator:
    """Tarea que lanza el job de PySpark del mismo nombre.

    Args:
        task_id: nombre de la tarea y del archivo del job, sin la extensión.
        arguments: argumentos del job; admiten plantillas de Airflow.
        task_options: opciones de la tarea, como los reintentos.
    """
    return SparkSubmitOperator(
        task_id=task_id,
        application=f"{JOBS_DIR}/{task_id}.py",
        name=task_id,
        conn_id="spark_default",
        conf=DRIVER_CONF,
        application_args=arguments,
        **task_options,
    )


@task(trigger_rule=TriggerRule.ONE_FAILED)
def mark_run_failed() -> None:
    """Deja la corrida en error cuando alguna tarea falló.

    Airflow decide el estado de una corrida por sus tareas finales. La última,
    `iceberg_maintenance`, corre siempre y casi siempre termina bien, así que
    sin esta tarea una corrida con una validación fallida figuraría como
    correcta. Solo se ejecuta si alguna tarea falló; si todas van bien, se
    omite y la corrida queda en `success`.
    """
    raise AirflowFailException(
        "Alguna tarea de la corrida falló; su log dice cuál y por qué. "
        "La corrida siguiente vuelve a intentarlo."
    )


with DAG(
    dag_id="elastiflix_medallion",
    description="Bronze -> Silver -> Gold, con validaciones y mantenimiento de Iceberg",
    # Fecha fija en el pasado: solo marca desde cuándo puede haber corridas.
    start_date=datetime(2026, 1, 1, tzinfo=UTC),
    schedule=timedelta(minutes=10),
    # Sin catchup no se crean las corridas atrasadas desde start_date: solo la
    # más reciente.
    catchup=False,
    # Una corrida a la vez: dos escribiendo Silver al mismo tiempo chocarían.
    # Si una se alarga más de 10 minutos, la siguiente espera.
    max_active_runs=1,
    # Airflow crea los DAG en pausa; este nace activo para que el laboratorio
    # funcione solo tras `docker compose up`.
    is_paused_upon_creation=False,
    doc_md=__doc__,
    tags=["elastiflix"],
) as dag:
    # Sin las 20 tablas Bronze o sin el pipeline de Flink en marcha no se toca
    # Silver. No se reintenta: si falla, la corrida siguiente vuelve a mirar.
    validate_bronze = spark_job("validate_bronze")

    bronze_to_silver = spark_job("bronze_to_silver", arguments=RUN_TIMESTAMP, **RETRY)

    # Si Silver no es coherente, Gold no se recarga y conserva su último estado.
    validate_silver = spark_job("validate_silver")

    silver_to_gold = spark_job("silver_to_gold", arguments=RUN_TIMESTAMP, **RETRY)

    validate_gold = spark_job("validate_gold")

    # Corre siempre, aunque falle o se salte una tarea anterior: Bronze acumula
    # archivos pequeños con cada checkpoint de Flink y no puede esperar.
    iceberg_maintenance = spark_job("iceberg_maintenance", trigger_rule=TriggerRule.ALL_DONE)

    (
        validate_bronze
        >> bronze_to_silver
        >> validate_silver
        >> silver_to_gold
        >> validate_gold
        >> iceberg_maintenance
    )

    [
        validate_bronze, bronze_to_silver, validate_silver, silver_to_gold,
        validate_gold, iceberg_maintenance,
    ] >> mark_run_failed()
