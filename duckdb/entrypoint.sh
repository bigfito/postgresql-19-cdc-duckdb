#!/bin/sh
# =============================================================================
# ElastiFlix: arranque de la línea de comandos de DuckDB (diseño, sección 34)
# =============================================================================
# Abre DuckDB con el lakehouse ya adjunto. Ejecuta antes
# /duckdb/init/attach_lakehouse.sql, que es el mismo archivo que usan Superset
# y el simulador, con sus dos marcadores sustituidos por las variables de
# entorno del contenedor.
#
# Los argumentos que reciba se pasan a DuckDB tal cual. Sin argumentos abre la
# consola interactiva; con -c "SQL" ejecuta una consulta y termina.
#
# Las vistas de Gold no se crean aquí: dentro de la consola, y solo cuando
# Gold ya existe, se crean con
#
#   .read /duckdb/init/gold_views.sql

set -eu

INIT_SQL="${DUCKDB_INIT_SQL:-/duckdb/init/attach_lakehouse.sql}"

fail() {
    echo "[duckdb] ERROR: $*" >&2
    exit 1
}

[ -n "${AWS_ACCESS_KEY_ID:-}" ] || fail "falta la variable AWS_ACCESS_KEY_ID. Lanza el contenedor con docker compose, que la toma de .env."
[ -n "${AWS_SECRET_ACCESS_KEY:-}" ] || fail "falta la variable AWS_SECRET_ACCESS_KEY. Lanza el contenedor con docker compose, que la toma de .env."
[ -r "$INIT_SQL" ] || fail "no se puede leer $INIT_SQL. Causa probable: duckdb/init no está montado en /duckdb/init."

# Quita las líneas de comentario y sustituye los marcadores. Los valores se
# leen del entorno dentro de awk, de modo que no pasan por ninguna expresión
# de la shell. En el texto de reemplazo de gsub, & y \ tienen significado
# propio, y por eso se escapan antes.
sql="$(awk '
    function literal(value) { gsub(/[\\&]/, "\\\\&", value); return value }
    BEGIN { key = literal(ENVIRON["AWS_ACCESS_KEY_ID"]); secret = literal(ENVIRON["AWS_SECRET_ACCESS_KEY"]) }
    /^--/ { next }
    {
        gsub(/\$\{AWS_ACCESS_KEY_ID\}/, key)
        gsub(/\$\{AWS_SECRET_ACCESS_KEY\}/, secret)
        print
    }
' "$INIT_SQL")"

# -cmd ejecuta ese SQL antes de leer lo demás. Su salida se descarta, para que
# la consola no empiece con las tablas de «Success» de cada sentencia. Los
# errores sí se ven: van por la salida de error.
exec duckdb -cmd ".output /dev/null" -cmd "$sql" -cmd ".output" "$@"
