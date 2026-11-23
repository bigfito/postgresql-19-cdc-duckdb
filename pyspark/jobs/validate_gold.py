"""Validación de Gold, quinta tarea del DAG (diseño, secciones 18 y 33).

Comprueba, después de `silver_to_gold.py`, que los siete productos sirven para
consultarse:

- cada tabla existe y tiene al menos una fila;
- sus columnas clave no traen nulos ni valores repetidos.

Si algo falla, el job termina con código 1 y el DAG queda en error. Gold no se
revierte: el fallo avisa de que la última recarga no es fiable.

Cómo se lanza::

    spark-submit /opt/spark/jobs/validate_gold.py
"""

from __future__ import annotations

import logging
import sys

from pyspark.sql import SparkSession

LOG = logging.getLogger("validate_gold")

APP_NAME = "validate_gold"
GOLD = "lake.gold"

# Producto -> columnas que identifican cada fila. No pueden ser nulas ni
# repetirse.
PRODUCT_KEYS = {
    "movie_current_overview": ("movie_id",),
    "genre_performance": ("genre_id",),
    "collection_performance": ("collection_id",),
    "financial_performance": ("movie_id",),
    "release_trends": ("period_start",),
    "cast_analysis": ("person_id",),
    "data_quality_coverage": ("dataset", "metric"),
}
MINIMUM_ROWS = 1


class GoldValidationError(Exception):
    """Algún producto de Gold falta, está vacío o tiene claves inválidas.

    El mensaje dice cuántos problemas hay y cuáles.
    """

    code = "VGOLD-001"

    def __str__(self) -> str:
        """El mensaje, precedido del código de error."""
        return f"[{self.code}] {super().__str__()}"


def product_problems(spark: SparkSession, product: str, keys: tuple[str, ...]) -> list[str]:
    """Problemas de un producto; lista vacía si está bien."""
    table = f"{GOLD}.{product}"
    if not spark.catalog.tableExists(table):
        return [f"{product}: la tabla no existe"]
    key_list = ", ".join(keys)
    any_null = " OR ".join(f"{key} IS NULL" for key in keys)
    rows, null_keys, repeated_keys = spark.sql(
        f"SELECT (SELECT count(*) FROM {table}), "
        f"(SELECT count(*) FROM {table} WHERE {any_null}), "
        f"(SELECT count(*) FROM (SELECT {key_list} FROM {table} GROUP BY {key_list} HAVING count(*) > 1))"
    ).first()
    problems = []
    if rows < MINIMUM_ROWS:
        problems.append(f"{product}: {rows} filas, menos del mínimo de {MINIMUM_ROWS}")
    if null_keys:
        problems.append(f"{product}: {null_keys} filas con {key_list} nulo")
    if repeated_keys:
        problems.append(f"{product}: {repeated_keys} valores de {key_list} repetidos")
    if not problems:
        LOG.info("%s: %d filas, claves sin nulos ni repetidos", product, rows)
    return problems


def run_checks(spark: SparkSession) -> None:
    """Comprueba los siete productos.

    Raises:
        GoldValidationError: si alguno tiene problemas.
    """
    problems = []
    for product, keys in PRODUCT_KEYS.items():
        found = product_problems(spark, product, keys)
        for problem in found:
            LOG.error("%s", problem)
        problems.extend(found)
    if problems:
        raise GoldValidationError(
            f"Gold tiene {len(problems)} problemas: {'; '.join(problems)}. Causa probable: "
            "silver_to_gold.py no terminó bien, o Silver todavía no tiene películas. Revisa el log "
            "de la tarea silver_to_gold de esta corrida; la corrida siguiente recarga Gold completo."
        )
    LOG.info("Gold pasa las comprobaciones en sus %d productos", len(PRODUCT_KEYS))


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
    except GoldValidationError as error:
        LOG.error("%s", error)
        return 1
    finally:
        spark.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
