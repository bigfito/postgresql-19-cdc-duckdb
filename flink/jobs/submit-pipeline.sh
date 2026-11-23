#!/usr/bin/env bash
# =============================================================================
# ElastiFlix: envío del pipeline de Flink CDC (diseño, sección 14)
# =============================================================================
# Lo ejecuta el job one-shot flink-cdc-submit en cada `docker compose up`. Es
# idempotente de verdad: repetirlo nunca arranca un segundo job. Un segundo
# envío no fallaría, pero repetiría el snapshot sobre las mismas tablas y
# Bronze perdería las marcas +U y la fecha real de cada cambio.
#
# Qué hace, en este orden:
#   1. Si el pipeline ya está en ejecución, termina sin hacer nada.
#   2. Si no lo está y hay un checkpoint retenido, lo reanuda desde el más
#      reciente, sin repetir el snapshot.
#   3. Si no hay ni job ni checkpoint, hace un envío nuevo, con snapshot
#      inicial. Pero si Bronze ya tiene tablas, se ha perdido el estado: no
#      envía nada, no borra nada y termina con error. Bronze se reconstruye
#      con el procedimiento de la sección 38.
#   4. Tras enviar o reanudar, espera a que el job esté en RUNNING. Si no lo
#      consigue en dos minutos, termina con error.
#
# La contraseña de elastiflix_cdc llega por la variable de entorno
# ELASTIFLIX_CDC_PASSWORD. Se escribe solo en una copia temporal del YAML,
# dentro del contenedor, que se borra al terminar.

set -euo pipefail

FLINK_REST="${FLINK_REST:-http://flink-jobmanager:8081}"
CATALOG="${CATALOG:-http://iceberg-rest:8181/v1}"
PIPELINE_FILE="${PIPELINE_FILE:-/opt/flink/jobs/postgres-to-bronze.yaml}"
PIPELINE_NAME="${PIPELINE_NAME:-elastiflix-postgres-to-bronze}"
CHECKPOINT_DIR="${CHECKPOINT_DIR:-/opt/flink/state/checkpoints}"
WAIT_SECONDS="${WAIT_SECONDS:-120}"

log() {
    echo "[flink-cdc-submit] $*"
}

fail() {
    echo "[flink-cdc-submit] ERROR: $*" >&2
    exit 1
}

# Estado del job del pipeline que no ha terminado, o nada si no hay ninguno.
pipeline_state() {
    curl --fail --silent --show-error "$FLINK_REST/jobs/overview" \
        | jq --raw-output --arg name "$PIPELINE_NAME" '
            [.jobs[]
             | select(.name == $name)
             | select(.state != "FINISHED" and .state != "CANCELED" and .state != "FAILED")]
            | first | .state // empty'
}

# Directorio del checkpoint retenido más reciente, o nada si no hay ninguno.
# Cada uno es <job>/chk-<n>/ y está completo cuando contiene _metadata.
latest_checkpoint() {
    [ -d "$CHECKPOINT_DIR" ] || return 0
    find "$CHECKPOINT_DIR" -mindepth 3 -maxdepth 3 -type f -name _metadata \
         -path '*/chk-*/_metadata' -printf '%T@ %h\n' \
        | sort --numeric-sort | tail --lines=1 | cut --delimiter=' ' --fields=2-
}

# Número de tablas que hay en el namespace bronze del catálogo.
bronze_table_count() {
    curl --fail --silent --show-error "$CATALOG/namespaces/bronze/tables" \
        | jq '.identifiers | length'
}

wait_until_running() {
    local deadline=$((SECONDS + WAIT_SECONDS))
    local state=""
    while [ "$SECONDS" -lt "$deadline" ]; do
        state="$(pipeline_state)"
        if [ "$state" = "RUNNING" ]; then
            log "El pipeline $PIPELINE_NAME está en RUNNING."
            return 0
        fi
        sleep 2
    done
    fail "el pipeline no llegó a RUNNING en $WAIT_SECONDS segundos (último estado: ${state:-ninguno})."
}

# --- 1. ¿Ya está en ejecución? -----------------------------------------------
state="$(pipeline_state)"
if [ "$state" = "RUNNING" ]; then
    log "El pipeline $PIPELINE_NAME ya está en ejecución. No se envía de nuevo."
    exit 0
fi
if [ -n "$state" ]; then
    log "El pipeline $PIPELINE_NAME ya existe, en estado $state. Se espera a que arranque."
    wait_until_running
    exit 0
fi

# --- 2 y 3. ¿Reanudar o envío nuevo? -----------------------------------------
checkpoint="$(latest_checkpoint)"
if [ -n "$checkpoint" ]; then
    log "No hay job en ejecución. Se reanuda desde el checkpoint $checkpoint."
else
    tables="$(bronze_table_count)"
    if [ "$tables" -gt 0 ]; then
        fail "no hay job ni checkpoint, pero Bronze ya tiene $tables tablas. Se ha perdido el estado de Flink. No se envía ni se borra nada: reconstruye Bronze con el procedimiento de la sección 38 del diseño."
    fi
    log "No hay job, ni checkpoint, ni tablas en Bronze. Envío nuevo, con snapshot inicial."
fi

# --- Copia temporal del YAML, con la contraseña ------------------------------
: "${ELASTIFLIX_CDC_PASSWORD:?falta ELASTIFLIX_CDC_PASSWORD}"
umask 077
pipeline_copy="$(mktemp --suffix=.yaml /tmp/pipeline.XXXXXX)"
trap 'rm -f "$pipeline_copy"' EXIT
# Solo se sustituye esa variable; cualquier otro $ del YAML queda como está.
envsubst '${ELASTIFLIX_CDC_PASSWORD}' < "$PIPELINE_FILE" > "$pipeline_copy"

# --- Envío --------------------------------------------------------------------
args=("$pipeline_copy" --flink-home "$FLINK_HOME")
if [ -n "$checkpoint" ]; then
    args+=(--from-savepoint "$checkpoint")
fi
"$FLINK_CDC_HOME/bin/flink-cdc.sh" "${args[@]}"

# --- 4. Esperar a RUNNING -----------------------------------------------------
wait_until_running
