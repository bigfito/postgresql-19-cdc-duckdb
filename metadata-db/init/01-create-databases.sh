#!/usr/bin/env bash
# Crea las cuentas y las bases de metadatos de Airflow y Superset (diseño,
# sección 45.3).
#
# La imagen oficial de PostgreSQL ejecuta este archivo una sola vez, cuando
# metadata-db/data/ está vacío. Si no es ejecutable, lo carga con `source`
# dentro de su propio script de arranque; por eso aquí no se cambian las
# opciones de la shell.
#
# Las contraseñas llegan por variables de entorno desde .env y se pasan a psql
# como variables, de modo que no quedan escritas en ningún archivo.
#
# Cada cuenta es dueña de su base y ninguna puede conectarse a la otra: se
# retira a PUBLIC el permiso de conexión en las dos bases.

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --no-password --no-psqlrc \
     --dbname "$POSTGRES_DB" \
     -v airflow_password="${AIRFLOW_DB_PASSWORD:?falta AIRFLOW_DB_PASSWORD}" \
     -v superset_password="${SUPERSET_DB_PASSWORD:?falta SUPERSET_DB_PASSWORD}" <<'SQL'
CREATE ROLE airflow LOGIN PASSWORD :'airflow_password';
CREATE ROLE superset LOGIN PASSWORD :'superset_password';

CREATE DATABASE airflow OWNER airflow;
CREATE DATABASE superset OWNER superset;

REVOKE ALL ON DATABASE airflow FROM PUBLIC;
REVOKE ALL ON DATABASE superset FROM PUBLIC;
SQL
