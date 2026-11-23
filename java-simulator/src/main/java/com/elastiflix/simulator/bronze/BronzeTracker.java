package com.elastiflix.simulator.bronze;

import com.elastiflix.simulator.bronze.BronzeConnection.BronzeRow;
import com.elastiflix.simulator.config.Credentials;
import com.elastiflix.simulator.config.SimulatorConfig;
import com.elastiflix.simulator.error.ErrorCode;
import com.elastiflix.simulator.simulation.ActivityBoard;
import com.elastiflix.simulator.simulation.BronzeStatus;
import com.elastiflix.simulator.simulation.TransactionRecord;

import java.nio.file.Path;
import java.sql.SQLException;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TreeSet;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * Sigue cada transacción reciente hasta Bronze (RF-09; diseño, sección 9.3).
 *
 * <p>Un hilo propio es el dueño de la conexión de DuckDB y hace todas las
 * consultas. Cada pocos segundos pregunta, en una sola consulta, por las
 * películas con transacciones pendientes y marca las que ya llegaron. Es de
 * solo lectura y opcional: si Bronze no responde, las transacciones siguen y
 * la conexión se reabre en el siguiente sondeo.</p>
 */
public final class BronzeTracker implements AutoCloseable {

    /** Estado de la conexión con Bronze, para la cabecera de la pantalla. */
    public enum State {
        DISABLED("desactivado"),
        CONNECTING("conectando"),
        CONNECTED("conectado"),
        /** La última consulta falló; la columna de seguimiento muestra «sin datos». */
        NO_DATA("sin datos"),
        /** Hay transacciones que llevan demasiado tiempo sin aparecer. */
        STALLED("no avanza");

        private final String label;

        State(String label) {
            this.label = label;
        }

        /** @return el texto de la cabecera */
        public String label() {
            return label;
        }
    }

    private static final Logger LOG = Logger.getLogger(BronzeTracker.class.getName());

    private final SimulatorConfig config;
    private final ActivityBoard board;
    private final Path initSqlFile;
    private final ScheduledExecutorService executor;
    private volatile State state;

    /** Solo la usa el hilo del seguimiento. */
    private BronzeConnection connection;

    /** Si alguna consulta de seguimiento ha funcionado ya. Solo la usa el hilo del seguimiento. */
    private boolean hasAnswered;

    /**
     * @param config      configuración: intervalo de sondeo, umbral de demora y límites de DuckDB
     * @param board       últimas transacciones, donde se anota el resultado
     * @param initSqlFile ruta de {@code attach_lakehouse.sql}
     */
    public BronzeTracker(SimulatorConfig config, ActivityBoard board, Path initSqlFile) {
        this.config = config;
        this.board = board;
        this.initSqlFile = initSqlFile;
        this.state = config.trackBronze() ? State.CONNECTING : State.DISABLED;
        this.executor = Executors.newSingleThreadScheduledExecutor(task -> {
            Thread thread = new Thread(task, "bronze-tracker");
            thread.setDaemon(true);
            return thread;
        });
    }

    /** Empieza a sondear Bronze. Si el seguimiento está desactivado, no hace nada. */
    public void start() {
        if (!config.trackBronze()) {
            LOG.info("Seguimiento hasta Bronze desactivado (SIMULATOR_TRACK_BRONZE=false)");
            return;
        }
        long interval = config.trackIntervalMillis();
        executor.scheduleWithFixedDelay(this::pollSafely, 0, interval, TimeUnit.MILLISECONDS);
        LOG.info("Seguimiento hasta Bronze activado: sondeo cada " + interval + " ms, demora a los "
                + config.trackLateMillis() + " ms");
    }

    /** @return el estado de la conexión con Bronze */
    public State state() {
        return state;
    }

    /** Un sondeo no puede lanzar ninguna excepción: el ejecutor dejaría de repetirlo. */
    private void pollSafely() {
        try {
            poll();
        } catch (SQLException | RuntimeException e) {
            onQueryFailure(e);
        }
    }

    private void poll() throws SQLException {
        List<TransactionRecord> waiting = board.awaitingBronze();
        ensureConnection();
        Map<Long, BronzeRow> rows = connection.readMovieRows(movieIdsOf(waiting));
        hasAnswered = hasAnswered || !waiting.isEmpty();
        List<Long> delays = markArrived(waiting, rows);
        int late = markLate(waiting);
        changeState(late > 0 ? State.STALLED : State.CONNECTED, late);
        if (!delays.isEmpty()) {
            LOG.info("BRONZE confirmadas=" + delays.size()
                    + " retraso_s=" + seconds(Collections.min(delays)) + "-" + seconds(Collections.max(delays))
                    + " pendientes=" + (waiting.size() - delays.size())
                    + " demoradas=" + late);
        }
    }

    private static String seconds(long millis) {
        return String.format(Locale.US, "%.1f", millis / 1000.0);
    }

    private void ensureConnection() throws SQLException {
        if (connection == null) {
            List<String> initStatements = InitSqlScript.load(initSqlFile, sqlVariables());
            connection = BronzeConnection.open(config.duckdbThreads(), config.duckdbMemoryLimit(), initStatements);
            LOG.log(hasAnswered ? Level.FINE : Level.INFO, "DuckDB conectado al catálogo Iceberg (threads="
                    + config.duckdbThreads() + ", memory_limit=" + config.duckdbMemoryLimit() + ")");
        }
    }

    private Map<String, String> sqlVariables() {
        Credentials credentials = config.credentials();
        return Map.of(
                "AWS_ACCESS_KEY_ID", credentials.awsAccessKeyId(),
                "AWS_SECRET_ACCESS_KEY", credentials.awsSecretAccessKey());
    }

    private static TreeSet<Long> movieIdsOf(List<TransactionRecord> records) {
        TreeSet<Long> movieIds = new TreeSet<>();
        for (TransactionRecord record : records) {
            movieIds.add(record.movieId());
        }
        return movieIds;
    }

    /** @return el retraso, en milisegundos, de cada transacción que se ha visto llegar en este sondeo */
    private List<Long> markArrived(List<TransactionRecord> waiting, Map<Long, BronzeRow> rows) {
        Instant now = Instant.now();
        List<Long> delays = new ArrayList<>();
        for (TransactionRecord record : waiting) {
            BronzeRow row = rows.get(record.movieId());
            if (row != null && BronzeMatcher.hasArrived(
                    record.type(), record.referenceMillis(), row.cdcOpType(), row.cdcOpTs())) {
                long delayMillis = Duration.between(record.finishedAt(), now).toMillis();
                record.markArrived(delayMillis);
                delays.add(delayMillis);
            }
        }
        return delays;
    }

    /**
     * Marca como demoradas las que superan el umbral. Se siguen comprobando: si
     * el cambio llega después, pasan a confirmadas con su tiempo real.
     *
     * @return cuántas transacciones están demoradas tras este sondeo
     */
    private int markLate(List<TransactionRecord> waiting) {
        Instant now = Instant.now();
        int late = 0;
        for (TransactionRecord record : waiting) {
            BronzeStatus status = record.bronze().status();
            boolean overdue = Duration.between(record.finishedAt(), now).toMillis() > config.trackLateMillis();
            if (status == BronzeStatus.PENDING && overdue) {
                record.markLate();
                late++;
            } else if (status == BronzeStatus.LATE) {
                late++;
            }
        }
        return late;
    }

    /** El cambio de estado se anota una vez, no en cada sondeo. */
    private void changeState(State newState, int lateCount) {
        if (state == newState) {
            return;
        }
        if (newState == State.STALLED) {
            LOG.warning("BRONZE no avanza: " + lateCount + " transacciones llevan más de "
                    + config.trackLateMillis() + " ms sin aparecer. Comprueba el pipeline de Flink.");
        } else if (state == State.STALLED || state == State.NO_DATA) {
            LOG.info("BRONZE responde con normalidad");
        }
        state = newState;
    }

    /** Ante cualquier fallo se cierra la conexión; el siguiente sondeo abre otra. */
    private void onQueryFailure(Exception failure) {
        closeConnection();
        markLate(board.awaitingBronze());
        if (state != State.NO_DATA) {
            logQueryFailure(withoutSecrets(failure.getMessage()));
        }
        state = State.NO_DATA;
    }

    /**
     * Mientras Bronze no haya respondido nunca, el fallo es lo esperado en el
     * arranque: Flink crea cada tabla cuando le llega su primer cambio.
     */
    private void logQueryFailure(String reason) {
        if (hasAnswered) {
            LOG.warning(ErrorCode.BRONZE_QUERY.message(reason));
        } else {
            LOG.info("BRONZE aún no responde; es normal en el arranque, hasta que Flink crea la tabla movie."
                    + " Se reintenta cada " + config.trackIntervalMillis() + " ms. Motivo: " + reason);
        }
    }

    /** Por si DuckDB repite en un mensaje de error la sentencia que lleva las claves. */
    private String withoutSecrets(String message) {
        if (message == null) {
            return "sin mensaje";
        }
        Credentials credentials = config.credentials();
        return message
                .replace(credentials.awsSecretAccessKey(), "***")
                .replace(credentials.awsAccessKeyId(), "***")
                .replaceAll("\\s*\\R\\s*", " · ");
    }

    private void closeConnection() {
        if (connection == null) {
            return;
        }
        try {
            connection.close();
        } catch (SQLException e) {
            LOG.log(Level.FINE, "Error al cerrar DuckDB: " + e.getMessage());
        }
        connection = null;
    }

    /** Detiene el sondeo y cierra DuckDB desde su propio hilo. */
    @Override
    public void close() {
        executor.execute(this::closeConnection);
        executor.shutdown();
    }
}
