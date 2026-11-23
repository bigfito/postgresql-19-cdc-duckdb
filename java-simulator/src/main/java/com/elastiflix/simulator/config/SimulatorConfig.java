package com.elastiflix.simulator.config;

import java.nio.file.Path;

/**
 * Configuración con la que arranca el simulador (diseño, sección 9.6).
 *
 * <p>El intervalo y los pesos son valores iniciales: después se cambian desde
 * la interfaz. Lo que no viene de una variable de entorno (direcciones y
 * rutas dentro del contenedor) está en las constantes de este tipo.</p>
 *
 * @param delayMillis         intervalo inicial entre transacciones
 * @param weights             pesos iniciales de INSERT, UPDATE y DELETE
 * @param randomSeed          semilla de la secuencia automática
 * @param continuous          seguir generando cambios al agotar {@code movie.csv}
 * @param autostart           empezar a simular al arrancar, o esperar en pausa
 * @param trackBronze         activar el seguimiento de cada cambio hasta Bronze
 * @param trackIntervalMillis cada cuánto se consulta Bronze
 * @param trackLateMillis     tiempo tras el que una transacción pendiente pasa a «demorada»
 * @param duckdbThreads       hilos de DuckDB
 * @param duckdbMemoryLimit   memoria de DuckDB, por ejemplo {@code 128MB}
 * @param credentials         contraseñas y claves
 */
public record SimulatorConfig(
        long delayMillis,
        Weights weights,
        long randomSeed,
        boolean continuous,
        boolean autostart,
        boolean trackBronze,
        long trackIntervalMillis,
        long trackLateMillis,
        int duckdbThreads,
        String duckdbMemoryLimit,
        Credentials credentials) {

    /** Base operacional, por el nombre del servicio en la red del Compose. */
    public static final String POSTGRES_URL =
            "jdbc:postgresql://postgresql:5432/elastiflix"
                    + "?ApplicationName=elastiflix-event-simulator&reWriteBatchedInserts=true";

    /** Cuenta de la aplicación (diseño, sección 45.3). */
    public static final String POSTGRES_USER = "elastiflix_app";

    /** Dónde monta el Compose el dataset, en solo lectura. */
    public static final Path RAW_DATA_DIR = Path.of("/raw_data");

    /** SQL de inicialización de DuckDB, montado en solo lectura (diseño, sección 34). */
    public static final Path DUCKDB_INIT_SQL = Path.of("/duckdb/init/attach_lakehouse.sql");

    /** Copia del log, legible aunque la interfaz esté abierta (diseño, sección 9.8). */
    public static final Path LOG_FILE = Path.of("/tmp/simulator.log");
}
