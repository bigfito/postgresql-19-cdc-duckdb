"""Job PySpark de mantenimiento de las tablas Iceberg (diseño, secciones 18 y 38).

Es la última tarea del DAG y corre siempre, aunque falle una tarea anterior.
Hace dos cosas, según la capa:

- **Bronze: compactar y expirar.** Flink escribe un commit por checkpoint y por
  tabla, con deletes de igualdad: en una hora se acumulan miles de archivos
  pequeños, y cada lectura tiene que abrirlos todos y aplicar los deletes. La
  compactación reescribe cada tabla en pocos archivos, ya sin deletes.
- **Silver y Gold: solo expirar.** Cada MERGE de Silver y cada recarga de Gold
  dejan un snapshot más; sus archivos ya son pocos.

Expirar snapshots es lo que borra de RustFS los archivos que ya nadie usa. De
cada tabla se conservan los cinco últimos snapshots.

El job recorre las tablas que existen en el catálogo, así que no falla si una
capa todavía está vacía. Si una tabla da error, lo anota, sigue con las demás y
termina con código 1, para que la tarea de Airflow quede en error sin dejar a
medias el resto del mantenimiento.

Cómo se lanza (modo cliente, contra el clúster standalone)::

    spark-submit /opt/spark/jobs/iceberg_maintenance.py

A mano, desde la raíz del repositorio::

    docker compose run --rm --no-deps spark-worker spark-submit /opt/spark/jobs/iceberg_maintenance.py
"""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

from py4j.protocol import Py4JJavaError
from pyspark.sql import Row, SparkSession

LOG = logging.getLogger("iceberg_maintenance")

APP_NAME = "iceberg_maintenance"
CATALOG = "lake"

# Capas, en el orden en que se tratan, y si sus tablas se compactan.
NAMESPACES = (("bronze", True), ("silver", False), ("gold", False))

# Snapshots que se conservan de cada tabla (sección 38).
RETAINED_SNAPSHOTS = 5

# Intentos de compactar una tabla cuando Flink confirma un checkpoint a la vez,
# y texto con el que Iceberg avisa de ese cruce.
CONFLICT_ATTEMPTS = 3
CONFLICT_MARK = "Cannot remove dangling deletes"


class MaintenanceError(Exception):
    """El mantenimiento de una o más tablas falló.

    El mensaje dice cuántas y cuáles; el detalle de cada una queda en el log.
    """

    code = "MAINT-001"

    def __str__(self) -> str:
        """El mensaje, precedido del código de error."""
        return f"[{self.code}] {super().__str__()}"


@dataclass
class Totals:
    """Lo que hizo la corrida, sumado sobre todas las tablas."""

    tables: int = 0
    rewritten_data_files: int = 0
    added_data_files: int = 0
    removed_delete_files: int = 0
    deleted_files: int = 0
    failed: list[str] = field(default_factory=list)


def existing_tables(spark: SparkSession, namespace: str) -> list[str]:
    """Tablas que existen ahora en una capa, en orden alfabético."""
    rows = spark.sql(f"SHOW TABLES IN {CATALOG}.{namespace}").collect()
    return sorted(row["tableName"] for row in rows)


def call(spark: SparkSession, procedure: str, table: str, arguments: str = "") -> Row:
    """Ejecuta un procedimiento de Iceberg sobre una tabla y devuelve su resultado."""
    extra = f", {arguments}" if arguments else ""
    return spark.sql(f"CALL {CATALOG}.system.{procedure}(table => '{table}'{extra})").first()


def rewrite_data_files(spark: SparkSession, table: str) -> Row | None:
    """Reescribe los archivos de datos de una tabla, reintentando si Flink se cruza.

    Flink escribe en Bronze mientras el job corre. Si confirma un checkpoint
    justo entre la reescritura y la retirada de los deletes sobrantes, Iceberg
    rechaza esta última («Cannot remove dangling deletes: current snapshot
    changed»). No se pierde nada: basta con repetir.

    Returns:
        El resultado del procedimiento, o ``None`` si Flink se cruzó en todos
        los intentos; en ese caso la tabla queda para la corrida siguiente.
    """
    for attempt in range(1, CONFLICT_ATTEMPTS + 1):
        try:
            return call(
                spark, "rewrite_data_files", table,
                "options => map('rewrite-all', 'true', 'remove-dangling-deletes', 'true')",
            )
        except Py4JJavaError as error:
            if CONFLICT_MARK not in str(error.java_exception):
                raise
            LOG.warning(
                "%s: Flink escribió en la tabla durante la compactación (intento %d de %d)",
                table, attempt, CONFLICT_ATTEMPTS,
            )
    return None


def compact(spark: SparkSession, table: str, totals: Totals) -> None:
    """Reescribe una tabla en pocos archivos y retira los deletes ya aplicados.

    ``rewrite-all`` reescribe todos los archivos, que es lo adecuado mientras
    las tablas sean pequeñas. Puede correr con Flink escribiendo en la tabla.
    """
    data = rewrite_data_files(spark, table)
    if data is None:
        LOG.warning("%s: sin compactar en esta corrida; lo intenta la siguiente", table)
        return
    call(spark, "rewrite_position_delete_files", table, "options => map('rewrite-all', 'true')")
    result = data.asDict()
    removed_deletes = result.get("removed_delete_files_count", 0)
    totals.rewritten_data_files += result["rewritten_data_files_count"]
    totals.added_data_files += result["added_data_files_count"]
    totals.removed_delete_files += removed_deletes
    LOG.info(
        "%s: compactada, %d archivos de datos pasan a %d; %d archivos de borrado retirados",
        table, result["rewritten_data_files_count"], result["added_data_files_count"], removed_deletes,
    )


def expire(spark: SparkSession, table: str, older_than: datetime, totals: Totals) -> None:
    """Expira los snapshots de una tabla, conservando los últimos.

    ``older_than`` es obligatorio aquí: por defecto el procedimiento solo
    expira snapshots de más de cinco días, así que en un laboratorio que lleva
    horas en marcha ``retain_last`` por sí solo no expiraría ninguno.
    """
    cutoff = older_than.strftime("%Y-%m-%d %H:%M:%S")
    result = call(
        spark, "expire_snapshots", table,
        f"older_than => TIMESTAMP '{cutoff}', retain_last => {RETAINED_SNAPSHOTS}",
    )
    deleted = sum(result[name] for name in result.asDict() if name.startswith("deleted_"))
    totals.deleted_files += deleted
    LOG.info("%s: snapshots expirados, %d archivos borrados", table, deleted)


def maintain_table(spark: SparkSession, table: str, older_than: datetime, totals: Totals, *,
                   compact_it: bool) -> None:
    """Mantiene una tabla; si falla, lo anota y deja seguir con las demás."""
    try:
        if compact_it:
            compact(spark, table, totals)
        expire(spark, table, older_than, totals)
        totals.tables += 1
    except Exception:
        # Se captura todo a propósito: una tabla con problemas no debe dejar
        # sin mantenimiento a las demás. El error no se pierde: queda en el
        # log con su traza y el job termina con código 1.
        LOG.exception("%s: el mantenimiento falló; se sigue con las demás tablas", table)
        totals.failed.append(table)


def run_job(spark: SparkSession) -> None:
    """Recorre las tres capas y mantiene cada tabla que existe.

    Raises:
        MaintenanceError: si el mantenimiento de alguna tabla falló.
    """
    started = time.monotonic()
    older_than = datetime.now(UTC)
    totals = Totals()
    for namespace, compact_it in NAMESPACES:
        tables = existing_tables(spark, namespace)
        LOG.info("%s: %d tablas", namespace, len(tables))
        for name in tables:
            maintain_table(spark, f"{namespace}.{name}", older_than, totals, compact_it=compact_it)
    LOG.info(
        "Corrida terminada en %.1f s; %d tablas mantenidas; %d archivos de datos compactados en %d; "
        "%d archivos de borrado retirados; %d archivos borrados al expirar snapshots",
        time.monotonic() - started, totals.tables, totals.rewritten_data_files,
        totals.added_data_files, totals.removed_delete_files, totals.deleted_files,
    )
    if totals.failed:
        raise MaintenanceError(
            f"El mantenimiento falló en {len(totals.failed)} tablas: {', '.join(totals.failed)}. "
            "El detalle de cada una está más arriba en el log. Causa probable: un conflicto de "
            "commit con otra escritura o un fallo al leer o borrar archivos en RustFS. Las demás "
            "tablas sí se mantuvieron; la corrida siguiente lo vuelve a intentar."
        )


def main() -> int:
    """Punto de entrada. Devuelve el código de salida del proceso."""
    logging.basicConfig(
        level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    spark = SparkSession.builder.appName(APP_NAME).getOrCreate()
    # Los mensajes INFO de Spark tapan los del job; se dejan sus avisos y errores.
    spark.sparkContext.setLogLevel("WARN")
    try:
        run_job(spark)
    except MaintenanceError as error:
        LOG.error("%s", error)
        return 1
    finally:
        spark.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
