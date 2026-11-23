#!/usr/bin/env bash
# Pone la contraseña a las cuentas elastiflix_app y elastiflix_cdc (diseño,
# sección 45.5).
#
# Las contraseñas llegan por variables de entorno desde .env y se pasan a psql
# como variables suyas: no quedan escritas en ningún archivo versionado ni
# aparecen en la salida. PostgreSQL las guarda cifradas con scram-sha-256.
#
# La imagen oficial de PostgreSQL ejecuta este archivo una sola vez, cuando
# postgresql/data/ está vacío. Si no es ejecutable, lo carga con `source`
# dentro de su propio script de arranque; por eso aquí no se cambian las
# opciones de la shell.
#
# Si falta alguna de las dos variables, la inicialización se detiene con un
# mensaje: una cuenta sin contraseña no podría entrar desde la red, y Flink o
# el simulador fallarían más tarde sin una causa visible.

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --no-password --no-psqlrc \
     --dbname "$POSTGRES_DB" \
     -v app_password="${ELASTIFLIX_APP_PASSWORD:?falta ELASTIFLIX_APP_PASSWORD}" \
     -v cdc_password="${ELASTIFLIX_CDC_PASSWORD:?falta ELASTIFLIX_CDC_PASSWORD}" <<'SQL'
ALTER ROLE elastiflix_app PASSWORD :'app_password';
ALTER ROLE elastiflix_cdc PASSWORD :'cdc_password';
SQL
