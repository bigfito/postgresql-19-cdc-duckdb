"""Job PySpark #1: Bronze -> Silver (diseño, secciones 19 a 31).

Lee el estado actual de las 20 tablas Bronze, tombstones incluidos, y mantiene
el modelo dimensional de Silver: 14 dimensiones, 2 hechos y 6 bridges.

Propiedades que el job cumple (sección 19):

- **Idempotente.** Cada tabla se compara con lo que ya hay en Silver y solo se
  escribe cuando hay diferencias. Una corrida sin cambios en Bronze no crea
  versiones, snapshots ni filas, y tampoco snapshots de Iceberg.
- **Determinístico.** Las fechas de vigencia salen del dato (``updated_at`` o
  ``cdc_op_ts``); la hora de la corrida solo se usa cuando el dato no trae
  ninguna. Las claves sustitutas se numeran con ``max + row_number``.
- **Tolerante a lecturas no atómicas.** Flink publica cada tabla Bronze por
  separado. Una referencia cuya dimensión todavía no llegó queda con clave 0 y
  se repara en la corrida siguiente.

Cómo se lanza (modo cliente, contra el clúster standalone)::

    spark-submit /opt/spark/jobs/bronze_to_silver.py [--run-ts 2026-11-23T10:00:00+00:00]

``--run-ts`` es el timestamp lógico de la corrida; el DAG de Airflow pasa
``dag_run.run_after``. Si falta, se usa la hora actual.

A mano, desde la raíz del repositorio, en un contenedor temporal que hace de
driver::

    docker compose run --rm --no-deps spark-worker spark-submit /opt/spark/jobs/bronze_to_silver.py

El job no usa UDF de Python: todo son expresiones de DataFrame y SQL. Tampoco
usa ``cache()``: el origen de un ``MERGE INTO`` no puede ser un DataFrame en
caché (Spark 4.1.4 con Iceberg 1.12.0), así que los resultados intermedios se
fijan con ``localCheckpoint()``.
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import reduce
from pathlib import Path

from pyspark.errors import AnalysisException
from pyspark.sql import Column, DataFrame, SparkSession, Window
from pyspark.sql import functions as F

LOG = logging.getLogger("bronze_to_silver")

APP_NAME = "bronze_to_silver"
BRONZE = "lake.bronze"
SILVER = "lake.silver"

# Claves sustitutas reservadas (sección 30).
UNKNOWN_SK = 0
NOT_APPLICABLE_SK = -1
SPECIAL_ROWS = ((UNKNOWN_SK, "Unknown"), (NOT_APPLICABLE_SK, "Not Applicable"))

# Valor de cdc_op_type que deja Flink CDC en una fila borrada (sección 17).
TOMBSTONE = "-D"

# Calendario de dim_date. Cubre las fechas de estreno del dataset (desde 1902)
# y deja margen para las fechas de snapshot.
CALENDAR_START = "1900-01-01"
CALENDAR_END = "2099-12-31"
# Día de la semana que devuelve weekday() para el sábado; el lunes es 0.
SATURDAY = 5

# allocation_weight = 1 / n. Decimal y no double: es exacto al comparar y es un
# tipo simple para DuckDB y Superset.
WEIGHT_TYPE = "decimal(12,10)"

# Separador y marca de nulo al calcular hashes: dos caracteres de control que
# no aparecen en los datos, para que ('a', NULL) y (NULL, 'a') no coincidan.
HASH_SEPARATOR = "\u001f"
HASH_NULL = "\u0000"

# Acciones de un conjunto de cambios. Cada fila del conjunto lleva una en la
# columna _action y el MERGE decide con ella qué hacer.
INSERT = "insert"
UPDATE = "update"
CLOSE = "close"
DELETE = "delete"
ACTION_LABELS = {INSERT: "altas", UPDATE: "actualizaciones", CLOSE: "cierres", DELETE: "bajas"}

# Las 20 tablas Bronze, en el orden en que se fija su snapshot: primero la
# película, después sus relaciones y al final las entidades y los catálogos
# que estas referencian. Así, si Flink publica un checkpoint mientras se fijan
# los snapshots, lo más probable es que la tabla referenciada sea la más
# reciente y la referencia se resuelva sin pasar por la clave 0.
BRONZE_TABLES = (
    "movie",
    "movie_collection", "movie_genre", "movie_keyword", "movie_cast",
    "movie_production_company", "movie_production_country", "movie_spoken_language",
    "movie_enrichment",
    "collection", "genre", "keyword", "person", "production_company",
    "production_country", "spoken_language",
    "original_language", "movie_status", "content_rating", "enrichment_field",
)


# =============================================================================
# Errores
# =============================================================================

class SilverJobError(Exception):
    """Error previsto del job, con un código que identifica la causa.

    El mensaje dice qué pasó, cuál es la causa probable y qué hacer.
    """

    code = "SILVER-000"

    def __str__(self) -> str:
        """El mensaje, precedido del código de error."""
        return f"[{self.code}] {super().__str__()}"


class InvalidRunTimestampError(SilverJobError):
    """El argumento ``--run-ts`` no es una fecha y hora ISO 8601."""

    code = "SILVER-001"


class BronzeTableMissingError(SilverJobError):
    """Falta una tabla Bronze; el job no escribe nada (sección 38)."""

    code = "SILVER-002"


class ReferenceDataError(SilverJobError):
    """Un archivo de ``pyspark/reference/`` falta o no tiene la forma esperada."""

    code = "SILVER-003"


# =============================================================================
# Definición de las tablas de Silver
# =============================================================================

AUDIT_COLUMNS = ("source_updated_at timestamp", "silver_processed_at timestamp")
SCD2_COLUMNS = (
    "effective_from timestamp", "effective_to timestamp", "is_current boolean",
    "version_number int", "attribute_hash string", *AUDIT_COLUMNS,
)


def column_names(definitions: Sequence[str]) -> list[str]:
    """Nombres de una lista de columnas escritas como ``"nombre tipo"``."""
    return [definition.split(None, 1)[0] for definition in definitions]


@dataclass(frozen=True)
class Dimension:
    """Una dimensión de Silver, Tipo 1 o SCD2 (secciones 20 a 25 y 29).

    Attributes:
        table: nombre de la tabla, sin el namespace.
        surrogate_key: columna de la clave sustituta.
        business_key: columna de la clave de negocio.
        attributes: clave de negocio y atributos, como ``"nombre tipo"``, en el
            orden de la tabla.
        label_columns: columnas de texto que en las filas especiales 0 y -1
            llevan el rótulo «Unknown» o «Not Applicable».
        scd2: ``True`` si guarda historial con SCD Type 2.
    """

    table: str
    surrogate_key: str
    business_key: str
    attributes: tuple[str, ...]
    label_columns: tuple[str, ...]
    scd2: bool = False

    @property
    def columns(self) -> tuple[str, ...]:
        """Todas las columnas de la tabla, como ``"nombre tipo"``."""
        technical = SCD2_COLUMNS if self.scd2 else AUDIT_COLUMNS
        return (f"{self.surrogate_key} bigint", *self.attributes, *technical)

    @property
    def descriptive(self) -> list[str]:
        """Atributos que se comparan para detectar un cambio."""
        return [name for name in column_names(self.attributes) if name != self.business_key]


@dataclass(frozen=True)
class Bridge:
    """Un bridge N:M entre película y una dimensión (sección 28).

    Attributes:
        table: nombre de la tabla, sin el namespace.
        relation: tabla Bronze de la relación.
        position: columna de orden, ``source_position`` o ``billing_order``.
        dimension: dimensión del otro extremo; la relación Bronze la referencia
            por su clave de negocio.
    """

    table: str
    relation: str
    position: str
    dimension: Dimension

    @property
    def columns(self) -> tuple[str, ...]:
        """Todas las columnas de la tabla, como ``"nombre tipo"``."""
        return (
            "movie_id bigint", f"{self.dimension.surrogate_key} bigint", f"{self.position} int",
            f"allocation_weight {WEIGHT_TYPE}", "effective_from timestamp",
            "effective_to timestamp", "is_current boolean",
        )


DIM_DATE_COLUMNS = (
    "date_sk bigint", "calendar_date date", "day_number int", "day_name string",
    "day_of_week int", "week_of_year int", "month_number int", "month_name string",
    "quarter_number int", "year_number int", "decade_number int", "is_weekend boolean",
)

DIM_MOVIE = Dimension(
    table="dim_movie", surrogate_key="movie_sk", business_key="movie_id", scd2=True,
    attributes=(
        "movie_id bigint", "imdb_id string", "title string", "original_title string",
        "overview string", "plot string", "tagline string", "release_date date",
        "release_year int", "release_month int", "release_decade int", "homepage string",
        "poster_path string", "backdrop_path string", "adult boolean", "video boolean",
    ),
    label_columns=("title", "original_title"),
)
DIM_COLLECTION = Dimension(
    table="dim_collection", surrogate_key="collection_sk", business_key="collection_id", scd2=True,
    attributes=(
        "collection_id bigint", "collection_name string",
        "canonical_poster_path string", "canonical_backdrop_path string",
    ),
    label_columns=("collection_name",),
)
DIM_KEYWORD = Dimension(
    table="dim_keyword", surrogate_key="keyword_sk", business_key="keyword_id", scd2=True,
    attributes=("keyword_id bigint", "keyword_name string"),
    label_columns=("keyword_name",),
)
DIM_ORIGINAL_LANGUAGE = Dimension(
    table="dim_original_language", surrogate_key="original_language_sk", business_key="language_code",
    attributes=(
        "language_code string", "language_name string", "is_tmdb_specific boolean",
        "quality_status string",
    ),
    label_columns=("language_code", "language_name"),
)
DIM_STATUS = Dimension(
    table="dim_status", surrogate_key="status_sk", business_key="status_code",
    attributes=("status_code string", "status_description string", "quality_status string"),
    label_columns=("status_code", "status_description"),
)
DIM_RATING = Dimension(
    table="dim_rating", surrogate_key="rating_sk", business_key="rating_code",
    attributes=(
        "rating_code string", "rating_system string", "rating_description string",
        "quality_status string",
    ),
    label_columns=("rating_code", "rating_description"),
)
DIM_GENRE = Dimension(
    table="dim_genre", surrogate_key="genre_sk", business_key="genre_id",
    attributes=("genre_id bigint", "genre_name string"),
    label_columns=("genre_name",),
)
DIM_PERSON = Dimension(
    table="dim_person", surrogate_key="person_sk", business_key="person_id",
    attributes=("person_id bigint", "person_name string"),
    label_columns=("person_name",),
)
DIM_PRODUCTION_COMPANY = Dimension(
    table="dim_production_company", surrogate_key="company_sk", business_key="company_id",
    attributes=("company_id bigint", "company_name string"),
    label_columns=("company_name",),
)
DIM_PRODUCTION_COUNTRY = Dimension(
    table="dim_production_country", surrogate_key="country_sk", business_key="country_id",
    attributes=(
        "country_id bigint", "source_country_name string", "standard_country_name string",
        "country_code string", "quality_status string",
    ),
    label_columns=("source_country_name", "standard_country_name"),
)
DIM_SPOKEN_LANGUAGE = Dimension(
    table="dim_spoken_language", surrogate_key="spoken_language_sk", business_key="spoken_language_id",
    attributes=(
        "spoken_language_id bigint", "source_language_name string",
        "standard_language_name string", "language_code string", "quality_status string",
    ),
    label_columns=("source_language_name", "standard_language_name"),
)
DIM_ENRICHMENT_FIELD = Dimension(
    table="dim_enrichment_field", surrogate_key="enrichment_field_sk", business_key="field_name",
    attributes=("field_name string", "field_description string", "quality_status string"),
    label_columns=("field_name", "field_description"),
)
DIM_ENRICHMENT_CODE = Dimension(
    table="dim_enrichment_code", surrogate_key="enrichment_code_sk", business_key="code",
    attributes=(
        "code string", "source_system string", "source_family string",
        "source_date_text string", "currency_code string", "currency_year int",
        "qualifier string", "quality_status string",
    ),
    label_columns=("code",),
)

DIMENSIONS = (
    DIM_ORIGINAL_LANGUAGE, DIM_STATUS, DIM_RATING, DIM_GENRE, DIM_PERSON,
    DIM_PRODUCTION_COMPANY, DIM_PRODUCTION_COUNTRY, DIM_SPOKEN_LANGUAGE,
    DIM_ENRICHMENT_FIELD, DIM_ENRICHMENT_CODE, DIM_MOVIE, DIM_COLLECTION, DIM_KEYWORD,
)

BRIDGES = (
    Bridge("bridge_movie_genre", "movie_genre", "source_position", DIM_GENRE),
    Bridge("bridge_movie_keyword", "movie_keyword", "source_position", DIM_KEYWORD),
    Bridge("bridge_movie_cast", "movie_cast", "billing_order", DIM_PERSON),
    Bridge("bridge_movie_production_company", "movie_production_company", "source_position",
           DIM_PRODUCTION_COMPANY),
    Bridge("bridge_movie_production_country", "movie_production_country", "source_position",
           DIM_PRODUCTION_COUNTRY),
    Bridge("bridge_movie_spoken_language", "movie_spoken_language", "source_position",
           DIM_SPOKEN_LANGUAGE),
)

FACT_SNAPSHOT = "fact_movie_snapshot"
FACT_SNAPSHOT_COLUMNS = (
    "movie_snapshot_sk bigint", "movie_sk bigint", "collection_sk bigint",
    "original_language_sk bigint", "status_sk bigint", "rating_sk bigint",
    "release_date_sk bigint", "snapshot_date_sk bigint", "movie_id bigint",
    "snapshot_at timestamp", "runtime_minutes int", "budget_usd decimal(18,2)",
    "revenue_usd decimal(18,2)", "profit_usd decimal(19,2)", "roi_percentage decimal(28,4)",
    "popularity decimal(10,3)", "user_score decimal(3,1)", "vote_average decimal(5,3)",
    "vote_count int", "genre_count int", "keyword_count int", "cast_count int",
    "company_count int", "country_count int", "spoken_language_count int",
    "has_collection boolean", "has_budget boolean", "has_revenue boolean",
    "has_homepage boolean", "is_deleted boolean", "source_updated_at timestamp",
    "silver_processed_at timestamp", "record_hash string",
)
# Claves sustitutas del hecho que pueden quedar en 0 y repararse después.
FACT_REPAIRABLE_KEYS = ("movie_sk", "collection_sk", "original_language_sk", "status_sk", "rating_sk")
# Conteo del hecho -> relación Bronze de la que sale.
FACT_COUNTS = {
    "genre_count": "movie_genre",
    "keyword_count": "movie_keyword",
    "cast_count": "movie_cast",
    "company_count": "movie_production_company",
    "country_count": "movie_production_country",
    "spoken_language_count": "movie_spoken_language",
}
# record_hash: claves de negocio de las dimensiones relacionadas, medidas y
# conteos (sección 27). No entran las claves sustitutas ni los atributos
# descriptivos: un cambio de título no debe crear snapshot.
FACT_HASH_COLUMNS = (
    "movie_id", "collection_id", "original_language_code", "status_code", "rating_code",
    "release_date", "runtime_minutes", "budget_usd", "revenue_usd", "popularity",
    "user_score", "vote_average", "vote_count", *FACT_COUNTS,
)
# Lo que se añade al record_hash del último snapshot para obtener el del
# snapshot de borrado: nunca coincide con el hash de una película viva.
DELETED_HASH_SUFFIX = "|deleted"

FACT_ENRICHMENT = "fact_movie_enrichment"
FACT_ENRICHMENT_COLUMNS = (
    "movie_id bigint", "enrichment_field_sk bigint", "enrichment_code_sk bigint",
    "observed_at timestamp", "is_current boolean", "silver_processed_at timestamp",
)

# Sistemas de procedencia conocidos (sección 29, regla 6).
KNOWN_SOURCE_SYSTEMS = ("tmdb", "wikipedia", "wikidata", "unverified")
FX_FAMILY = "wikipedia_infobox_fx"
CODE_DATE_SUFFIX = r"_(\d{4}-\d{2}-\d{2})$"
FX_SUFFIX = r"^([A-Z]{3}):(\d{4})$"


# =============================================================================
# Contexto de la corrida
# =============================================================================

@dataclass
class JobContext:
    """Lo que comparten todos los pasos de una corrida.

    Attributes:
        spark: sesión de Spark.
        run_ts: timestamp lógico de la corrida, con zona horaria.
        reference_dir: directorio de los archivos de referencia.
        bronze: las tablas Bronze, cada una fijada en un snapshot y ya leída.
        report: acciones aplicadas a cada tabla de Silver en esta corrida.
    """

    spark: SparkSession
    run_ts: datetime
    reference_dir: Path
    bronze: dict[str, DataFrame] = field(default_factory=dict)
    report: dict[str, dict[str, int]] = field(default_factory=dict)

    def silver(self, table: str) -> DataFrame:
        """Estado actual de una tabla de Silver."""
        return self.spark.table(f"{SILVER}.{table}")

    @property
    def run_ts_column(self) -> Column:
        """El timestamp de la corrida, como literal de Spark."""
        return F.lit(self.run_ts)


# =============================================================================
# Utilidades de DataFrame
# =============================================================================

def materialize(frame: DataFrame) -> DataFrame:
    """Calcula el DataFrame una sola vez y corta su linaje.

    Es lo que permite usarlo después como origen de un ``MERGE INTO``, que no
    admite un DataFrame en caché, y contar sus filas sin recalcularlo.
    """
    return frame.localCheckpoint(eager=True)


def conform(frame: DataFrame, columns: Sequence[str]) -> DataFrame:
    """Deja el DataFrame con las columnas, el orden y los tipos de la tabla."""
    selected = []
    for definition in columns:
        name, data_type = definition.split(None, 1)
        selected.append(F.col(name).cast(data_type).alias(name))
    return frame.select(*selected)


def row_hash(columns: Sequence[str | Column]) -> Column:
    """SHA-256 de varias columnas, distinguiendo el nulo de la cadena vacía."""
    parts = [
        F.coalesce(F.col(c).cast("string") if isinstance(c, str) else c.cast("string"), F.lit(HASH_NULL))
        for c in columns
    ]
    return F.sha2(F.concat_ws(HASH_SEPARATOR, *parts), 256)


def any_of(conditions: Sequence[Column]) -> Column:
    """``True`` si se cumple alguna de las condiciones."""
    return reduce(lambda left, right: left | right, conditions)


def next_keys(max_key: int, *order_by: str | Column) -> Column:
    """Claves sustitutas nuevas: ``max(SK) + row_number()`` (sección 21).

    El orden es el de las columnas indicadas, que identifican cada fila, así
    que la numeración no depende del particionado ni cambia al reejecutar. Es
    una numeración global: todas las filas nuevas pasan por una única tarea,
    que con este volumen sobra. Por eso pyspark/conf/log4j2.properties calla
    el aviso de Spark sobre las ventanas sin partición.
    """
    return (F.lit(max_key) + F.row_number().over(Window.orderBy(*order_by))).cast("bigint")


def max_key(frame: DataFrame, key: str) -> int:
    """La mayor clave sustituta de una tabla; 0 si solo tiene filas especiales."""
    value = frame.agg(F.max(key)).first()[0]
    return max(value or 0, 0)


def date_key(date: Column) -> Column:
    """Clave de ``dim_date`` para una fecha, con la forma ``YYYYMMDD``."""
    in_calendar = date.between(F.lit(CALENDAR_START).cast("date"), F.lit(CALENDAR_END).cast("date"))
    return F.when(in_calendar, F.date_format(date, "yyyyMMdd").cast("bigint")).otherwise(F.lit(UNKNOWN_SK))


def is_tombstone() -> Column:
    """La fila Bronze es el rastro de un DELETE."""
    return F.col("cdc_op_type").eqNullSafe(TOMBSTONE)


def alive(frame: DataFrame) -> DataFrame:
    """Filas Bronze que existen ahora en PostgreSQL."""
    return frame.where(~is_tombstone())


def cdc_timestamp() -> Column:
    """``cdc_op_ts``, que llega en milisegundos, como timestamp."""
    return F.timestamp_millis(F.col("cdc_op_ts"))


def change_columns(*, has_updated_at: bool) -> list[Column]:
    """Columnas ``_deleted`` y ``_changed_at`` de una entidad con historial.

    ``_changed_at`` sigue el orden de la sección 21: ``updated_at`` en las
    filas vivas de las tablas que lo tienen, y ``cdc_op_ts`` en los tombstones
    y en las tablas sin ``updated_at``.
    """
    changed_at = cdc_timestamp()
    if has_updated_at:
        changed_at = F.coalesce(F.when(~is_tombstone(), F.col("updated_at")), changed_at)
    return [is_tombstone().alias("_deleted"), changed_at.alias("_changed_at")]


def key_lookup(ctx: JobContext, dim: Dimension, key_alias: str | None = None) -> DataFrame:
    """Clave de negocio -> clave sustituta vigente de una dimensión.

    Deja fuera las filas especiales y, en las SCD2, las versiones cerradas.
    """
    rows = ctx.silver(dim.table).where(F.col(dim.surrogate_key) > 0)
    if dim.scd2:
        rows = rows.where(F.col("is_current"))
    return rows.select(F.col(dim.business_key).alias(key_alias or dim.business_key), dim.surrogate_key)


# =============================================================================
# Lectura de Bronze y de los archivos de referencia
# =============================================================================

def current_snapshot_id(spark: SparkSession, table: str) -> int | None:
    """Snapshot vigente de una tabla Iceberg, o ``None`` si aún no tiene.

    Raises:
        BronzeTableMissingError: si la tabla no existe en el catálogo.
    """
    try:
        row = spark.sql(f"SELECT snapshot_id FROM {table}.refs WHERE name = 'main'").first()
    except AnalysisException as error:
        if error.getCondition() != "TABLE_OR_VIEW_NOT_FOUND":
            raise
        raise BronzeTableMissingError(
            f"No existe la tabla {table}. Causa probable: el pipeline de Flink CDC todavía "
            "no la ha creado, o Bronze se está reconstruyendo (diseño, sección 38). "
            "Silver no se ha modificado; vuelve a lanzar el job cuando Bronze tenga sus 20 tablas."
        ) from error
    return row["snapshot_id"] if row else None


def load_bronze(spark: SparkSession) -> dict[str, DataFrame]:
    """Lee las 20 tablas Bronze, cada una en su snapshot vigente.

    Flink sigue escribiendo mientras el job corre. Primero se fijan los 20
    snapshots, que son llamadas rápidas al catálogo, y después se leen: así
    las tablas quedan fijadas con segundos de diferencia y no con lo que tarde
    la lectura. Fijar el snapshot garantiza además que todos los pasos ven el
    mismo estado de cada tabla, y leerla una sola vez evita aplicar sus
    deletes de igualdad en cada paso.
    """
    snapshots = {name: current_snapshot_id(spark, f"{BRONZE}.{name}") for name in BRONZE_TABLES}
    frames: dict[str, DataFrame] = {}
    for name, snapshot_id in snapshots.items():
        reader = spark.read
        if snapshot_id is not None:
            reader = reader.option("versionAsOf", snapshot_id)
        frames[name] = materialize(reader.table(f"{BRONZE}.{name}"))
        LOG.debug("Bronze %s leída en el snapshot %s", name, snapshot_id)
    return frames


def read_reference(ctx: JobContext, file_name: str, key: str, attributes: Sequence[str]) -> DataFrame:
    """Lee un archivo de referencia (sección 24) como DataFrame de textos.

    Son archivos de unas decenas de filas: se leen en el driver, que es donde
    está montado ``pyspark/reference/``, y se añade la columna ``_found``.

    Raises:
        ReferenceDataError: si el archivo falta, le falta una columna o repite
            un valor en su columna clave.
    """
    path = ctx.reference_dir / file_name
    names = [key, *attributes]
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            header = reader.fieldnames or []
            rows = list(reader)
    except OSError as error:
        raise ReferenceDataError(
            f"No se puede leer el archivo de referencia {path}. Causa probable: pyspark/reference/ "
            "no está montado en el contenedor que hace de driver. Móntalo o indica su ruta con "
            "--reference-dir."
        ) from error
    missing = [name for name in names if name not in header]
    if missing:
        raise ReferenceDataError(
            f"Al archivo de referencia {path} le faltan las columnas {missing}; trae {header}. "
            "Corrige su cabecera (diseño, sección 24)."
        )
    keys = [row[key] for row in rows]
    repeated = sorted({value for value in keys if keys.count(value) > 1})
    if repeated:
        raise ReferenceDataError(
            f"El archivo de referencia {path} repite en la columna {key} los valores {repeated}. "
            "Deja una sola fila por valor."
        )
    schema = ", ".join(f"{name} string" for name in names)
    data = [tuple(row[name] or None for name in names) for row in rows]
    return ctx.spark.createDataFrame(data, schema).withColumn("_found", F.lit(True))


# =============================================================================
# Escritura en Silver
# =============================================================================

def assignments(columns: Sequence[str]) -> str:
    """``t.a = s.a, t.b = s.b`` para la cláusula ``UPDATE SET`` de un MERGE."""
    return ", ".join(f"t.{name} = s.{name}" for name in columns)


def insert_clause(columns: Sequence[str]) -> str:
    """``INSERT (a, b) VALUES (s.a, s.b)`` para un MERGE."""
    return f"INSERT ({', '.join(columns)}) VALUES ({', '.join(f's.{name}' for name in columns)})"


def apply_changes(ctx: JobContext, table: str, changes: DataFrame, merge_sql: str) -> None:
    """Aplica un conjunto de cambios a una tabla de Silver con un ``MERGE INTO``.

    Si el conjunto está vacío no ejecuta nada: un MERGE sin filas crearía
    igualmente un snapshot de Iceberg y el job dejaría de ser idempotente.

    Args:
        ctx: contexto de la corrida.
        table: tabla de Silver, sin el namespace.
        changes: filas a aplicar, con la columna ``_action``.
        merge_sql: sentencia MERGE con los marcadores ``{target}`` y ``{source}``.
    """
    changes = materialize(changes)
    counts = {row["_action"]: row["count"] for row in changes.groupBy("_action").count().collect()}
    ctx.report[table] = counts
    if not counts:
        LOG.info("%s: sin cambios, no se escribe", table)
        return
    view = f"changes_{table}_{uuid.uuid4().hex[:8]}"
    changes.createOrReplaceTempView(view)
    try:
        ctx.spark.sql(merge_sql.format(target=f"{SILVER}.{table}", source=view))
    finally:
        ctx.spark.catalog.dropTempView(view)
    detail = ", ".join(f"{ACTION_LABELS[action]}: {count}" for action, count in sorted(counts.items()))
    LOG.info("%s: %s", table, detail)


def create_table(ctx: JobContext, table: str, columns: Sequence[str], rows: DataFrame | None = None) -> bool:
    """Crea una tabla de Silver si no existe, en formato Iceberg v2.

    La tabla y sus filas iniciales se crean en una sola operación: una
    dimensión nunca existe sin sus filas especiales.

    Returns:
        ``True`` si la tabla se creó en esta llamada.
    """
    name = f"{SILVER}.{table}"
    if ctx.spark.catalog.tableExists(name):
        return False
    schema = ", ".join(columns)
    initial = conform(rows, columns) if rows is not None else ctx.spark.createDataFrame([], schema)
    initial.writeTo(name).using("iceberg").tableProperty("format-version", "2").create()
    LOG.info("%s: tabla creada", table)
    return True


def special_rows(ctx: JobContext, columns: Sequence[str], surrogate_key: str,
                 label_columns: Sequence[str] = (), *, scd2: bool = False) -> DataFrame:
    """Las filas 0 (Unknown) y -1 (Not Applicable) de una dimensión (sección 30).

    Llevan el rótulo en las columnas de texto que nombran al miembro y nulo en
    el resto. En una dimensión SCD2 figuran como vigentes, para que un filtro
    por ``is_current`` no las descarte.
    """
    names = column_names(columns)
    rows = []
    for key, label in SPECIAL_ROWS:
        values: dict[str, object] = {surrogate_key: key}
        values.update({name: label for name in label_columns})
        if "silver_processed_at" in names:
            values["silver_processed_at"] = ctx.run_ts
        if scd2:
            values["is_current"] = True
        rows.append(tuple(values.get(name) for name in names))
    return ctx.spark.createDataFrame(rows, ", ".join(columns))


def create_tables(ctx: JobContext) -> None:
    """Crea las tablas de Silver que falten: 14 dimensiones, 6 bridges y 2 hechos."""
    create_dim_date(ctx)
    for dim in DIMENSIONS:
        seed = special_rows(ctx, dim.columns, dim.surrogate_key, dim.label_columns, scd2=dim.scd2)
        create_table(ctx, dim.table, dim.columns, seed)
    for bridge in BRIDGES:
        create_table(ctx, bridge.table, bridge.columns)
    create_table(ctx, FACT_SNAPSHOT, FACT_SNAPSHOT_COLUMNS)
    create_table(ctx, FACT_ENRICHMENT, FACT_ENRICHMENT_COLUMNS)


# =============================================================================
# dim_date (sección 26)
# =============================================================================

def create_dim_date(ctx: JobContext) -> None:
    """Crea ``dim_date`` con su calendario. Es estática: se carga una sola vez.

    ``day_of_week`` sigue ISO 8601: 1 es lunes y 7 es domingo. Los nombres de
    día y de mes van en inglés, como el resto de los datos.
    """
    if ctx.spark.catalog.tableExists(f"{SILVER}.dim_date"):
        return
    day = F.col("calendar_date")
    calendar = ctx.spark.sql(
        f"SELECT explode(sequence(DATE'{CALENDAR_START}', DATE'{CALENDAR_END}', INTERVAL 1 DAY)) "
        "AS calendar_date"
    ).select(
        F.date_format(day, "yyyyMMdd").alias("date_sk"),
        day,
        F.dayofmonth(day).alias("day_number"),
        F.date_format(day, "EEEE").alias("day_name"),
        (F.weekday(day) + 1).alias("day_of_week"),
        F.weekofyear(day).alias("week_of_year"),
        F.month(day).alias("month_number"),
        F.date_format(day, "MMMM").alias("month_name"),
        F.quarter(day).alias("quarter_number"),
        F.year(day).alias("year_number"),
        (F.floor(F.year(day) / 10) * 10).alias("decade_number"),
        (F.weekday(day) >= SATURDAY).alias("is_weekend"),
    )
    rows = conform(calendar, DIM_DATE_COLUMNS).unionByName(special_rows(ctx, DIM_DATE_COLUMNS, "date_sk"))
    create_table(ctx, "dim_date", DIM_DATE_COLUMNS, rows)


# =============================================================================
# Dimensiones Tipo 1 (secciones 24, 25 y 29)
# =============================================================================

def load_type1_dimension(ctx: JobContext, dim: Dimension, source: DataFrame) -> None:
    """Da de alta las claves nuevas y sobrescribe los atributos que cambiaron.

    Solo compara atributos: un ``source_updated_at`` distinto, como el que deja
    una reconstrucción de Bronze, no reescribe la fila.

    Args:
        ctx: contexto de la corrida.
        dim: dimensión Tipo 1.
        source: una fila por clave de negocio, con los atributos de la
            dimensión y ``source_updated_at``.
    """
    key, sk = dim.business_key, dim.surrogate_key
    current = ctx.silver(dim.table).where(F.col(sk) > 0)
    joined = source.alias("s").join(current.alias("c"), F.col(f"s.{key}") == F.col(f"c.{key}"), "left")
    is_new = F.col(f"c.{sk}").isNull()
    differs = any_of([~F.col(f"s.{name}").eqNullSafe(F.col(f"c.{name}")) for name in dim.descriptive])
    incoming = [F.col(f"s.{name}").alias(name) for name in (*column_names(dim.attributes), "source_updated_at")]

    inserts = (
        joined.where(is_new).select(*incoming)
        .withColumn(sk, next_keys(max_key(current, sk), key))
        .withColumn("_action", F.lit(INSERT))
    )
    updates = joined.where(~is_new & differs).select(
        F.col(f"c.{sk}").alias(sk), *incoming, F.lit(UPDATE).alias("_action")
    )
    changes = inserts.unionByName(updates).withColumn("silver_processed_at", ctx.run_ts_column)

    names = column_names(dim.columns)
    apply_changes(ctx, dim.table, conform(changes, (*dim.columns, "_action string")), (
        f"MERGE INTO {{target}} t USING {{source}} s ON t.{sk} = s.{sk} "
        f"WHEN MATCHED THEN UPDATE SET {assignments(names)} "
        f"WHEN NOT MATCHED THEN {insert_clause(names)}"
    ))


def with_reference(source: DataFrame, reference: DataFrame, source_key: str, reference_key: str) -> DataFrame:
    """Añade a las filas de Bronze los atributos de su archivo de referencia.

    Un valor que no está en el archivo queda con ``_found`` nulo y los
    atributos derivados en ``NULL``: no se inventan equivalencias (sección 24).
    """
    return source.join(F.broadcast(reference), F.col(source_key) == F.col(reference_key), "left")


def mapped_status() -> Column:
    """``quality_status`` de un catálogo: ``ok`` o ``unmapped``."""
    return F.when(F.col("_found").isNull(), "unmapped").otherwise("ok").alias("quality_status")


def standardized_status(source_name: str, standard_name: str) -> Column:
    """``quality_status`` con estandarización: ``ok``, ``standardized`` o ``unmapped``."""
    return (
        F.when(F.col("_found").isNull(), "unmapped")
        .when(F.col(source_name) == F.col(standard_name), "ok")
        .otherwise("standardized")
        .alias("quality_status")
    )


def original_language_rows(ctx: JobContext) -> DataFrame:
    """``dim_original_language``: códigos de Bronze con su nombre de referencia."""
    reference = read_reference(ctx, "languages.csv", "language_code", ("language_name", "is_tmdb_specific"))
    source = alive(ctx.bronze["original_language"]).select(
        F.col("language_code").alias("_code"), cdc_timestamp().alias("source_updated_at")
    )
    return with_reference(source, reference, "_code", "language_code").select(
        F.col("_code").alias("language_code"), "language_name",
        (F.lower("is_tmdb_specific") == "true").alias("is_tmdb_specific"),
        mapped_status(), "source_updated_at",
    )


def status_rows(ctx: JobContext) -> DataFrame:
    """``dim_status``: estados de Bronze con su descripción de referencia."""
    reference = read_reference(ctx, "statuses.csv", "status_code", ("status_description",))
    source = alive(ctx.bronze["movie_status"]).select(
        F.col("status_code").alias("_code"), cdc_timestamp().alias("source_updated_at")
    )
    return with_reference(source, reference, "_code", "status_code").select(
        F.col("_code").alias("status_code"), "status_description", mapped_status(), "source_updated_at"
    )


def rating_rows(ctx: JobContext) -> DataFrame:
    """``dim_rating``: clasificaciones de Bronze con su sistema y descripción."""
    reference = read_reference(ctx, "ratings.csv", "rating_code", ("rating_system", "rating_description"))
    source = alive(ctx.bronze["content_rating"]).select(
        F.col("rating_code").alias("_code"), cdc_timestamp().alias("source_updated_at")
    )
    return with_reference(source, reference, "_code", "rating_code").select(
        F.col("_code").alias("rating_code"), "rating_system", "rating_description",
        mapped_status(), "source_updated_at",
    )


def named_entity_rows(ctx: JobContext, bronze_table: str, key: str, name_column: str) -> DataFrame:
    """Dimensión cuyo único atributo es el nombre: género, persona o compañía."""
    return alive(ctx.bronze[bronze_table]).select(
        key, F.col("name").alias(name_column), cdc_timestamp().alias("source_updated_at")
    )


def production_country_rows(ctx: JobContext) -> DataFrame:
    """``dim_production_country``: conserva el nombre fuente y añade el estándar."""
    reference = read_reference(ctx, "countries.csv", "source_name", ("standard_country_name", "country_code"))
    source = alive(ctx.bronze["production_country"]).select(
        "country_id", F.col("name").alias("source_country_name"), cdc_timestamp().alias("source_updated_at")
    )
    return with_reference(source, reference, "source_country_name", "source_name").select(
        "country_id", "source_country_name", "standard_country_name", "country_code",
        standardized_status("source_country_name", "standard_country_name"), "source_updated_at",
    )


def spoken_language_rows(ctx: JobContext) -> DataFrame:
    """``dim_spoken_language``: conserva el nombre fuente y añade el estándar."""
    reference = read_reference(ctx, "spoken.csv", "source_name", ("standard_language_name", "language_code"))
    source = alive(ctx.bronze["spoken_language"]).select(
        "spoken_language_id", F.col("name").alias("source_language_name"),
        cdc_timestamp().alias("source_updated_at"),
    )
    return with_reference(source, reference, "source_language_name", "source_name").select(
        "spoken_language_id", "source_language_name", "standard_language_name", "language_code",
        standardized_status("source_language_name", "standard_language_name"), "source_updated_at",
    )


def enrichment_field_rows(ctx: JobContext) -> DataFrame:
    """``dim_enrichment_field``: campos de Bronze con su descripción de referencia."""
    reference = read_reference(ctx, "enrichment.csv", "field_name", ("field_description",))
    source = alive(ctx.bronze["enrichment_field"]).select(
        F.col("field_name").alias("_field"), cdc_timestamp().alias("source_updated_at")
    )
    return with_reference(source, reference, "_field", "field_name").select(
        F.col("_field").alias("field_name"), "field_description", mapped_status(), "source_updated_at"
    )


def enrichment_code_rows(ctx: JobContext) -> DataFrame:
    """``dim_enrichment_code``: una fila por código, descompuesto con reglas fijas.

    Aplica, en orden, las seis reglas de la sección 29: separar base y sufijo
    en el primer ``:``, extraer la fecha final de la base, derivar familia y
    sistema, y repartir el sufijo entre moneda y año o ``qualifier``.
    """
    codes = alive(ctx.bronze["movie_enrichment"]).groupBy("code").agg(
        F.min(cdc_timestamp()).alias("source_updated_at")
    )
    base = F.substring_index("code", ":", 1)
    is_fx = F.col("source_family") == FX_FAMILY
    fx_is_valid = F.coalesce(F.col("_suffix").rlike(FX_SUFFIX), F.lit(False))
    is_unmapped = ~F.col("source_system").isin(*KNOWN_SOURCE_SYSTEMS) | (is_fx & ~fx_is_valid)
    return (
        codes
        .withColumn("_suffix", F.when(F.col("code").contains(":"), F.expr("substring(code, instr(code, ':') + 1)")))
        .withColumn("source_date_text", F.nullif(F.regexp_extract(base, CODE_DATE_SUFFIX, 1), F.lit("")))
        .withColumn("source_family", F.regexp_replace(base, CODE_DATE_SUFFIX, ""))
        .withColumn("source_system", F.substring_index("source_family", "_", 1))
        .withColumn("currency_code", F.when(is_fx & fx_is_valid, F.regexp_extract("_suffix", FX_SUFFIX, 1)))
        .withColumn("currency_year",
                    F.when(is_fx & fx_is_valid, F.regexp_extract("_suffix", FX_SUFFIX, 2).try_cast("int")))
        .withColumn("qualifier", F.when(~is_fx, F.col("_suffix")))
        .withColumn("quality_status", F.when(is_unmapped, "unmapped").otherwise("ok"))
        .drop("_suffix")
    )


# =============================================================================
# Dimensiones SCD2 (secciones 21 a 23 y 25)
# =============================================================================

def load_scd2_dimension(ctx: JobContext, dim: Dimension, source: DataFrame) -> None:
    """Compara el estado de Bronze con la versión vigente y aplica SCD Type 2.

    Por cada clave de negocio:

    - viva y sin versión vigente: versión nueva (alta o reactivación);
    - viva y con atributos distintos: cierra la vigente e inserta otra;
    - tombstone, o ausente de Bronze: cierra la vigente y no inserta nada;
    - tombstone sin versión vigente: nada, para Silver no llegó a existir.

    La versión que se cierra recibe como ``effective_to`` el inicio de la que
    la reemplaza; si no la hay, la fecha del borrado o, cuando la clave ya no
    está en Bronze, el timestamp de la corrida.

    Args:
        ctx: contexto de la corrida.
        dim: dimensión SCD2.
        source: una fila por clave de negocio, con los atributos de la
            dimensión, ``_deleted`` y ``_changed_at``.
    """
    key, sk = dim.business_key, dim.surrogate_key
    history = ctx.silver(dim.table).where(F.col(sk) > 0)
    current = history.where(F.col("is_current"))
    previous = history.groupBy(key).agg(
        F.max("version_number").alias("_last_version"), F.max("effective_to").alias("_last_closed_at")
    )
    state = source.withColumn("attribute_hash", row_hash(dim.descriptive))
    joined = state.alias("s").join(current.alias("c"), F.col(f"s.{key}") == F.col(f"c.{key}"), "full_outer")

    is_alive = F.col(f"s.{key}").isNotNull() & ~F.col("s._deleted")
    has_current = F.col(f"c.{sk}").isNotNull()
    hash_differs = ~F.col("s.attribute_hash").eqNullSafe(F.col("c.attribute_hash"))
    # Sin fecha en el dato (clave ausente de Bronze) vale la de la corrida.
    changed_at = F.coalesce(F.col("s._changed_at"), ctx.run_ts_column)
    names = column_names(dim.columns)

    closes = joined.where(has_current & (~is_alive | hash_differs)).select(
        *[F.col(f"c.{name}").alias(name) for name in names
          if name not in ("effective_to", "is_current", "silver_processed_at")],
        # greatest: un rango nunca termina antes de empezar.
        F.greatest(changed_at, F.col("c.effective_from")).alias("effective_to"),
        F.lit(False).alias("is_current"),
        F.lit(CLOSE).alias("_action"),
    )
    inserts = (
        joined.where(is_alive & (~has_current | hash_differs))
        .join(previous.alias("p"), F.col(f"s.{key}") == F.col(f"p.{key}"), "left")
        .select(
            *[F.col(f"s.{name}").alias(name) for name in column_names(dim.attributes)],
            # greatest: la versión nueva no empieza antes de que acabe la anterior.
            F.greatest(changed_at, F.col("c.effective_from"), F.col("p._last_closed_at")).alias("effective_from"),
            F.lit(None).cast("timestamp").alias("effective_to"),
            F.lit(True).alias("is_current"),
            (F.coalesce(F.col("p._last_version"), F.lit(0)) + 1).alias("version_number"),
            F.col("s.attribute_hash").alias("attribute_hash"),
            changed_at.alias("source_updated_at"),
            F.lit(INSERT).alias("_action"),
        )
        .withColumn(sk, next_keys(max_key(history, sk), key, "effective_from"))
    )
    changes = closes.unionByName(inserts).withColumn("silver_processed_at", ctx.run_ts_column)

    apply_changes(ctx, dim.table, conform(changes, (*dim.columns, "_action string")), (
        f"MERGE INTO {{target}} t USING {{source}} s ON t.{sk} = s.{sk} "
        f"WHEN MATCHED THEN UPDATE SET {assignments(('effective_to', 'is_current', 'silver_processed_at'))} "
        f"WHEN NOT MATCHED THEN {insert_clause(names)}"
    ))


def movie_rows(ctx: JobContext) -> DataFrame:
    """``dim_movie``: atributos descriptivos; las medidas van al hecho."""
    release_year = F.year("release_date")
    return ctx.bronze["movie"].select(
        "movie_id", "imdb_id", "title", "original_title", "overview", "plot", "tagline",
        "release_date",
        release_year.alias("release_year"),
        F.month("release_date").alias("release_month"),
        (F.floor(release_year / 10) * 10).alias("release_decade"),
        "homepage", "poster_path", "backdrop_path", "adult", "video",
        *change_columns(has_updated_at=True),
    )


def collection_rows(ctx: JobContext) -> DataFrame:
    """``dim_collection``: nombre y rutas canónicas de sus imágenes.

    La ruta canónica es el primer valor no nulo observado (sección 23): si
    Silver ya tiene una, se conserva; si no, es la de la película viva con
    menor ``movie_id`` que traiga alguna.
    """
    observed = alive(ctx.bronze["movie_collection"])
    first_poster = observed.where(F.col("observed_poster_path").isNotNull()).groupBy("collection_id").agg(
        F.min_by("observed_poster_path", "movie_id").alias("_first_poster")
    )
    first_backdrop = observed.where(F.col("observed_backdrop_path").isNotNull()).groupBy("collection_id").agg(
        F.min_by("observed_backdrop_path", "movie_id").alias("_first_backdrop")
    )
    known = (
        ctx.silver(DIM_COLLECTION.table)
        .where(F.col("collection_sk") > 0)
        .groupBy("collection_id")
        .agg(
            F.max_by("canonical_poster_path", "version_number").alias("_known_poster"),
            F.max_by("canonical_backdrop_path", "version_number").alias("_known_backdrop"),
        )
    )
    return (
        ctx.bronze["collection"]
        .join(first_poster, "collection_id", "left")
        .join(first_backdrop, "collection_id", "left")
        .join(known, "collection_id", "left")
        .select(
            "collection_id",
            F.col("name").alias("collection_name"),
            F.coalesce("_known_poster", "_first_poster").alias("canonical_poster_path"),
            F.coalesce("_known_backdrop", "_first_backdrop").alias("canonical_backdrop_path"),
            *change_columns(has_updated_at=True),
        )
    )


def keyword_rows(ctx: JobContext) -> DataFrame:
    """``dim_keyword``: el nombre puede cambiar para un mismo ``keyword_id``."""
    return ctx.bronze["keyword"].select(
        "keyword_id", F.col("name").alias("keyword_name"), *change_columns(has_updated_at=True)
    )


# =============================================================================
# Bridges (sección 28)
# =============================================================================

def load_bridge(ctx: JobContext, bridge: Bridge) -> None:
    """Sincroniza un bridge con su relación Bronze.

    Cada fila vigente se identifica por película y posición. Comparando el
    estado de Bronze con las filas vigentes:

    - la relación ya no existe, o en esa posición hay otro miembro: se cierra;
    - la relación es nueva: se inserta, con la clave sustituta vigente del
      miembro o 0 si su dimensión todavía no lo tiene;
    - la fila quedó con clave 0 y el miembro ya está en su dimensión: se
      repara en el sitio;
    - cambió el número de miembros de la película: se recalcula el peso.

    Un cambio de nombre de una keyword no toca el bridge: la fila conserva la
    versión vigente al crearse y se compara por clave de negocio.
    """
    dim, position = bridge.dimension, bridge.position
    key, sk = dim.business_key, dim.surrogate_key
    relation = ctx.bronze[bridge.relation]
    members = ctx.silver(dim.table).where(F.col(sk) > 0)

    resolved = key_lookup(ctx, dim).withColumnRenamed(sk, "_resolved_sk")
    movie_members = Window.partitionBy("movie_id")
    desired = alive(relation).join(resolved, key, "left").select(
        "movie_id", key, position,
        F.coalesce("_resolved_sk", F.lit(UNKNOWN_SK)).alias("_resolved_sk"),
        (F.lit(1).cast(WEIGHT_TYPE) / F.count("*").over(movie_members)).cast(WEIGHT_TYPE).alias("_weight"),
        cdc_timestamp().alias("_changed_at"),
    )
    # Clave de negocio del miembro de cada fila vigente; nula si quedó en 0.
    member_keys = members.select(F.col(sk).alias("_member_sk"), F.col(key).alias("_member_key"))
    current = ctx.silver(bridge.table).where(F.col("is_current")).join(
        member_keys, F.col(sk) == F.col("_member_sk"), "left"
    )
    joined = desired.alias("d").join(
        current.alias("c"),
        (F.col("d.movie_id") == F.col("c.movie_id")) & (F.col(f"d.{position}") == F.col(f"c.{position}")),
        "full_outer",
    )

    wanted = F.col("d.movie_id").isNotNull()
    exists = F.col("c.movie_id").isNotNull()
    pending = F.col(f"c.{sk}") == UNKNOWN_SK
    same_member = wanted & exists & (pending | F.col("c._member_key").eqNullSafe(F.col(f"d.{key}")))
    repaired_sk = F.when(pending, F.col("d._resolved_sk")).otherwise(F.col(f"c.{sk}"))

    inserts = joined.where(wanted & ~same_member).select(
        F.lit(INSERT).alias("_action"),
        F.col("d.movie_id").alias("movie_id"),
        F.col("d._resolved_sk").alias(sk),
        F.col(f"d.{position}").alias(position),
        F.col("d._weight").alias("allocation_weight"),
        F.col("d._changed_at").alias("effective_from"),
        F.lit(None).cast("timestamp").alias("effective_to"),
        F.lit(True).alias("is_current"),
    )
    updates = joined.where(
        same_member & ((repaired_sk != F.col(f"c.{sk}")) | (F.col("d._weight") != F.col("c.allocation_weight")))
    ).select(
        F.lit(UPDATE).alias("_action"),
        F.col("c.movie_id").alias("movie_id"),
        repaired_sk.alias(sk),
        F.col(f"c.{position}").alias(position),
        F.col("d._weight").alias("allocation_weight"),
        F.col("c.effective_from").alias("effective_from"),
        F.col("c.effective_to").alias("effective_to"),
        F.lit(True).alias("is_current"),
    )
    # La fecha de cierre es la del último cambio de la relación en Bronze, que
    # en un borrado es la del tombstone. Si la relación ya no está en Bronze,
    # o la fila estaba en 0 y no se sabe de quién era, la de la corrida.
    relation_changes = relation.select(
        F.col("movie_id").alias("_movie_id"), F.col(key).alias("_key"),
        cdc_timestamp().alias("_relation_changed_at"),
    )
    closes = (
        joined.where(exists & ~same_member)
        .join(
            relation_changes,
            (F.col("c.movie_id") == F.col("_movie_id")) & (F.col("c._member_key") == F.col("_key")),
            "left",
        )
        .select(
            F.lit(CLOSE).alias("_action"),
            F.col("c.movie_id").alias("movie_id"),
            F.col(f"c.{sk}").alias(sk),
            F.col(f"c.{position}").alias(position),
            F.col("c.allocation_weight").alias("allocation_weight"),
            F.col("c.effective_from").alias("effective_from"),
            F.greatest(
                F.coalesce("_relation_changed_at", ctx.run_ts_column), F.col("c.effective_from")
            ).alias("effective_to"),
            F.lit(False).alias("is_current"),
        )
    )
    changes = inserts.unionByName(updates).unionByName(closes)

    names = column_names(bridge.columns)
    apply_changes(ctx, bridge.table, conform(changes, (*bridge.columns, "_action string")), (
        f"MERGE INTO {{target}} t USING {{source}} s "
        f"ON s._action <> '{INSERT}' AND t.is_current AND t.movie_id = s.movie_id "
        f"AND t.{position} = s.{position} "
        f"WHEN MATCHED AND s._action = '{CLOSE}' THEN UPDATE SET {assignments(('effective_to', 'is_current'))} "
        f"WHEN MATCHED AND s._action = '{UPDATE}' THEN UPDATE SET {assignments((sk, 'allocation_weight'))} "
        f"WHEN NOT MATCHED AND s._action = '{INSERT}' THEN {insert_clause(names)}"
    ))


# =============================================================================
# fact_movie_snapshot (sección 27)
# =============================================================================

def movie_state(ctx: JobContext) -> DataFrame:
    """Estado de cada película viva: medidas, conteos, claves y su hash.

    Trae también las claves sustitutas resueltas contra las dimensiones, ya
    actualizadas en esta corrida: 0 si la dimensión aún no tiene el valor y -1
    en ``collection_sk`` si la película no pertenece a ninguna colección.
    """
    state = alive(ctx.bronze["movie"]).select(
        "movie_id", "original_language_code", "status_code", "rating_code", "release_date",
        "runtime_minutes", "budget_usd", "revenue_usd", "popularity", "user_score",
        "vote_average", "vote_count",
        F.col("homepage").isNotNull().alias("has_homepage"),
        F.col("updated_at").alias("snapshot_at"),
    )
    for count_column, relation in FACT_COUNTS.items():
        counts = alive(ctx.bronze[relation]).groupBy("movie_id").agg(
            F.count("*").cast("int").alias(count_column)
        )
        state = state.join(counts, "movie_id", "left")
    state = state.fillna(0, subset=list(FACT_COUNTS))
    membership = alive(ctx.bronze["movie_collection"]).select("movie_id", "collection_id")
    state = state.join(membership, "movie_id", "left").withColumn("record_hash", row_hash(FACT_HASH_COLUMNS))

    resolved = (
        state
        .join(latest_movie_versions(ctx), "movie_id", "left")
        .join(key_lookup(ctx, DIM_COLLECTION), "collection_id", "left")
        .join(key_lookup(ctx, DIM_ORIGINAL_LANGUAGE, "original_language_code"), "original_language_code", "left")
        .join(key_lookup(ctx, DIM_STATUS), "status_code", "left")
        .join(key_lookup(ctx, DIM_RATING), "rating_code", "left")
    )
    unknown = F.lit(UNKNOWN_SK)
    return resolved.select(
        *[name for name in state.columns if name != "record_hash"],
        F.coalesce("movie_sk", unknown).alias("movie_sk"),
        F.when(F.col("collection_id").isNull(), F.lit(NOT_APPLICABLE_SK))
        .otherwise(F.coalesce("collection_sk", unknown)).alias("collection_sk"),
        F.coalesce("original_language_sk", unknown).alias("original_language_sk"),
        F.coalesce("status_sk", unknown).alias("status_sk"),
        # Un rating nulo no encuentra fila y queda en 0 (sección 30).
        F.coalesce("rating_sk", unknown).alias("rating_sk"),
        "record_hash",
    )


def latest_movie_versions(ctx: JobContext) -> DataFrame:
    """``movie_id`` -> ``movie_sk`` de su última versión, vigente o cerrada."""
    return (
        ctx.silver(DIM_MOVIE.table)
        .where(F.col("movie_sk") > 0)
        .groupBy("movie_id")
        .agg(F.max_by("movie_sk", "version_number").alias("movie_sk"))
    )


def load_fact_movie_snapshot(ctx: JobContext) -> None:
    """Añade un snapshot por película cuyo ``record_hash`` cambió.

    - Película viva con hash distinto al de su último snapshot, o sin
      snapshot: snapshot nuevo, fechado con el ``updated_at`` de la película.
    - Película borrada (tombstone o ausente de Bronze) cuyo último snapshot no
      es de borrado: snapshot con ``is_deleted = true`` y los valores del
      último, fechado con el tombstone o con la corrida.
    - Último snapshot con una clave en 0 que ya se puede resolver: se repara.
    """
    fact = ctx.silver(FACT_SNAPSHOT)
    newest_first = Window.partitionBy("movie_id").orderBy(F.col("movie_snapshot_sk").desc())
    latest = fact.withColumn("_rank", F.row_number().over(newest_first)).where("_rank = 1").drop("_rank")
    state = materialize(movie_state(ctx))
    names = column_names(FACT_SNAPSHOT_COLUMNS)

    compared = state.alias("s").join(latest.alias("l"), F.col("s.movie_id") == F.col("l.movie_id"), "left")
    is_unchanged = F.col("s.record_hash").eqNullSafe(F.col("l.record_hash"))
    budget, revenue = F.col("s.budget_usd"), F.col("s.revenue_usd")
    snapshots = compared.where(~is_unchanged).select(
        "s.*",
        date_key(F.col("s.release_date")).alias("release_date_sk"),
        date_key(F.to_date("s.snapshot_at")).alias("snapshot_date_sk"),
        # Solo cuando existen los dos: un nulo no se convierte en cero.
        (revenue - budget).alias("profit_usd"),
        F.when(budget > 0, F.round((revenue - budget) / budget * 100, 4)).alias("roi_percentage"),
        F.col("s.collection_id").isNotNull().alias("has_collection"),
        budget.isNotNull().alias("has_budget"),
        revenue.isNotNull().alias("has_revenue"),
        F.lit(False).alias("is_deleted"),
        F.col("s.snapshot_at").alias("source_updated_at"),
    )

    tombstones = ctx.bronze["movie"].where(is_tombstone()).select(
        F.col("movie_id").alias("_movie_id"), cdc_timestamp().alias("_deleted_at")
    )
    last_versions = latest_movie_versions(ctx).select(
        F.col("movie_id").alias("_version_movie_id"), F.col("movie_sk").alias("_last_movie_sk")
    )
    untouched = [name for name in names if name not in (
        "movie_snapshot_sk", "movie_sk", "snapshot_date_sk", "snapshot_at", "is_deleted",
        "source_updated_at", "silver_processed_at", "record_hash",
    )]
    deletions = (
        latest.where(~F.col("is_deleted")).alias("l")
        .join(state.alias("s"), F.col("l.movie_id") == F.col("s.movie_id"), "left_anti")
        .join(tombstones, F.col("l.movie_id") == F.col("_movie_id"), "left")
        .join(last_versions, F.col("l.movie_id") == F.col("_version_movie_id"), "left")
        # Con tombstone, su fecha; sin él, la de la corrida (decisión 64).
        .withColumn("_snapshot_at", F.greatest(
            F.coalesce("_deleted_at", ctx.run_ts_column), F.col("l.snapshot_at")
        ))
        .select(
            *[F.col(f"l.{name}").alias(name) for name in untouched],
            F.coalesce("_last_movie_sk", "l.movie_sk").alias("movie_sk"),
            F.col("_snapshot_at").alias("snapshot_at"),
            date_key(F.to_date("_snapshot_at")).alias("snapshot_date_sk"),
            F.lit(True).alias("is_deleted"),
            F.col("_snapshot_at").alias("source_updated_at"),
            F.sha2(F.concat(F.col("l.record_hash"), F.lit(DELETED_HASH_SUFFIX)), 256).alias("record_hash"),
        )
    )
    # Las dos partes se llevan a las columnas del hecho antes de unirlas; la
    # clave sustituta y la fecha de proceso se añaden después.
    pending_columns = [definition for definition in FACT_SNAPSHOT_COLUMNS
                       if column_names([definition])[0] not in ("movie_snapshot_sk", "silver_processed_at")]
    inserts = (
        conform(snapshots, pending_columns).unionByName(conform(deletions, pending_columns))
        .withColumn("movie_snapshot_sk", next_keys(max_key(fact, "movie_snapshot_sk"), "movie_id", "snapshot_at"))
        .withColumn("_action", F.lit(INSERT))
    )

    # Reparación: el último snapshot refleja el estado actual (mismo hash), así
    # que sus claves en 0 se pueden volver a resolver con las de ahora.
    def repaired(name: str) -> Column:
        return F.when(F.col(f"l.{name}") == UNKNOWN_SK, F.col(f"s.{name}")).otherwise(F.col(f"l.{name}"))

    needs_repair = any_of([repaired(name) != F.col(f"l.{name}") for name in FACT_REPAIRABLE_KEYS])
    repairs = compared.where(is_unchanged & ~F.col("l.is_deleted") & needs_repair).select(
        *[repaired(name).alias(name) if name in FACT_REPAIRABLE_KEYS else F.col(f"l.{name}").alias(name)
          for name in names if name != "silver_processed_at"],
        F.lit(UPDATE).alias("_action"),
    )
    changes = inserts.unionByName(repairs).withColumn("silver_processed_at", ctx.run_ts_column)

    apply_changes(ctx, FACT_SNAPSHOT, conform(changes, (*FACT_SNAPSHOT_COLUMNS, "_action string")), (
        "MERGE INTO {target} t USING {source} s ON t.movie_snapshot_sk = s.movie_snapshot_sk "
        f"WHEN MATCHED THEN UPDATE SET {assignments((*FACT_REPAIRABLE_KEYS, 'silver_processed_at'))} "
        f"WHEN NOT MATCHED THEN {insert_clause(names)}"
    ))


# =============================================================================
# fact_movie_enrichment (sección 29)
# =============================================================================

def load_fact_movie_enrichment(ctx: JobContext) -> None:
    """Sincroniza la procedencia de cada película con ``movie_enrichment``.

    Compara, por película, campo y código ya resueltos a clave sustituta, lo
    que hay en Bronze con las filas vigentes:

    - combinación nueva: se inserta;
    - combinación que ya no está (otro código, o película borrada): la fila
      deja de ser vigente y se conserva;
    - fila con clave 0 cuya dimensión ya llegó: se sustituye por la fila
      resuelta. Una fila en 0 no se puede identificar, así que no se actualiza
      en el sitio: se borra y se inserta la correcta en el mismo MERGE.
    """
    keys = ["movie_id", "enrichment_field_sk", "enrichment_code_sk"]
    unknown = F.lit(UNKNOWN_SK)
    desired = (
        alive(ctx.bronze["movie_enrichment"])
        .join(key_lookup(ctx, DIM_ENRICHMENT_FIELD), "field_name", "left")
        .join(key_lookup(ctx, DIM_ENRICHMENT_CODE), "code", "left")
        .select(
            "movie_id",
            F.coalesce("enrichment_field_sk", unknown).alias("enrichment_field_sk"),
            F.coalesce("enrichment_code_sk", unknown).alias("enrichment_code_sk"),
            cdc_timestamp().alias("_observed_at"),
        )
        .groupBy(*keys)
        .agg(F.count("*").alias("_wanted"), F.min("_observed_at").alias("observed_at"))
    )
    current = ctx.silver(FACT_ENRICHMENT).where(F.col("is_current")).groupBy(*keys).agg(
        F.count("*").alias("_present")
    )
    # Una combinación resuelta aparece una vez; solo las filas en 0 se repiten.
    differing = desired.join(current, keys, "full_outer").where(
        ~F.col("_wanted").eqNullSafe(F.col("_present"))
    )
    is_placeholder = (F.col("enrichment_field_sk") == UNKNOWN_SK) | (F.col("enrichment_code_sk") == UNKNOWN_SK)

    removals = differing.where(F.col("_present").isNotNull()).select(
        F.when(is_placeholder, F.lit(DELETE)).otherwise(F.lit(CLOSE)).alias("_action"),
        *keys,
        F.lit(None).cast("timestamp").alias("observed_at"),
        F.lit(False).alias("is_current"),
    )
    inserts = (
        differing.where(F.col("_wanted").isNotNull())
        .withColumn("_copy", F.explode(F.sequence(F.lit(1), F.col("_wanted"))))
        .select(F.lit(INSERT).alias("_action"), *keys, "observed_at", F.lit(True).alias("is_current"))
    )
    changes = removals.unionByName(inserts).withColumn("silver_processed_at", ctx.run_ts_column)

    names = column_names(FACT_ENRICHMENT_COLUMNS)
    apply_changes(ctx, FACT_ENRICHMENT, conform(changes, (*FACT_ENRICHMENT_COLUMNS, "_action string")), (
        "MERGE INTO {target} t USING {source} s "
        f"ON s._action <> '{INSERT}' AND t.is_current AND t.movie_id = s.movie_id "
        "AND t.enrichment_field_sk = s.enrichment_field_sk AND t.enrichment_code_sk = s.enrichment_code_sk "
        f"WHEN MATCHED AND s._action = '{DELETE}' THEN DELETE "
        f"WHEN MATCHED AND s._action = '{CLOSE}' THEN UPDATE SET {assignments(('is_current', 'silver_processed_at'))} "
        f"WHEN NOT MATCHED AND s._action = '{INSERT}' THEN {insert_clause(names)}"
    ))


# =============================================================================
# Orquestación
# =============================================================================

def job_steps() -> list[tuple[str, Callable[[JobContext], None]]]:
    """Pasos del job, en orden: dimensiones, bridges y hechos (sección 21).

    Las dimensiones van primero porque bridges y hechos resuelven contra ellas
    sus claves sustitutas.
    """
    type1 = [
        (DIM_ORIGINAL_LANGUAGE, original_language_rows),
        (DIM_STATUS, status_rows),
        (DIM_RATING, rating_rows),
        (DIM_GENRE, lambda ctx: named_entity_rows(ctx, "genre", "genre_id", "genre_name")),
        (DIM_PERSON, lambda ctx: named_entity_rows(ctx, "person", "person_id", "person_name")),
        (DIM_PRODUCTION_COMPANY,
         lambda ctx: named_entity_rows(ctx, "production_company", "company_id", "company_name")),
        (DIM_PRODUCTION_COUNTRY, production_country_rows),
        (DIM_SPOKEN_LANGUAGE, spoken_language_rows),
        (DIM_ENRICHMENT_FIELD, enrichment_field_rows),
        (DIM_ENRICHMENT_CODE, enrichment_code_rows),
    ]
    scd2 = [(DIM_MOVIE, movie_rows), (DIM_COLLECTION, collection_rows), (DIM_KEYWORD, keyword_rows)]

    def type1_step(dim: Dimension, rows: Callable[[JobContext], DataFrame]) -> Callable[[JobContext], None]:
        return lambda ctx: load_type1_dimension(ctx, dim, rows(ctx))

    def scd2_step(dim: Dimension, rows: Callable[[JobContext], DataFrame]) -> Callable[[JobContext], None]:
        return lambda ctx: load_scd2_dimension(ctx, dim, rows(ctx))

    def bridge_step(bridge: Bridge) -> Callable[[JobContext], None]:
        return lambda ctx: load_bridge(ctx, bridge)

    steps = [(dim.table, type1_step(dim, rows)) for dim, rows in type1]
    steps += [(dim.table, scd2_step(dim, rows)) for dim, rows in scd2]
    steps += [(bridge.table, bridge_step(bridge)) for bridge in BRIDGES]
    steps += [(FACT_SNAPSHOT, load_fact_movie_snapshot), (FACT_ENRICHMENT, load_fact_movie_enrichment)]
    return steps


def run_job(ctx: JobContext) -> None:
    """Ejecuta la corrida completa: lee Bronze, crea lo que falte y sincroniza."""
    started = time.monotonic()
    ctx.bronze = load_bronze(ctx.spark)
    LOG.info("Bronze leído: %d tablas en %.1f s", len(ctx.bronze), time.monotonic() - started)
    create_tables(ctx)
    for table, step in job_steps():
        step_started = time.monotonic()
        step(ctx)
        LOG.debug("%s: %.1f s", table, time.monotonic() - step_started)
    written = sorted(table for table, counts in ctx.report.items() if counts)
    if written:
        LOG.info("Corrida terminada en %.1f s; tablas escritas: %s",
                 time.monotonic() - started, ", ".join(written))
    else:
        LOG.info("Corrida terminada en %.1f s; Silver ya estaba al día y no se escribió nada",
                 time.monotonic() - started)


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
    parser = argparse.ArgumentParser(description="Construye Silver a partir del estado actual de Bronze.")
    parser.add_argument(
        "--run-ts",
        help="Timestamp lógico de la corrida, en ISO 8601 (dag_run.run_after). Por defecto, la hora actual.",
    )
    parser.add_argument(
        "--reference-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "reference",
        help="Directorio de los archivos de referencia. Por defecto, reference/ junto a jobs/.",
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
        run_job(JobContext(spark=spark, run_ts=run_ts, reference_dir=args.reference_dir))
    except SilverJobError as error:
        LOG.error("%s", error)
        return 1
    finally:
        spark.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
