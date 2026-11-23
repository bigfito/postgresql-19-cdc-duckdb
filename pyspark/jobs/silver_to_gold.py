"""Job PySpark #2: Silver -> Gold (diseño, secciones 32 y 33).

Lee el modelo dimensional de Silver y materializa los siete productos
analíticos de Gold, que son lo que consulta Superset a través de DuckDB.

Qué resuelve Gold para que no tenga que resolverlo quien consulta:

- **El historial.** Cada producto describe el catálogo tal como está ahora:
  las películas vivas, con su versión vigente y su último snapshot. Las
  películas borradas no aparecen.
- **Los nombres vigentes.** El título, el nombre de la colección y los géneros
  salen de la versión vigente, buscada por la clave de negocio. El hecho guarda
  la clave sustituta de la versión que estaba vigente al crear el snapshot, que
  puede estar ya cerrada (sección 19).
- **Las relaciones N:M.** Los productos por género y por persona traen, junto a
  los totales, las cifras repartidas con ``allocation_weight``, que se pueden
  sumar entre filas sin contar dos veces la misma película.

Estrategia de escritura (sección 32): recarga completa. Cada corrida recalcula
cada producto y reemplaza todas sus filas en un solo snapshot de Iceberg, sin
archivos de borrado.

Cómo se lanza (modo cliente, contra el clúster standalone)::

    spark-submit /opt/spark/jobs/silver_to_gold.py [--run-ts 2026-11-23T10:00:00+00:00]

``--run-ts`` es el timestamp lógico de la corrida; el DAG de Airflow pasa
``dag_run.run_after``. Si falta, se usa la hora actual.

A mano, desde la raíz del repositorio, en un contenedor temporal que hace de
driver::

    docker compose run --rm --no-deps spark-worker spark-submit /opt/spark/jobs/silver_to_gold.py

El job no usa UDF de Python: todo son expresiones de DataFrame.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import reduce

from pyspark.sql import Column, DataFrame, SparkSession, Window
from pyspark.sql import functions as F

LOG = logging.getLogger("silver_to_gold")

APP_NAME = "silver_to_gold"
SILVER = "lake.silver"
GOLD = "lake.gold"

# Tablas de Silver que lee el job. Si falta alguna, no se escribe nada.
SILVER_TABLES = (
    "dim_movie", "dim_collection", "dim_original_language", "dim_status", "dim_rating",
    "dim_genre", "dim_person", "dim_production_country", "dim_spoken_language",
    "dim_enrichment_field", "dim_enrichment_code",
    "fact_movie_snapshot", "fact_movie_enrichment",
    "bridge_movie_genre", "bridge_movie_cast",
)

# Dimensiones cuyos atributos salen de un archivo de referencia (sección 24).
REFERENCE_DIMENSIONS = (
    ("dim_original_language", "original_language_sk"),
    ("dim_status", "status_sk"),
    ("dim_rating", "rating_sk"),
    ("dim_production_country", "country_sk"),
    ("dim_spoken_language", "spoken_language_sk"),
    ("dim_enrichment_field", "enrichment_field_sk"),
    ("dim_enrichment_code", "enrichment_code_sk"),
)
UNMAPPED = "unmapped"

# Tramos de presupuesto de financial_performance: tope en dólares, orden y rótulo.
BUDGET_BANDS = (
    (1_000_000, 1, "< 1M"),
    (10_000_000, 2, "1M - 10M"),
    (50_000_000, 3, "10M - 50M"),
    (100_000_000, 4, "50M - 100M"),
)
TOP_BUDGET_BAND = (5, ">= 100M")

# Tipos de las cifras calculadas. Todos son tipos simples para DuckDB y Superset.
MONEY_TOTAL = "decimal(22,2)"
ROI = "decimal(28,4)"

AUDIT_COLUMN = "gold_processed_at timestamp"


# =============================================================================
# Errores
# =============================================================================

class GoldJobError(Exception):
    """Error previsto del job, con un código que identifica la causa.

    El mensaje dice qué pasó, cuál es la causa probable y qué hacer.
    """

    code = "GOLD-000"

    def __str__(self) -> str:
        """El mensaje, precedido del código de error."""
        return f"[{self.code}] {super().__str__()}"


class InvalidRunTimestampError(GoldJobError):
    """El argumento ``--run-ts`` no es una fecha y hora ISO 8601."""

    code = "GOLD-001"


class SilverTableMissingError(GoldJobError):
    """Falta una tabla de Silver; el job no escribe nada."""

    code = "GOLD-002"


# =============================================================================
# Columnas de los siete productos (sección 33)
# =============================================================================

MOVIE_CURRENT_OVERVIEW_COLUMNS = (
    "movie_id bigint", "imdb_id string", "title string", "original_title string",
    "release_date date", "release_year int", "release_month int", "release_decade int",
    "original_language_code string", "original_language_name string",
    "status_code string", "rating_code string",
    "collection_id bigint", "collection_name string",
    "primary_genre string", "genres string",
    "runtime_minutes int", "budget_usd decimal(18,2)", "revenue_usd decimal(18,2)",
    "profit_usd decimal(19,2)", f"roi_percentage {ROI}",
    "popularity decimal(10,3)", "user_score decimal(3,1)", "vote_average decimal(5,3)",
    "vote_count int",
    "genre_count int", "keyword_count int", "cast_count int", "company_count int",
    "country_count int", "spoken_language_count int",
    "has_collection boolean", "has_budget boolean", "has_revenue boolean",
    "has_homepage boolean", "adult boolean",
    "version_number int", "last_changed_at timestamp", AUDIT_COLUMN,
)

GENRE_PERFORMANCE_COLUMNS = (
    "genre_id bigint", "genre_name string", "movie_count int",
    "weighted_movie_count decimal(18,4)",
    f"total_budget_usd {MONEY_TOTAL}", f"total_revenue_usd {MONEY_TOTAL}",
    f"total_profit_usd {MONEY_TOTAL}",
    f"weighted_revenue_usd {MONEY_TOTAL}", f"weighted_profit_usd {MONEY_TOTAL}",
    f"roi_percentage {ROI}", "movies_with_financials int",
    "avg_popularity decimal(12,3)", "avg_vote_average decimal(5,3)",
    "avg_user_score decimal(4,2)", "avg_runtime_minutes decimal(6,1)", AUDIT_COLUMN,
)

COLLECTION_PERFORMANCE_COLUMNS = (
    "collection_id bigint", "collection_name string", "movie_count int",
    "first_release_date date", "last_release_date date",
    f"total_budget_usd {MONEY_TOTAL}", f"total_revenue_usd {MONEY_TOTAL}",
    f"total_profit_usd {MONEY_TOTAL}",
    f"roi_percentage {ROI}", "movies_with_financials int",
    "avg_popularity decimal(12,3)", "avg_vote_average decimal(5,3)",
    "avg_user_score decimal(4,2)", "avg_runtime_minutes decimal(6,1)",
    "total_vote_count bigint", AUDIT_COLUMN,
)

FINANCIAL_PERFORMANCE_COLUMNS = (
    "movie_id bigint", "title string", "release_date date", "release_year int",
    "release_decade int", "primary_genre string", "original_language_name string",
    "rating_code string", "collection_name string",
    "budget_usd decimal(18,2)", "revenue_usd decimal(18,2)", "profit_usd decimal(19,2)",
    f"roi_percentage {ROI}", "is_profitable boolean",
    "budget_band string", "budget_band_order int", "profit_rank int", AUDIT_COLUMN,
)

RELEASE_TRENDS_COLUMNS = (
    "period_start date", "release_year int", "release_month int", "release_decade int",
    "movie_count int",
    f"total_budget_usd {MONEY_TOTAL}", f"total_revenue_usd {MONEY_TOTAL}",
    f"total_profit_usd {MONEY_TOTAL}",
    f"roi_percentage {ROI}", "movies_with_financials int",
    "avg_popularity decimal(12,3)", "avg_vote_average decimal(5,3)",
    "avg_user_score decimal(4,2)", "avg_runtime_minutes decimal(6,1)", AUDIT_COLUMN,
)

CAST_ANALYSIS_COLUMNS = (
    "person_id bigint", "person_name string", "movie_count int", "top_billed_count int",
    "avg_billing_order decimal(6,2)",
    "first_release_date date", "last_release_date date", "career_span_years int",
    f"total_revenue_usd {MONEY_TOTAL}", f"weighted_revenue_usd {MONEY_TOTAL}",
    "avg_popularity decimal(12,3)", "avg_vote_average decimal(5,3)",
    "avg_user_score decimal(4,2)", AUDIT_COLUMN,
)

DATA_QUALITY_COVERAGE_COLUMNS = (
    "dataset string", "metric string", "total_count bigint", "covered_count bigint",
    "coverage_percentage decimal(5,2)", AUDIT_COLUMN,
)


# =============================================================================
# Contexto de la corrida
# =============================================================================

@dataclass
class JobContext:
    """Lo que comparten todos los pasos de una corrida.

    Attributes:
        spark: sesión de Spark.
        run_ts: timestamp lógico de la corrida, con zona horaria.
        movies: las películas vivas, con todo lo que usan los productos; se
            calcula una vez y se reutiliza.
        report: filas escritas en cada producto.
    """

    spark: SparkSession
    run_ts: datetime
    movies: DataFrame | None = None
    report: dict[str, int] = field(default_factory=dict)

    def silver(self, table: str) -> DataFrame:
        """Estado actual de una tabla de Silver."""
        return self.spark.table(f"{SILVER}.{table}")


@dataclass(frozen=True)
class Product:
    """Un producto de Gold.

    Attributes:
        table: nombre de la tabla, sin el namespace.
        columns: sus columnas, como ``"nombre tipo"``, en el orden de la tabla.
        build: función que calcula sus filas a partir de Silver.
    """

    table: str
    columns: tuple[str, ...]
    build: Callable[[JobContext], DataFrame]


# =============================================================================
# Utilidades
# =============================================================================

def conform(frame: DataFrame, columns: Sequence[str]) -> DataFrame:
    """Deja el DataFrame con las columnas, el orden y los tipos de la tabla."""
    selected = []
    for definition in columns:
        name, data_type = definition.split(None, 1)
        selected.append(F.col(name).cast(data_type).alias(name))
    return frame.select(*selected)


def real_rows(frame: DataFrame, surrogate_key: str) -> DataFrame:
    """Filas de una dimensión sin las especiales 0 (Unknown) y -1 (Not Applicable)."""
    return frame.where(F.col(surrogate_key) > 0)


def has_financials() -> Column:
    """La película trae presupuesto y recaudación."""
    return F.col("has_budget") & F.col("has_revenue")


def financial_aggregates() -> list[Column]:
    """Totales de dinero de un grupo de películas.

    Los valores ausentes no cuentan como cero: cada total suma solo las
    películas que traen el dato. El ROI del grupo se calcula sobre las
    películas con presupuesto mayor que cero y recaudación, igual que el de
    cada película (sección 27).
    """
    has_roi = (F.col("budget_usd") > 0) & F.col("revenue_usd").isNotNull()
    return [
        F.sum("budget_usd").alias("total_budget_usd"),
        F.sum("revenue_usd").alias("total_revenue_usd"),
        F.sum("profit_usd").alias("total_profit_usd"),
        (F.sum(F.when(has_roi, F.col("profit_usd"))) / F.sum(F.when(has_roi, F.col("budget_usd"))) * 100)
        .alias("roi_percentage"),
        F.count(F.when(has_financials(), True)).alias("movies_with_financials"),
    ]


def audience_aggregates() -> list[Column]:
    """Promedios de popularidad, votos, puntuación y duración de un grupo."""
    return [
        F.avg("popularity").alias("avg_popularity"),
        F.avg("vote_average").alias("avg_vote_average"),
        F.avg("user_score").alias("avg_user_score"),
        F.avg("runtime_minutes").alias("avg_runtime_minutes"),
    ]


def percentage(part: Column, total: Column) -> Column:
    """``part`` como porcentaje de ``total``; nulo si ``total`` es cero."""
    return F.when(total > 0, part / total * 100)


# =============================================================================
# Películas vivas: la base de todos los productos
# =============================================================================

def latest_snapshots(ctx: JobContext) -> DataFrame:
    """El último snapshot de cada película: el de mayor ``movie_snapshot_sk``."""
    newest_first = Window.partitionBy("movie_id").orderBy(F.col("movie_snapshot_sk").desc())
    return (
        ctx.silver("fact_movie_snapshot")
        .withColumn("_rank", F.row_number().over(newest_first))
        .where(F.col("_rank") == 1)
        .drop("_rank")
    )


def collection_names(ctx: JobContext) -> DataFrame:
    """``collection_sk`` -> ``collection_id`` y nombre vigente de la colección.

    El hecho guarda la clave sustituta de la versión que estaba vigente al
    crear el snapshot. El nombre se toma de la versión vigente ahora, buscada
    por ``collection_id``. Las filas especiales conservan su rótulo.
    """
    versions = ctx.silver("dim_collection")
    current = real_rows(versions, "collection_sk").where(F.col("is_current")).select(
        F.col("collection_id").alias("_current_id"), F.col("collection_name").alias("_current_name")
    )
    return versions.join(current, F.col("collection_id") == F.col("_current_id"), "left").select(
        "collection_sk", "collection_id",
        F.coalesce("_current_name", "collection_name").alias("collection_name"),
    )


def movie_genres(ctx: JobContext) -> DataFrame:
    """Géneros vigentes de cada película: el primero y la lista completa.

    La lista va en el orden de ``source_position``, como texto separado por
    comas: un tipo simple que Superset puede mostrar y filtrar.
    """
    genres = real_rows(ctx.silver("dim_genre"), "genre_sk").select("genre_sk", "genre_name")
    ordered = F.sort_array(F.collect_list(F.struct("source_position", "genre_name")))
    return (
        ctx.silver("bridge_movie_genre").where(F.col("is_current"))
        .join(F.broadcast(genres), "genre_sk")
        .groupBy("movie_id")
        .agg(ordered.alias("_genres"))
        .select(
            "movie_id",
            F.col("_genres")[0]["genre_name"].alias("primary_genre"),
            F.array_join(F.transform("_genres", lambda genre: genre["genre_name"]), ", ").alias("genres"),
        )
    )


def current_movies(ctx: JobContext) -> DataFrame:
    """Una fila por película viva, con su versión vigente y su último snapshot.

    Una película está viva si tiene versión vigente en ``dim_movie`` y su
    último snapshot no es de borrado. Los atributos descriptivos salen de la
    versión vigente; las medidas y los conteos, del último snapshot.
    """
    versions = real_rows(ctx.silver("dim_movie"), "movie_sk").where(F.col("is_current")).select(
        "movie_id", "imdb_id", "title", "original_title", "overview", "tagline",
        "release_date", "release_year", "release_month", "release_decade",
        "homepage", "poster_path", "backdrop_path", "adult", "version_number",
        F.col("effective_from").alias("_version_from"),
    )
    snapshots = latest_snapshots(ctx).where(~F.col("is_deleted")).select(
        "movie_id", "collection_sk", "original_language_sk", "status_sk", "rating_sk",
        "runtime_minutes", "budget_usd", "revenue_usd", "profit_usd", "roi_percentage",
        "popularity", "user_score", "vote_average", "vote_count",
        "genre_count", "keyword_count", "cast_count", "company_count", "country_count",
        "spoken_language_count", "has_collection", "has_budget", "has_revenue", "snapshot_at",
    )
    languages = ctx.silver("dim_original_language").select(
        "original_language_sk",
        F.col("language_code").alias("original_language_code"),
        F.col("language_name").alias("original_language_name"),
    )
    statuses = ctx.silver("dim_status").select("status_sk", "status_code")
    ratings = ctx.silver("dim_rating").select("rating_sk", "rating_code")
    return (
        versions.join(snapshots, "movie_id")
        .join(F.broadcast(languages), "original_language_sk", "left")
        .join(F.broadcast(statuses), "status_sk", "left")
        .join(F.broadcast(ratings), "rating_sk", "left")
        .join(collection_names(ctx), "collection_sk", "left")
        .join(movie_genres(ctx), "movie_id", "left")
        # Del atributo vigente, no del snapshot: un cambio de homepage crea
        # versión en dim_movie y no crea snapshot.
        .withColumn("has_homepage", F.col("homepage").isNotNull())
        .withColumn("last_changed_at", F.greatest("_version_from", "snapshot_at"))
    )


# =============================================================================
# Los siete productos
# =============================================================================

def movie_current_overview(ctx: JobContext) -> DataFrame:
    """Una fila por película viva: la ficha completa para explorar el catálogo."""
    return ctx.movies


def genre_performance(ctx: JobContext) -> DataFrame:
    """Una fila por género, con las películas vivas que lo tienen ahora.

    Una película con tres géneros cuenta en los tres: los ``total_*`` de dos
    géneros no se pueden sumar. Las columnas ``weighted_*`` reparten cada
    película entre sus géneros con ``allocation_weight`` y sí se pueden sumar.
    """
    genres = real_rows(ctx.silver("dim_genre"), "genre_sk").select("genre_sk", "genre_id", "genre_name")
    weight = F.col("allocation_weight")
    return (
        ctx.silver("bridge_movie_genre").where(F.col("is_current"))
        .join(F.broadcast(genres), "genre_sk")
        .join(ctx.movies, "movie_id")
        .groupBy("genre_id", "genre_name")
        .agg(
            F.count("*").alias("movie_count"),
            F.sum(weight).alias("weighted_movie_count"),
            *financial_aggregates(),
            F.sum(F.col("revenue_usd") * weight).alias("weighted_revenue_usd"),
            F.sum(F.col("profit_usd") * weight).alias("weighted_profit_usd"),
            *audience_aggregates(),
        )
    )


def collection_performance(ctx: JobContext) -> DataFrame:
    """Una fila por colección con al menos una película viva."""
    return (
        ctx.movies.where(F.col("collection_id").isNotNull())
        .groupBy("collection_id", "collection_name")
        .agg(
            F.count("*").alias("movie_count"),
            F.min("release_date").alias("first_release_date"),
            F.max("release_date").alias("last_release_date"),
            *financial_aggregates(),
            *audience_aggregates(),
            F.sum("vote_count").alias("total_vote_count"),
        )
    )


def budget_band() -> tuple[Column, Column]:
    """Tramo de presupuesto de una película: su rótulo y su orden."""
    budget = F.col("budget_usd")
    top_order, top_label = TOP_BUDGET_BAND
    label, order = F.lit(top_label), F.lit(top_order)
    for limit, band_order, band_label in reversed(BUDGET_BANDS):
        label = F.when(budget < limit, band_label).otherwise(label)
        order = F.when(budget < limit, band_order).otherwise(order)
    return label.alias("budget_band"), order.alias("budget_band_order")


def financial_performance(ctx: JobContext) -> DataFrame:
    """Una fila por película viva que trae presupuesto y recaudación.

    ``profit_rank`` ordena por ganancia, de mayor a menor; el ``movie_id``
    desempata para que el orden sea el mismo en cada corrida.
    """
    by_profit = Window.orderBy(F.col("profit_usd").desc(), F.col("movie_id"))
    return ctx.movies.where(has_financials()).select(
        "movie_id", "title", "release_date", "release_year", "release_decade", "primary_genre",
        "original_language_name", "rating_code", "collection_name",
        "budget_usd", "revenue_usd", "profit_usd", "roi_percentage",
        (F.col("profit_usd") > 0).alias("is_profitable"),
        *budget_band(),
        F.row_number().over(by_profit).alias("profit_rank"),
    )


def release_trends(ctx: JobContext) -> DataFrame:
    """Una fila por mes de estreno; ``period_start`` es el primer día del mes."""
    return (
        ctx.movies
        .groupBy("release_year", "release_month", "release_decade")
        .agg(F.count("*").alias("movie_count"), *financial_aggregates(), *audience_aggregates())
        .withColumn("period_start", F.make_date("release_year", "release_month", F.lit(1)))
    )


def cast_analysis(ctx: JobContext) -> DataFrame:
    """Una fila por persona con al menos una película viva en su reparto.

    ``top_billed_count`` cuenta las películas en las que la persona encabeza
    el reparto, es decir, tiene el menor ``billing_order`` de la película.
    ``weighted_revenue_usd`` reparte la recaudación de cada película entre su
    reparto con ``allocation_weight``.
    """
    people = real_rows(ctx.silver("dim_person"), "person_sk").select("person_sk", "person_id", "person_name")
    first_billing = F.min("billing_order").over(Window.partitionBy("movie_id"))
    return (
        ctx.silver("bridge_movie_cast").where(F.col("is_current"))
        .withColumn("_is_top_billed", F.col("billing_order") == first_billing)
        .join(people, "person_sk")
        .join(ctx.movies, "movie_id")
        .groupBy("person_id", "person_name")
        .agg(
            F.count("*").alias("movie_count"),
            F.count(F.when(F.col("_is_top_billed"), True)).alias("top_billed_count"),
            F.avg("billing_order").alias("avg_billing_order"),
            F.min("release_date").alias("first_release_date"),
            F.max("release_date").alias("last_release_date"),
            F.sum("revenue_usd").alias("total_revenue_usd"),
            F.sum(F.col("revenue_usd") * F.col("allocation_weight")).alias("weighted_revenue_usd"),
            *audience_aggregates()[:3],
        )
        .withColumn("career_span_years", F.year("last_release_date") - F.year("first_release_date"))
    )


def movie_attribute_coverage(ctx: JobContext) -> DataFrame:
    """Cuántas películas vivas traen cada atributo opcional."""
    checks = {
        "imdb_id": F.col("imdb_id").isNotNull(),
        "overview": F.col("overview").isNotNull(),
        "tagline": F.col("tagline").isNotNull(),
        "homepage": F.col("has_homepage"),
        "poster_path": F.col("poster_path").isNotNull(),
        "backdrop_path": F.col("backdrop_path").isNotNull(),
        "runtime_minutes": F.col("runtime_minutes").isNotNull(),
        "budget_usd": F.col("has_budget"),
        "revenue_usd": F.col("has_revenue"),
        "user_score": F.col("user_score").isNotNull(),
        "vote_average": F.col("vote_average").isNotNull(),
        # Un rating nulo queda con la clave 0 en el hecho (sección 30).
        "rating_code": F.col("rating_sk") > 0,
        "collection": F.col("has_collection"),
    }
    totals = ctx.movies.agg(
        F.count("*").alias("total_count"),
        *[F.count(F.when(condition, True)).alias(name) for name, condition in checks.items()],
    )
    per_metric = F.explode(F.array(*[
        F.struct(F.lit(name).alias("metric"), F.col(name).alias("covered_count")) for name in checks
    ]))
    return totals.select(F.lit("movie").alias("dataset"), "total_count", per_metric.alias("_metric")).select(
        "dataset", F.col("_metric.metric").alias("metric"), "total_count",
        F.col("_metric.covered_count").alias("covered_count"),
    )


def reference_coverage(ctx: JobContext) -> DataFrame:
    """Cuántos valores de cada catálogo tienen equivalencia en su archivo de referencia."""
    frames = []
    for table, surrogate_key in REFERENCE_DIMENSIONS:
        frames.append(real_rows(ctx.silver(table), surrogate_key).agg(
            F.lit(table).alias("dataset"),
            F.lit("reference_mapped").alias("metric"),
            F.count("*").alias("total_count"),
            F.count(F.when(F.col("quality_status") != UNMAPPED, True)).alias("covered_count"),
        ))
    return reduce(DataFrame.unionByName, frames)


def provenance_coverage(ctx: JobContext) -> DataFrame:
    """Cuántas películas vivas tienen procedencia registrada para cada campo."""
    fields = real_rows(ctx.silver("dim_enrichment_field"), "enrichment_field_sk").select(
        "enrichment_field_sk", "field_name"
    )
    alive = ctx.movies.select("movie_id")
    covered = (
        ctx.silver("fact_movie_enrichment").where(F.col("is_current"))
        .join(alive, "movie_id")
        .groupBy("enrichment_field_sk")
        .agg(F.countDistinct("movie_id").alias("covered_count"))
    )
    total = alive.agg(F.count("*").alias("total_count"))
    return fields.join(covered, "enrichment_field_sk", "left").crossJoin(total).select(
        F.lit("movie_enrichment").alias("dataset"),
        F.col("field_name").alias("metric"),
        "total_count",
        F.coalesce("covered_count", F.lit(0)).alias("covered_count"),
    )


def data_quality_coverage(ctx: JobContext) -> DataFrame:
    """Cobertura de los datos, una fila por conjunto de datos y métrica.

    Tres grupos: atributos opcionales de las películas vivas (``movie``),
    equivalencias de cada catálogo con su archivo de referencia (el nombre de
    la dimensión) y procedencia por campo (``movie_enrichment``).
    """
    rows = reduce(DataFrame.unionByName, [
        movie_attribute_coverage(ctx), reference_coverage(ctx), provenance_coverage(ctx),
    ])
    return rows.withColumn("coverage_percentage", percentage(F.col("covered_count"), F.col("total_count")))


PRODUCTS = (
    Product("movie_current_overview", MOVIE_CURRENT_OVERVIEW_COLUMNS, movie_current_overview),
    Product("genre_performance", GENRE_PERFORMANCE_COLUMNS, genre_performance),
    Product("collection_performance", COLLECTION_PERFORMANCE_COLUMNS, collection_performance),
    Product("financial_performance", FINANCIAL_PERFORMANCE_COLUMNS, financial_performance),
    Product("release_trends", RELEASE_TRENDS_COLUMNS, release_trends),
    Product("cast_analysis", CAST_ANALYSIS_COLUMNS, cast_analysis),
    Product("data_quality_coverage", DATA_QUALITY_COVERAGE_COLUMNS, data_quality_coverage),
)


# =============================================================================
# Escritura en Gold
# =============================================================================

def write_product(ctx: JobContext, product: Product) -> None:
    """Calcula un producto y reemplaza con él todas las filas de su tabla.

    La primera vez crea la tabla, en formato Iceberg v2. Después sobrescribe
    todas sus filas en un solo snapshot: quien consulta ve la carga anterior o
    la nueva, nunca una mezcla (sección 32). Cada carga deja un único archivo
    de datos por tabla.
    """
    name = f"{GOLD}.{product.table}"
    # Una sola partición: el producto más grande tiene unas cien mil filas, y
    # un archivo por tabla es lo que menos peticiones cuesta a quien la lee.
    rows = conform(
        product.build(ctx).withColumn("gold_processed_at", F.lit(ctx.run_ts)), product.columns
    ).coalesce(1).cache()
    try:
        count = rows.count()
        if ctx.spark.catalog.tableExists(name):
            rows.writeTo(name).overwrite(F.lit(True))
        else:
            rows.writeTo(name).using("iceberg").tableProperty("format-version", "2").create()
            LOG.info("%s: tabla creada", product.table)
    finally:
        rows.unpersist()
    ctx.report[product.table] = count
    LOG.info("%s: %d filas", product.table, count)


def require_silver_tables(ctx: JobContext) -> None:
    """Comprueba que Silver tiene todas las tablas que el job lee.

    Raises:
        SilverTableMissingError: si falta alguna.
    """
    missing = [table for table in SILVER_TABLES if not ctx.spark.catalog.tableExists(f"{SILVER}.{table}")]
    if missing:
        raise SilverTableMissingError(
            f"Faltan en Silver las tablas {missing}. Causa probable: bronze_to_silver.py todavía "
            "no ha terminado bien ninguna corrida. Gold no se ha modificado; lanza primero "
            "bronze_to_silver.py y después este job."
        )


# =============================================================================
# Orquestación
# =============================================================================

def run_job(ctx: JobContext) -> None:
    """Ejecuta la corrida completa: prepara las películas vivas y escribe los productos."""
    started = time.monotonic()
    require_silver_tables(ctx)
    ctx.movies = current_movies(ctx).cache()
    try:
        LOG.info("Películas vivas: %d", ctx.movies.count())
        for product in PRODUCTS:
            write_product(ctx, product)
    finally:
        ctx.movies.unpersist()
    LOG.info("Corrida terminada en %.1f s; productos recargados: %d", time.monotonic() - started, len(ctx.report))


def parse_run_timestamp(value: str | None) -> datetime:
    """Convierte ``--run-ts`` en una fecha y hora con zona.

    Sin valor, devuelve la hora actual en UTC: es el caso de una corrida
    lanzada a mano. Un valor sin zona se toma como UTC.

    Raises:
        InvalidRunTimestampError: si el valor no es ISO 8601.
    """
    if value is None:
        return datetime.now(UTC)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise InvalidRunTimestampError(
            f"El valor de --run-ts, {value!r}, no es una fecha y hora ISO 8601. "
            "Usa una forma como 2026-11-23T10:00:00+00:00, que es la que entrega dag_run.run_after."
        ) from error
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Lee los argumentos de la línea de comandos."""
    parser = argparse.ArgumentParser(description="Recarga los productos de Gold a partir de Silver.")
    parser.add_argument(
        "--run-ts",
        help="Timestamp lógico de la corrida, en ISO 8601 (dag_run.run_after). Por defecto, la hora actual.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Punto de entrada. Devuelve el código de salida del proceso."""
    logging.basicConfig(
        level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    args = parse_arguments(argv)
    try:
        run_ts = parse_run_timestamp(args.run_ts)
    except InvalidRunTimestampError as error:
        LOG.error("%s", error)
        return 2

    spark = SparkSession.builder.appName(APP_NAME).getOrCreate()
    # Los mensajes INFO de Spark tapan los del job; se dejan sus avisos y errores.
    spark.sparkContext.setLogLevel("WARN")
    LOG.info("Corrida con timestamp lógico %s", run_ts.isoformat())
    try:
        run_job(JobContext(spark=spark, run_ts=run_ts))
    except GoldJobError as error:
        LOG.error("%s", error)
        return 1
    finally:
        spark.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
