# =============================================================================
# ElastiFlix: imagen de Superset con DuckDB (diseño, secciones 34 y 35)
# =============================================================================
# La usan el servicio superset y el job superset-init del Compose.
#
# Superset consulta Gold con DuckDB, que no es un servidor: es una librería
# que corre dentro de este mismo contenedor. Por eso la imagen oficial
# necesita tres cosas más:
#   - duckdb y duckdb-engine, el motor y su dialecto para SQLAlchemy;
#   - psycopg2-binary, para los metadatos del propio Superset en metadata-db:
#     la imagen de la serie 6.1 no trae ningún driver de base de datos;
#   - las extensiones de DuckDB que leen Iceberg desde RustFS.
#
# Se usa la variante -py312: la etiqueta 6.1.0 a secas trae Python 3.10.
# Superset 6.1.0 admite duckdb>=1.4.2,<2.

FROM apache/superset:6.1.0-py312

ARG DUCKDB_VERSION=1.5.6
ARG DUCKDB_ENGINE_VERSION=0.17.0
ARG PSYCOPG2_VERSION=2.9.13

USER root

# Los paquetes van en el entorno virtual de la imagen, /app/.venv, que es de
# root. uv ya viene en la imagen base.
RUN uv pip install --python /app/.venv/bin/python --no-cache \
        "duckdb==${DUCKDB_VERSION}" \
        "duckdb-engine==${DUCKDB_ENGINE_VERSION}" \
        "psycopg2-binary==${PSYCOPG2_VERSION}" \
    # Directorio propio para las extensiones. El que DuckDB usa por defecto
    # cuelga del HOME, que aquí es /app/superset_home: el volumen que el
    # Compose monta en esa ruta taparía lo instalado durante el build.
    && mkdir -p /opt/duckdb_extensions \
    && chown superset:superset /opt/duckdb_extensions

USER superset

# Las tres extensiones se instalan aquí, durante el build. En ejecución solo
# se cargan: el contenedor no descarga nada. iceberg necesita avro y, si no
# la encuentra instalada, intenta bajarla al cargarse. La segunda conexión
# comprueba que las tres cargan con la instalación automática desactivada.
RUN python -c "\
import duckdb; \
con = duckdb.connect(); \
con.execute(\"SET extension_directory = '/opt/duckdb_extensions'\"); \
[con.execute(f'INSTALL {name}') for name in ('httpfs', 'iceberg', 'avro')]; \
con.close(); \
con = duckdb.connect(); \
con.execute(\"SET extension_directory = '/opt/duckdb_extensions'\"); \
con.execute('SET autoinstall_known_extensions = false'); \
[con.execute(f'LOAD {name}') for name in ('httpfs', 'avro', 'iceberg')]; \
print('duckdb', duckdb.__version__, con.execute(\"SELECT list(extension_name ORDER BY extension_name) FROM duckdb_extensions() WHERE loaded AND extension_name IN ('httpfs', 'iceberg', 'avro')\").fetchone()[0]); \
import duckdb_engine, psycopg2; \
print('duckdb-engine', duckdb_engine.__version__, '| psycopg2', psycopg2.__version__)"
