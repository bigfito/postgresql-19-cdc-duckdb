"""Validación de Silver, tercera tarea del DAG (diseño, secciones 18 y 36).

Comprueba, después de `bronze_to_silver.py` y antes de recargar Gold, las tres
propiedades que Gold da por ciertas:

- una sola versión vigente por clave de negocio en cada dimensión SCD2;
- rangos de vigencia sin solapes ni invertidos;
- ninguna clave sustituta huérfana: toda clave de un hecho o de un bridge
  existe en su dimensión.

Cada comprobación es una consulta que cuenta incidencias; cero es lo correcto.
Si alguna da más de cero, el job termina con código 1, el DAG se detiene y
Gold conserva su último estado.

Las claves en 0 (Unknown) no son un error: son referencias pendientes que la
corrida siguiente repara (sección 30). Se cuentan y se anotan en el log, sin
hacer fallar la validación.

Cómo se lanza::

    spark-submit /opt/spark/jobs/validate_silver.py
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass

from pyspark.sql import SparkSession

LOG = logging.getLogger("validate_silver")

APP_NAME = "validate_silver"
SILVER = "lake.silver"

# Dimensiones SCD2: tabla, clave sustituta y clave de negocio.
SCD2_DIMENSIONS = (
    ("dim_movie", "movie_sk", "movie_id"),
    ("dim_collection", "collection_sk", "collection_id"),
    ("dim_keyword", "keyword_sk", "keyword_id"),
)

# Referencias de un hecho o un bridge a una dimensión: tabla que referencia,
# columna, dimensión y clave sustituta de la dimensión.
REFERENCES = (
    ("fact_movie_snapshot", "movie_sk", "dim_movie", "movie_sk"),
    ("fact_movie_snapshot", "collection_sk", "dim_collection", "collection_sk"),
    ("fact_movie_snapshot", "original_language_sk", "dim_original_language", "original_language_sk"),
    ("fact_movie_snapshot", "status_sk", "dim_status", "status_sk"),
    ("fact_movie_snapshot", "rating_sk", "dim_rating", "rating_sk"),
    ("fact_movie_snapshot", "release_date_sk", "dim_date", "date_sk"),
    ("fact_movie_snapshot", "snapshot_date_sk", "dim_date", "date_sk"),
    ("fact_movie_enrichment", "enrichment_field_sk", "dim_enrichment_field", "enrichment_field_sk"),
    ("fact_movie_enrichment", "enrichment_code_sk", "dim_enrichment_code", "enrichment_code_sk"),
    ("bridge_movie_genre", "genre_sk", "dim_genre", "genre_sk"),
    ("bridge_movie_keyword", "keyword_sk", "dim_keyword", "keyword_sk"),
    ("bridge_movie_cast", "person_sk", "dim_person", "person_sk"),
    ("bridge_movie_production_company", "company_sk", "dim_production_company", "company_sk"),
    ("bridge_movie_production_country", "country_sk", "dim_production_country", "country_sk"),
    ("bridge_movie_spoken_language", "spoken_language_sk", "dim_spoken_language", "spoken_language_sk"),
)

# Referencias que pueden quedar en 0 a la espera de la corrida siguiente. Un
# rating nulo también lleva la clave 0, y no está pendiente de nada.
PENDING_REFERENCES = tuple(
    (table, column) for table, column, _dimension, _key in REFERENCES
    if not column.endswith("date_sk") and column != "rating_sk"
)


class SilverValidationError(Exception):
    """Silver incumple alguna de las propiedades que Gold da por ciertas.

    El mensaje dice cuántas comprobaciones fallaron y cuáles.
    """

    code = "VSILVER-001"

    def __str__(self) -> str:
        """El mensaje, precedido del código de error."""
        return f"[{self.code}] {super().__str__()}"


@dataclass(frozen=True)
class Check:
    """Una comprobación: su nombre y la consulta que cuenta sus incidencias."""

    name: str
    sql: str


def scd2_checks() -> list[Check]:
    """Versión vigente única y rangos coherentes en cada dimensión SCD2."""
    checks = []
    for table, surrogate_key, business_key in SCD2_DIMENSIONS:
        versions = f"{SILVER}.{table} WHERE {surrogate_key} > 0"
        checks.append(Check(
            f"{table}: claves con más de una versión vigente",
            f"SELECT count(*) FROM (SELECT {business_key} FROM {versions} AND is_current "
            f"GROUP BY {business_key} HAVING count(*) > 1)",
        ))
        checks.append(Check(
            f"{table}: is_current no cuadra con effective_to, o rango invertido",
            f"SELECT count(*) FROM {versions} "
            "AND (is_current <> (effective_to IS NULL) OR effective_to < effective_from)",
        ))
        checks.append(Check(
            f"{table}: rangos solapados entre versiones de una misma clave",
            "SELECT count(*) FROM (SELECT effective_from, "
            f"lag(effective_to) OVER (PARTITION BY {business_key} ORDER BY version_number) AS previous_to, "
            f"lag(version_number) OVER (PARTITION BY {business_key} ORDER BY version_number) AS previous_version "
            f"FROM {versions}) "
            "WHERE previous_version IS NOT NULL AND (previous_to IS NULL OR previous_to > effective_from)",
        ))
    return checks


def orphan_checks() -> list[Check]:
    """Toda clave sustituta de un hecho o de un bridge existe en su dimensión."""
    return [
        Check(
            f"{table}.{column}: claves huérfanas",
            f"SELECT count(*) FROM {SILVER}.{table} f LEFT ANTI JOIN {SILVER}.{dimension} d "
            f"ON f.{column} = d.{key}",
        )
        for table, column, dimension, key in REFERENCES
    ]


def count_incidents(spark: SparkSession, check: Check) -> int:
    """Ejecuta una comprobación y devuelve su número de incidencias."""
    return spark.sql(check.sql).first()[0]


def log_pending_references(spark: SparkSession) -> None:
    """Anota cuántas referencias siguen en 0, a la espera de repararse."""
    for table, column in PENDING_REFERENCES:
        pending = spark.sql(f"SELECT count(*) FROM {SILVER}.{table} WHERE {column} = 0").first()[0]
        if pending:
            LOG.warning("%s.%s: %d referencias en 0, pendientes de la corrida siguiente", table, column, pending)


def run_checks(spark: SparkSession) -> None:
    """Ejecuta todas las comprobaciones.

    Raises:
        SilverValidationError: si alguna encuentra incidencias.
    """
    failed = []
    checks = scd2_checks() + orphan_checks()
    for check in checks:
        incidents = count_incidents(spark, check)
        if incidents:
            LOG.error("%s: %d", check.name, incidents)
            failed.append(check.name)
        else:
            LOG.info("%s: 0", check.name)
    log_pending_references(spark)
    if failed:
        raise SilverValidationError(
            f"Fallaron {len(failed)} de las {len(checks)} comprobaciones de Silver: {'; '.join(failed)}. "
            "Causa probable: una corrida de bronze_to_silver.py que quedó a medias o un defecto del "
            "job. Gold no se ha recargado y conserva su último estado. Vuelve a lanzar "
            "bronze_to_silver.py; si se repite, revisa las tablas señaladas."
        )
    LOG.info("Silver pasa las %d comprobaciones", len(checks))


def main() -> int:
    """Punto de entrada. Devuelve el código de salida del proceso."""
    logging.basicConfig(
        level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    spark = SparkSession.builder.appName(APP_NAME).getOrCreate()
    # Los mensajes INFO de Spark tapan los del job; se dejan sus avisos y errores.
    spark.sparkContext.setLogLevel("WARN")
    try:
        run_checks(spark)
    except SilverValidationError as error:
        LOG.error("%s", error)
        return 1
    finally:
        spark.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
