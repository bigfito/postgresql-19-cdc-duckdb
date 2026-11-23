"""Validación de Bronze, primera tarea del DAG (diseño, sección 18).

Comprueba dos cosas antes de que `bronze_to_silver.py` lea nada:

- que existen las 20 tablas Bronze. Mientras Flink está creándolas, o durante
  una reconstrucción de Bronze, faltan algunas; con unas sí y otras no, Silver
  daría por borradas filas que siguen existiendo (sección 38);
- que el pipeline de Flink CDC está en `RUNNING`, según la API REST de Flink.

No exige actividad reciente: con el simulador en pausa Bronze puede estar
quieto. Si algo falla, el job termina con código 1, el DAG se detiene y Silver
conserva su último estado.

Cómo se lanza::

    spark-submit /opt/spark/jobs/validate_bronze.py
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import urllib.error
import urllib.request
from collections.abc import Sequence

from pyspark.sql import SparkSession

LOG = logging.getLogger("validate_bronze")

APP_NAME = "validate_bronze"
BRONZE = "lake.bronze"
BRONZE_TABLES = (
    "movie",
    "movie_collection", "movie_genre", "movie_keyword", "movie_cast",
    "movie_production_company", "movie_production_country", "movie_spoken_language",
    "movie_enrichment",
    "collection", "genre", "keyword", "person", "production_company",
    "production_country", "spoken_language",
    "original_language", "movie_status", "content_rating", "enrichment_field",
)

# API REST de Flink, por el nombre del servicio en la red del Compose, y nombre
# del pipeline, el que le da flink/jobs/postgres-to-bronze.yaml.
FLINK_URL = "http://flink-jobmanager:8081"
PIPELINE_NAME = "elastiflix-postgres-to-bronze"
RUNNING = "RUNNING"
HTTP_TIMEOUT_SECONDS = 10


class ValidationError(Exception):
    """Bronze no está en condiciones de alimentar a Silver.

    El mensaje dice qué falta, cuál es la causa probable y qué hacer.
    """

    code = "VBRONZE-000"

    def __str__(self) -> str:
        """El mensaje, precedido del código de error."""
        return f"[{self.code}] {super().__str__()}"


class BronzeTablesMissingError(ValidationError):
    """Falta alguna de las 20 tablas Bronze."""

    code = "VBRONZE-001"


class PipelineNotRunningError(ValidationError):
    """El pipeline de Flink CDC no está en ejecución, o Flink no responde."""

    code = "VBRONZE-002"


def check_tables(spark: SparkSession) -> None:
    """Comprueba que existen las 20 tablas Bronze.

    Raises:
        BronzeTablesMissingError: si falta alguna.
    """
    missing = [name for name in BRONZE_TABLES if not spark.catalog.tableExists(f"{BRONZE}.{name}")]
    if missing:
        raise BronzeTablesMissingError(
            f"Faltan {len(missing)} de las {len(BRONZE_TABLES)} tablas Bronze: {', '.join(missing)}. "
            "Causa probable: el pipeline de Flink CDC acaba de arrancar y todavía las está creando, "
            "o Bronze se está reconstruyendo (diseño, sección 38). Silver no se ha tocado; la "
            "corrida siguiente lo vuelve a comprobar."
        )
    LOG.info("Existen las %d tablas Bronze", len(BRONZE_TABLES))


def pipeline_states(flink_url: str) -> list[str]:
    """Estados de los jobs de Flink que se llaman como el pipeline.

    Raises:
        PipelineNotRunningError: si la API de Flink no responde.
    """
    url = f"{flink_url}/jobs/overview"
    try:
        with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT_SECONDS) as response:
            overview = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise PipelineNotRunningError(
            f"La API de Flink no responde en {url}: {error}. Causa probable: flink-jobmanager está "
            "detenido o arrancando. Comprueba `docker compose ps flink-jobmanager`."
        ) from error
    return [job["state"] for job in overview.get("jobs", []) if job.get("name") == PIPELINE_NAME]


def check_pipeline(flink_url: str) -> None:
    """Comprueba que el pipeline de Flink CDC está en ``RUNNING``.

    Raises:
        PipelineNotRunningError: si no hay ningún job del pipeline en ejecución.
    """
    states = pipeline_states(flink_url)
    if RUNNING not in states:
        found = ", ".join(states) if states else "ninguno"
        raise PipelineNotRunningError(
            f"El pipeline {PIPELINE_NAME} no está en {RUNNING}; estados encontrados: {found}. "
            "Causa probable: el job falló o todavía no se ha enviado. Reenvíalo con "
            "`docker compose up -d flink-cdc-submit`, que retoma desde el último checkpoint."
        )
    LOG.info("El pipeline %s está en %s", PIPELINE_NAME, RUNNING)


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Lee los argumentos de la línea de comandos."""
    parser = argparse.ArgumentParser(description="Valida que Bronze puede alimentar a Silver.")
    parser.add_argument(
        "--flink-url", default=FLINK_URL,
        help=f"Dirección de la API REST de Flink. Por defecto, {FLINK_URL}.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Punto de entrada. Devuelve el código de salida del proceso."""
    logging.basicConfig(
        level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    args = parse_arguments(argv)
    spark = SparkSession.builder.appName(APP_NAME).getOrCreate()
    # Los mensajes INFO de Spark tapan los del job; se dejan sus avisos y errores.
    spark.sparkContext.setLogLevel("WARN")
    try:
        check_tables(spark)
        check_pipeline(args.flink_url)
    except ValidationError as error:
        LOG.error("%s", error)
        return 1
    finally:
        spark.stop()
    LOG.info("Bronze está en condiciones de alimentar a Silver")
    return 0


if __name__ == "__main__":
    sys.exit(main())
