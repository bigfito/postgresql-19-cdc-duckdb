#!/usr/bin/env bash
# =============================================================================
# ElastiFlix: borrado de las tablas Bronze, para reconstruirlas (diseño,
# sección 38, «Reconstrucción de Bronze»)
# =============================================================================
# Elimina del catálogo todas las tablas del namespace bronze, con sus archivos
# en RustFS. Es el paso 2 del procedimiento de reconstrucción, que se usa
# cuando se pierden los checkpoints de Flink o PostgreSQL invalida el slot.
#
# NO forma parte del arranque: se lanza a mano, desde la raíz del repositorio:
#
#   docker compose run --rm --no-deps flink-cdc-submit bash /opt/flink/jobs/drop-bronze-tables.sh --confirm
#
# Antes hay que pausar el DAG de Airflow (paso 1), para que bronze_to_silver no
# lea un Bronze a medio cargar. Después se ejecuta flink-cdc-submit (paso 3),
# que al no encontrar job, checkpoint ni tablas hace un envío nuevo.
#
# Salvaguardas:
#   - Sin --confirm no borra nada: solo dice qué borraría.
#   - Se niega si el pipeline está en ejecución: borrar las tablas bajo un job
#     vivo lo dejaría escribiendo sobre tablas que ya no existen.
#   - Solo toca el namespace bronze. Silver y Gold no se tocan nunca.

set -euo pipefail

FLINK_REST="${FLINK_REST:-http://flink-jobmanager:8081}"
CATALOG="${CATALOG:-http://iceberg-rest:8181/v1}"
PIPELINE_NAME="${PIPELINE_NAME:-elastiflix-postgres-to-bronze}"

log() {
    echo "[drop-bronze-tables] $*"
}

fail() {
    echo "[drop-bronze-tables] ERROR: $*" >&2
    exit 1
}

confirm=false
if [ "${1:-}" = "--confirm" ]; then
    confirm=true
elif [ "$#" -gt 0 ]; then
    fail "argumento no reconocido: $1. El único admitido es --confirm."
fi

# El pipeline no puede estar vivo.
state="$(curl --fail --silent --show-error "$FLINK_REST/jobs/overview" \
    | jq --raw-output --arg name "$PIPELINE_NAME" '
        [.jobs[]
         | select(.name == $name)
         | select(.state != "FINISHED" and .state != "CANCELED" and .state != "FAILED")]
        | first | .state // empty')"
if [ -n "$state" ]; then
    fail "el pipeline $PIPELINE_NAME está en estado $state. Bronze solo se reconstruye cuando no hay job."
fi

tables="$(curl --fail --silent --show-error "$CATALOG/namespaces/bronze/tables" \
    | jq --raw-output '.identifiers[].name' | sort)"
if [ -z "$tables" ]; then
    log "El namespace bronze no tiene tablas. No hay nada que borrar."
    exit 0
fi

count="$(printf '%s\n' "$tables" | wc --lines)"
if [ "$confirm" != true ]; then
    log "Se borrarían $count tablas de bronze, con sus archivos:"
    printf '%s\n' "$tables" | sed 's/^/  bronze./'
    log "No se ha borrado nada. Repite el comando con --confirm para borrarlas."
    exit 0
fi

for table in $tables; do
    curl --fail --silent --show-error --output /dev/null --request DELETE \
         "$CATALOG/namespaces/bronze/tables/$table?purgeRequested=true"
    log "Borrada bronze.$table"
done
log "Borradas $count tablas. Ejecuta ahora flink-cdc-submit para repetir el snapshot."
