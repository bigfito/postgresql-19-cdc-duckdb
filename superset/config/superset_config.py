"""Configuración de Superset para el laboratorio ElastiFlix (diseño, secciones 34 y 35).

Superset carga este archivo al arrancar: está montado en ``/app/pythonpath``,
que la imagen tiene en su ``PYTHONPATH``.

Hace dos cosas:

- **Ajustes.** Los metadatos de Superset van a ``metadata-db`` y la clave que
  firma las sesiones sale de ``.env``. Nada de eso está escrito aquí: llega
  por variables de entorno.
- **Hook de conexión de DuckDB.** DuckDB corre embebido y en memoria, y
  Superset abre una conexión nueva para cada consulta. Cada una empieza vacía,
  así que hay que adjuntarle el catálogo Iceberg y crearle las vistas de Gold.
  Lo hace un listener del evento ``connect`` de SQLAlchemy, que actúa solo
  sobre las conexiones de DuckDB.

Sin el hook, la base ``duckdb:///:memory:`` que registra quien usa el
laboratorio se conectaría bien, pero no vería ninguna tabla.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine

_LOG = logging.getLogger("elastiflix.superset_config")

# Los nombres que empiezan por guion bajo son de este archivo. Superset toma
# como ajuste todo nombre en mayúsculas que encuentre aquí.

# SQL de inicialización de DuckDB, montado en solo lectura desde duckdb/init/.
_DUCKDB_INIT_DIR = Path(os.environ.get("DUCKDB_INIT_DIR", "/duckdb/init"))
_ATTACH_SQL = _DUCKDB_INIT_DIR / "attach_lakehouse.sql"
_GOLD_VIEWS_SQL = _DUCKDB_INIT_DIR / "gold_views.sql"

# Marcadores de attach_lakehouse.sql y variable de entorno de cada uno.
_PLACEHOLDERS = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")

# Forma de cada sentencia de gold_views.sql. De ella sale el nombre del
# producto, para crear solo las vistas cuya tabla ya existe.
_GOLD_VIEW = re.compile(
    r"CREATE OR REPLACE VIEW memory\.main\.(?P<product>\w+) AS SELECT \* FROM lake\.gold\.(?P=product)",
    re.IGNORECASE,
)

_GOLD_TABLES_SQL = (
    "SELECT table_name FROM information_schema.tables "
    "WHERE table_catalog = 'lake' AND table_schema = 'gold'"
)


# =============================================================================
# Ajustes de Superset
# =============================================================================

class ConfigurationError(Exception):
    """Falta un dato imprescindible para arrancar Superset.

    El mensaje dice cuál es, de dónde debería llegar y qué hacer.
    """

    code = "SUPERSET-CFG-001"

    def __str__(self) -> str:
        """El mensaje, precedido del código de error."""
        return f"[{self.code}] {super().__str__()}"


def required_env(name: str) -> str:
    """Valor de una variable de entorno obligatoria.

    Raises:
        ConfigurationError: si la variable falta o está vacía.
    """
    value = os.environ.get(name, "")
    if not value:
        raise ConfigurationError(
            f"Falta la variable de entorno {name}. Causa probable: no está en .env o el servicio "
            "no la recibe en el Compose. Copia .env.example a .env y vuelve a levantar el servicio."
        )
    return value


# Clave que firma las sesiones y cifra las credenciales que Superset guarda.
SECRET_KEY = required_env("SUPERSET_SECRET_KEY")

# Metadatos de Superset en metadata-db, en la base superset y con la cuenta
# superset. La URI completa la arma el Compose a partir de .env.
SQLALCHEMY_DATABASE_URI = required_env("SUPERSET_DATABASE_URI")

# Los límites de peticiones de Superset guardan sus contadores en memoria.
# Con un solo contenedor basta, y se dice aquí para que no avise al arrancar.
RATELIMIT_STORAGE_URI = "memory://"


# =============================================================================
# Hook de conexión de DuckDB
# =============================================================================

def statements(sql_file: Path) -> list[str]:
    """Sentencias de un archivo de duckdb/init/, sin comentarios.

    Los dos archivos siguen una regla: los comentarios van en líneas propias y
    nunca llevan punto y coma. Por eso basta con descartar las líneas de
    comentario y partir el resto por ese carácter.
    """
    lines = [line for line in sql_file.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("--")]
    return [statement.strip() for statement in "\n".join(lines).split(";") if statement.strip()]


def with_credentials(statement: str) -> str:
    """Sustituye los marcadores ``${...}`` por las variables de entorno.

    La clave de RustFS no está en el archivo SQL: llega al contenedor por el
    entorno y se pone aquí, justo antes de ejecutar.
    """
    for name in _PLACEHOLDERS:
        statement = statement.replace("${" + name + "}", required_env(name))
    return statement


def attach_lakehouse(cursor: object) -> None:
    """Carga las extensiones, declara el acceso a RustFS y adjunta el catálogo."""
    for statement in statements(_ATTACH_SQL):
        cursor.execute(with_credentials(statement))


def create_gold_views(cursor: object) -> list[str]:
    """Crea la vista de cada producto de Gold cuya tabla ya existe.

    Antes de la primera corrida del DAG Gold está vacío, y una vista sobre una
    tabla que no existe haría fallar la conexión. Por eso se pregunta primero
    al catálogo qué tablas hay.

    Returns:
        Los productos para los que se creó vista.
    """
    cursor.execute(_GOLD_TABLES_SQL)
    existing = {row[0] for row in cursor.fetchall()}
    created = []
    for statement in statements(_GOLD_VIEWS_SQL):
        match = _GOLD_VIEW.search(statement)
        if match is None:
            _LOG.warning(
                "Sentencia de %s con una forma inesperada; se ignora: %.80s", _GOLD_VIEWS_SQL.name, statement
            )
            continue
        product = match.group("product")
        if product in existing:
            cursor.execute(statement)
            created.append(product)
    return created


@event.listens_for(Engine, "connect")
def initialize_duckdb_connection(dbapi_connection: object, _connection_record: object) -> None:
    """Prepara cada conexión nueva de DuckDB para consultar Gold.

    El listener está registrado sobre la clase ``Engine``, así que SQLAlchemy
    lo llama para todas las conexiones, también las de los metadatos de
    Superset en PostgreSQL. Solo actúa sobre las de DuckDB.

    Un fallo aquí hace fallar la conexión: es lo correcto, porque sin
    catálogo no habría nada que consultar, y el error llega a quien la abrió.
    """
    if not type(dbapi_connection).__module__.startswith("duckdb"):
        return
    cursor = dbapi_connection.cursor()
    try:
        attach_lakehouse(cursor)
        views = create_gold_views(cursor)
    finally:
        cursor.close()
    _LOG.debug("Conexión de DuckDB lista; vistas de Gold: %s", ", ".join(views) or "ninguna")
