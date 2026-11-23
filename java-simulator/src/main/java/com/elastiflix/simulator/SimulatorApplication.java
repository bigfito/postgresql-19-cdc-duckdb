package com.elastiflix.simulator;

import com.elastiflix.simulator.bronze.BronzeTracker;
import com.elastiflix.simulator.config.ConfigLoader;
import com.elastiflix.simulator.config.SimulatorConfig;
import com.elastiflix.simulator.dataset.Dataset;
import com.elastiflix.simulator.dataset.DatasetLoader;
import com.elastiflix.simulator.db.DatabaseStateReader;
import com.elastiflix.simulator.db.InsertedKeys;
import com.elastiflix.simulator.db.MovieOperations;
import com.elastiflix.simulator.db.PostgresSession;
import com.elastiflix.simulator.engine.SimulationEngine;
import com.elastiflix.simulator.error.ErrorCode;
import com.elastiflix.simulator.error.SimulatorException;
import com.elastiflix.simulator.logging.SimulatorLogging;
import com.elastiflix.simulator.simulation.ActivityBoard;
import com.elastiflix.simulator.simulation.MovieRegistry;
import com.elastiflix.simulator.simulation.OperationSelector;
import com.elastiflix.simulator.simulation.SimulationControl;
import com.elastiflix.simulator.ui.ConsoleUi;
import com.elastiflix.simulator.ui.UiContext;

import java.sql.SQLException;
import java.util.Random;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * Punto de entrada del Event Simulator (diseño, sección 9).
 *
 * <p>Arranca siempre en modo de líneas: carga el dataset, se conecta a
 * PostgreSQL, mira qué hay ya insertado y empieza a simular. La interfaz y el
 * seguimiento hasta Bronze corren en hilos aparte y no frenan la simulación.</p>
 */
public final class SimulatorApplication {

    private static final Logger LOG = Logger.getLogger(SimulatorApplication.class.getName());

    private static final int CONNECTION_ATTEMPTS = 12;
    private static final long CONNECTION_RETRY_MILLIS = 5_000;
    private static final long SHUTDOWN_WAIT_MILLIS = 5_000;

    private SimulatorApplication() {
    }

    /**
     * @param args no se usan; la configuración llega por variables de entorno
     */
    public static void main(String[] args) {
        SimulatorLogging.configure(SimulatorConfig.LOG_FILE);
        try {
            start();
        } catch (SimulatorException e) {
            LOG.severe(e.getMessage());
            System.exit(1);
        } catch (SQLException e) {
            LOG.log(Level.SEVERE, ErrorCode.POSTGRES_CONNECTION.message(e.getMessage()), e);
            System.exit(1);
        }
    }

    private static void start() throws SQLException {
        LOG.info("ElastiFlix Event Simulator: arrancando");
        SimulatorConfig config = new ConfigLoader(System.getenv()).load();
        logConfig(config);
        Dataset dataset = new DatasetLoader().load(SimulatorConfig.RAW_DATA_DIR);

        PostgresSession session = new PostgresSession(SimulatorConfig.POSTGRES_URL, SimulatorConfig.POSTGRES_USER,
                config.credentials().postgresPassword());
        connectWithRetries(session);

        DatabaseStateReader stateReader = new DatabaseStateReader(session);
        InsertedKeys insertedKeys = stateReader.readInsertedKeys();
        MovieRegistry registry = new MovieRegistry(dataset.movieIds(), stateReader.readMovieIds());
        logStartingPoint(registry, insertedKeys);

        Random random = new Random(config.randomSeed());
        ActivityBoard board = new ActivityBoard();
        SimulationControl control = new SimulationControl(!config.autostart(), config.delayMillis(), config.weights());
        SimulationEngine engine = new SimulationEngine(dataset,
                new MovieOperations(session, dataset, insertedKeys, random), registry,
                new OperationSelector(random), control, board, config.continuous(), config.trackBronze());
        BronzeTracker tracker = new BronzeTracker(config, board, SimulatorConfig.DUCKDB_INIT_SQL);

        Thread engineThread = new Thread(engine, "simulation");
        Thread uiThread = new Thread(
                new ConsoleUi(new UiContext(dataset, registry, board, control, engine, tracker, session,
                        config.randomSeed())), "console-ui");
        uiThread.setDaemon(true);
        Runtime.getRuntime().addShutdownHook(
                new Thread(() -> shutdown(engine, engineThread, tracker, session), "shutdown"));

        tracker.start();
        engineThread.start();
        uiThread.start();
        LOG.info(config.autostart()
                ? "Simulación en marcha"
                : "Simulación en pausa (SIMULATOR_AUTOSTART=false): se reanuda desde la interfaz con Espacio");
    }

    private static void logConfig(SimulatorConfig config) {
        LOG.info("CONFIG intervalo=" + config.delayMillis() + " ms"
                + " pesos INSERT/UPDATE/DELETE=" + config.weights().insert() + "/" + config.weights().update()
                + "/" + config.weights().delete()
                + " semilla=" + config.randomSeed()
                + " continuo=" + config.continuous()
                + " autoarranque=" + config.autostart()
                + " seguimiento_bronze=" + config.trackBronze());
    }

    /** PostgreSQL ya debería estar sano; los reintentos cubren un arranque lento. */
    private static void connectWithRetries(PostgresSession session) throws SQLException {
        for (int attempt = 1; ; attempt++) {
            try {
                session.connection();
                return;
            } catch (SQLException e) {
                if (attempt == CONNECTION_ATTEMPTS) {
                    throw e;
                }
                LOG.warning(ErrorCode.POSTGRES_CONNECTION.message(
                        "intento " + attempt + " de " + CONNECTION_ATTEMPTS + ": " + e.getMessage()));
                sleep(CONNECTION_RETRY_MILLIS);
            }
        }
    }

    /** Deja en el log desde dónde continúa el simulador (RF-13). */
    private static void logStartingPoint(MovieRegistry registry, InsertedKeys insertedKeys) {
        if (registry.aliveCount() == 0 && insertedKeys.totalCount() == 0) {
            LOG.info("PostgreSQL está vacío: la simulación empieza por la primera película de movie.csv");
            return;
        }
        String next = registry.nextPending().isPresent()
                ? "la siguiente pendiente es la " + registry.nextPending().getAsLong()
                : "no queda ninguna pendiente";
        LOG.info("PostgreSQL ya tiene datos: " + registry.aliveCount() + " películas presentes, "
                + registry.deletedCount() + " que faltan y cuentan como borradas, "
                + registry.pendingCount() + " pendientes; " + next + ". "
                + insertedKeys.totalCount() + " filas de catálogos y entidades se dan por insertadas.");
    }

    /** Al recibir la señal de parada: termina la transacción en curso y cierra las conexiones. */
    private static void shutdown(SimulationEngine engine, Thread engineThread, BronzeTracker tracker,
                                 PostgresSession session) {
        SimulatorLogging.logDuringShutdown("Deteniendo el simulador");
        engine.stop();
        try {
            engineThread.join(SHUTDOWN_WAIT_MILLIS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        tracker.close();
        session.close();
        SimulatorLogging.logDuringShutdown(
                "Simulador detenido. `docker compose start java-simulator` continúa donde quedó.");
    }

    private static void sleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new SimulatorException(ErrorCode.POSTGRES_CONNECTION, "arranque interrumpido", e);
        }
    }
}
