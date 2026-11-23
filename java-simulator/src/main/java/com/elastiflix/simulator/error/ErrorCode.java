package com.elastiflix.simulator.error;

/**
 * Códigos de error del simulador.
 *
 * <p>Cada código dice qué pasó y qué puede hacer quien lo lee. Aparecen en el
 * log entre corchetes, por ejemplo {@code [SIM-021]}, para poder buscarlos.</p>
 */
public enum ErrorCode {

    /** Una variable de entorno falta o tiene un valor que no se entiende. */
    CONFIG_INVALID("SIM-001",
            "La configuración no es válida",
            "Revisa las variables del simulador en .env (diseño, sección 9.6)"),

    /** Falta alguno de los 20 archivos del dataset. */
    DATASET_FILE_MISSING("SIM-010",
            "Falta un archivo del dataset",
            "Comprueba que raw_data/ está montado y contiene los 20 CSV"),

    /** Un CSV no tiene la cabecera o los valores que el diseño describe. */
    DATASET_FORMAT("SIM-011",
            "Un archivo del dataset no tiene el formato esperado",
            "Regenera el dataset con raw_data/generate_raw_data.py"),

    /** No se pudo abrir la conexión con PostgreSQL. */
    POSTGRES_CONNECTION("SIM-020",
            "No se pudo conectar con PostgreSQL",
            "Comprueba que el servicio postgresql está sano y que ELASTIFLIX_APP_PASSWORD es correcta"),

    /** Clave duplicada, referencia inexistente o película que no está donde debería (RF-12). */
    DATA_INCONSISTENT("SIM-021",
            "Dato inconsistente: la transacción se revirtió",
            "No requiere acción: el simulador continúa con la siguiente operación"),

    /** La transacción falló por un motivo que no es un dato inconsistente. */
    TRANSACTION_FAILED("SIM-022",
            "La transacción falló y se revirtió",
            "Revisa el estado de PostgreSQL; el simulador reabre la conexión y continúa"),

    /** El simulador daba la película por viva, pero no está en PostgreSQL. */
    MOVIE_MISSING("SIM-023",
            "La película no está en PostgreSQL: la transacción se revirtió",
            "No requiere acción: el simulador la da por borrada y continúa"),

    /** Se pidió a mano una operación que la película no admite en su situación actual. */
    MANUAL_REJECTED("SIM-024",
            "La operación manual no se puede ejecutar",
            "Elige una operación que corresponda a la situación de la película"),

    /** No se pudo leer o preparar el SQL de inicialización de DuckDB. */
    BRONZE_INIT_SQL("SIM-030",
            "No se pudo leer el SQL de inicialización de DuckDB",
            "Comprueba que duckdb/init/attach_lakehouse.sql está montado"),

    /** La consulta de seguimiento a Bronze falló. */
    BRONZE_QUERY("SIM-031",
            "No se pudo consultar Bronze",
            "Comprueba iceberg-rest, rustfs y el pipeline de Flink; las transacciones siguen"),

    /** La terminal no permite abrir la interfaz. */
    TERMINAL("SIM-040",
            "No se pudo usar la terminal para la interfaz",
            "El simulador sigue en modo de líneas");

    private final String code;
    private final String description;
    private final String action;

    ErrorCode(String code, String description, String action) {
        this.code = code;
        this.description = description;
        this.action = action;
    }

    /** @return el identificador corto, por ejemplo {@code SIM-021} */
    public String code() {
        return code;
    }

    /**
     * Compone el mensaje completo de un error.
     *
     * @param detail lo concreto de este caso: qué archivo, qué película, qué valor
     * @return el texto con código, descripción, detalle y acción sugerida
     */
    public String message(String detail) {
        return "[" + code + "] " + description + ": " + detail + ". Qué hacer: " + action + ".";
    }
}
