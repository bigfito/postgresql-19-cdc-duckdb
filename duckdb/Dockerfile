# =============================================================================
# ElastiFlix: línea de comandos de DuckDB para explorar el lakehouse (diseño,
# sección 34)
# =============================================================================
# Es una herramienta opcional: no forma parte del flujo. La usa el servicio
# duckdb del Compose, que solo existe bajo el perfil tools:
#
#   docker compose --profile tools run --rm duckdb
#
# Abre DuckDB con el catálogo Iceberg ya adjunto como lake, usando el mismo
# SQL de inicialización que Superset y el simulador (duckdb/init/).
#
# La imagen oficial de DuckDB solo contiene el binario: no trae shell. Aquí
# hace falta una para sustituir las credenciales en ese SQL antes de
# ejecutarlo, así que el binario se copia a una imagen mínima de Debian.

FROM duckdb/duckdb:1.5.6 AS duckdb

FROM debian:trixie-20261104-slim

COPY --from=duckdb /duckdb /usr/local/bin/duckdb

# Usuario sin privilegios (sección 45.2). No escribe en ningún directorio del
# host. Las extensiones van en /opt/duckdb_extensions, la misma ruta que en
# las imágenes de Superset y del simulador: es la que nombra el SQL de
# inicialización.
RUN groupadd --gid 10003 duckdb \
    && useradd --uid 10003 --gid 10003 --create-home --shell /usr/sbin/nologin duckdb \
    && mkdir -p /opt/duckdb_extensions /duckdb/init \
    && chown duckdb:duckdb /opt/duckdb_extensions

USER duckdb
WORKDIR /home/duckdb

# Las tres extensiones se instalan aquí, durante el build. En ejecución solo
# se cargan: el contenedor no descarga nada. iceberg necesita avro y, si no
# la encuentra instalada, intenta bajarla al cargarse. La segunda orden
# comprueba que las tres cargan sin red de por medio.
RUN duckdb -c "SET extension_directory = '/opt/duckdb_extensions'; INSTALL httpfs; INSTALL iceberg; INSTALL avro;" \
    && duckdb -c "SET extension_directory = '/opt/duckdb_extensions'; SET autoinstall_known_extensions = false; LOAD httpfs; LOAD avro; LOAD iceberg; SELECT extension_name, extension_version FROM duckdb_extensions() WHERE loaded AND extension_name IN ('httpfs', 'iceberg', 'avro') ORDER BY 1;"

COPY --chown=root:root --chmod=0755 entrypoint.sh /usr/local/bin/duckdb-lakehouse

ENTRYPOINT ["duckdb-lakehouse"]
