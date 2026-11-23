package com.elastiflix.simulator.engine;

import com.elastiflix.simulator.dataset.Dataset;
import com.elastiflix.simulator.db.MovieOperations;
import com.elastiflix.simulator.db.SqlErrors;
import com.elastiflix.simulator.error.ErrorCode;
import com.elastiflix.simulator.error.SimulatorException;
import com.elastiflix.simulator.simulation.ActivityBoard;
import com.elastiflix.simulator.simulation.CatalogLinks;
import com.elastiflix.simulator.simulation.CatalogTarget;
import com.elastiflix.simulator.simulation.ManualAction;
import com.elastiflix.simulator.simulation.MovieRegistry;
import com.elastiflix.simulator.simulation.MovieState;
import com.elastiflix.simulator.simulation.OperationSelector;
import com.elastiflix.simulator.simulation.OperationType;
import com.elastiflix.simulator.simulation.PlannedOperation;
import com.elastiflix.simulator.simulation.SimulationControl;
import com.elastiflix.simulator.simulation.SimulationStatus;
import com.elastiflix.simulator.simulation.TransactionOutcome;
import com.elastiflix.simulator.simulation.TransactionRecord;
import com.elastiflix.simulator.simulation.UpdateKind;

import java.sql.SQLException;
import java.util.Optional;
import java.util.OptionalLong;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * El hilo de la simulación: ejecuta, una tras otra, las transacciones
 * automáticas y las que se piden a mano.
 *
 * <p>Es el único hilo que usa la conexión con PostgreSQL y el generador de
 * números aleatorios. La interfaz no ejecuta nada por su cuenta: deja sus
 * peticiones en una cola y este hilo las atiende entre dos transacciones. Así
 * la pantalla nunca bloquea la simulación (diseño, sección 9.2).</p>
 */
public final class SimulationEngine implements Runnable {

    private static final Logger LOG = Logger.getLogger(SimulationEngine.class.getName());

    private static final String REINSERTION_LABEL = "reinserción";

    /** Cada cuánto se revisa la cola de peticiones mientras se espera el siguiente turno. */
    private static final long MAX_WAIT_MILLIS = 100;

    /** Espera tras un fallo que no es un dato inconsistente, antes de reintentar. */
    private static final long FAILURE_PAUSE_MILLIS = 2_000;

    /** Un UPDATE ya decidido: su tipo y, si es de catálogo, qué renombra. */
    private record UpdateChoice(UpdateKind kind, CatalogTarget target) {
    }

    private final Dataset dataset;
    private final MovieOperations operations;
    private final MovieRegistry registry;
    private final OperationSelector selector;
    private final SimulationControl control;
    private final ActivityBoard board;
    private final boolean continuous;
    private final boolean trackBronze;
    private final BlockingQueue<Runnable> requests = new LinkedBlockingQueue<>();

    private volatile boolean stopped;
    private long lastAutomaticStepNanos = System.nanoTime();
    private boolean finishAnnounced;

    /**
     * @param dataset     dataset en memoria
     * @param operations  transacciones sobre PostgreSQL
     * @param registry    situación de cada película
     * @param selector    elección de la siguiente operación
     * @param control     pausa, intervalo y pesos vigentes
     * @param board       contadores y últimas transacciones
     * @param continuous  si sigue generando cambios al agotar {@code movie.csv}
     * @param trackBronze si las transacciones se siguen hasta Bronze
     */
    public SimulationEngine(Dataset dataset, MovieOperations operations, MovieRegistry registry,
                            OperationSelector selector, SimulationControl control, ActivityBoard board,
                            boolean continuous, boolean trackBronze) {
        this.dataset = dataset;
        this.operations = operations;
        this.registry = registry;
        this.selector = selector;
        this.control = control;
        this.board = board;
        this.continuous = continuous;
        this.trackBronze = trackBronze;
    }

    /** Bucle del hilo de la simulación. Termina con {@link #stop()} o al interrumpir el hilo. */
    @Override
    public void run() {
        while (!stopped) {
            try {
                Runnable request = requests.poll(waitMillis(), TimeUnit.MILLISECONDS);
                if (request != null) {
                    request.run();
                } else if (automaticStepIsDue()) {
                    runAutomaticStep();
                }
                announceFinishOnce();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            } catch (RuntimeException e) {
                LOG.log(Level.SEVERE, "Error inesperado en la simulación; el simulador continúa", e);
            }
        }
    }

    /** Pide al hilo de la simulación que termine tras la transacción en curso. */
    public void stop() {
        stopped = true;
    }

    /** @return el estado que muestra la cabecera de la pantalla */
    public SimulationStatus status() {
        if (isFinished()) {
            return SimulationStatus.FINISHED;
        }
        return control.isPaused() ? SimulationStatus.PAUSED : SimulationStatus.RUNNING;
    }

    /**
     * Encola una operación manual (RF-08). Se ejecuta como una transacción
     * normal, también con la simulación en pausa.
     *
     * @param action  operación pedida
     * @param movieId película elegida; se ignora en {@link ManualAction#INSERT_NEXT}
     */
    public void submitManual(ManualAction action, long movieId) {
        requests.add(() -> runManual(action, movieId));
    }

    /**
     * Pide la colección y las keywords que una película tiene ahora en
     * PostgreSQL. La interfaz lo usa para saber si puede ofrecer el UPDATE de
     * catálogo.
     *
     * @param movieId película viva
     * @return un futuro que se completa cuando el hilo de la simulación responde
     */
    public CompletableFuture<CatalogLinks> askCatalogLinks(long movieId) {
        CompletableFuture<CatalogLinks> answer = new CompletableFuture<>();
        requests.add(() -> {
            try {
                answer.complete(operations.readCatalogLinks(movieId));
            } catch (SQLException e) {
                answer.completeExceptionally(e);
            }
        });
        return answer;
    }

    // ------------------------------------------------------------------
    // Simulación automática
    // ------------------------------------------------------------------

    /** Con el modo continuo desactivado, la simulación termina al agotar {@code movie.csv}. */
    private boolean isFinished() {
        return !continuous && registry.pendingCount() == 0;
    }

    private boolean isAutomaticActive() {
        return !control.isPaused() && !isFinished();
    }

    private long nanosUntilNextStep() {
        long dueAt = lastAutomaticStepNanos + control.delayMillis() * 1_000_000;
        return dueAt - System.nanoTime();
    }

    private boolean automaticStepIsDue() {
        return isAutomaticActive() && nanosUntilNextStep() <= 0;
    }

    /** Nunca espera más de 100 ms: así un cambio de intervalo o de pausa se nota enseguida. */
    private long waitMillis() {
        if (!isAutomaticActive()) {
            return MAX_WAIT_MILLIS;
        }
        long remainingMillis = nanosUntilNextStep() / 1_000_000;
        return Math.max(0, Math.min(MAX_WAIT_MILLIS, remainingMillis));
    }

    private void runAutomaticStep() {
        Optional<PlannedOperation> operation = selector.next(control.weights(), registry, continuous);
        operation.ifPresent(planned -> execute(planned, null, false));
        lastAutomaticStepNanos = System.nanoTime();
    }

    /** También cubre el arranque sobre una base que ya tiene todas las películas. */
    private void announceFinishOnce() {
        if (isFinished() && !finishAnnounced) {
            finishAnnounced = true;
            LOG.info("Simulación TERMINADA: movie.csv agotado y SIMULATOR_CONTINUOUS=false."
                    + " Se siguen aceptando operaciones manuales.");
        }
    }

    // ------------------------------------------------------------------
    // Operaciones manuales
    // ------------------------------------------------------------------

    private void runManual(ManualAction action, long movieId) {
        try {
            PlannedOperation operation = planManual(action, movieId);
            LOG.info("MANUAL " + action.label() + " movie_id=" + operation.movieId());
            execute(operation, action.updateKind(), true);
        } catch (SimulatorException e) {
            LOG.warning(e.getMessage());
        }
    }

    /** Comprueba que la película sigue en la situación que la operación necesita. */
    private PlannedOperation planManual(ManualAction action, long movieId) {
        return switch (action) {
            case INSERT_NEXT -> PlannedOperation.insert(nextPendingOrFail());
            case INSERT -> PlannedOperation.insert(require(movieId, MovieState.PENDING, action));
            case REINSERT -> PlannedOperation.reinsert(require(movieId, MovieState.DELETED, action));
            case DELETE -> PlannedOperation.delete(require(movieId, MovieState.ALIVE, action));
            case UPDATE_DESCRIPTIVE, UPDATE_MEASURES, UPDATE_RELATIONS, UPDATE_CATALOG ->
                    PlannedOperation.update(require(movieId, MovieState.ALIVE, action));
        };
    }

    private long nextPendingOrFail() {
        OptionalLong pending = registry.nextPending();
        if (pending.isEmpty()) {
            throw new SimulatorException(ErrorCode.MANUAL_REJECTED, "no quedan películas pendientes de alta");
        }
        return pending.getAsLong();
    }

    private long require(long movieId, MovieState expected, ManualAction action) {
        MovieState actual = registry.stateOf(movieId);
        if (actual != expected) {
            String situation = actual == null ? "no está en el dataset" : "está " + actual.label();
            throw new SimulatorException(ErrorCode.MANUAL_REJECTED,
                    action.label() + " sobre la película " + movieId + ", que " + situation);
        }
        return movieId;
    }

    // ------------------------------------------------------------------
    // Ejecución de una operación
    // ------------------------------------------------------------------

    /**
     * Ejecuta la operación como una transacción y deja constancia de ella, haya
     * ido bien o mal.
     *
     * @param operation  operación a ejecutar
     * @param forcedKind tipo de UPDATE pedido a mano; {@code null} para que lo elija la semilla
     * @param manual     si la operación se lanzó a mano
     */
    private void execute(PlannedOperation operation, UpdateKind forcedKind, boolean manual) {
        String kindLabel = operation.reinsertion() ? REINSERTION_LABEL : "";
        try {
            UpdateChoice update = null;
            if (operation.type() == OperationType.UPDATE) {
                update = chooseUpdate(operation.movieId(), forcedKind);
                kindLabel = update.kind().label();
            }
            TransactionOutcome outcome = runTransaction(operation, update);
            applyToRegistry(operation);
            publish(TransactionRecord.committed(board.nextSequence(), operation, kindLabel,
                    dataset.title(operation.movieId()), manual, outcome, trackBronze));
        } catch (SQLException | SimulatorException e) {
            handleFailure(operation, kindLabel, manual, e);
        }
    }

    /** Decide el tipo de UPDATE entre los que la película admite (diseño, sección 9.5). */
    private UpdateChoice chooseUpdate(long movieId, UpdateKind forcedKind) throws SQLException {
        if (forcedKind != null && forcedKind != UpdateKind.CATALOG) {
            return new UpdateChoice(forcedKind, null);
        }
        CatalogLinks links = operations.readCatalogLinks(movieId);
        UpdateKind kind = forcedKind != null ? forcedKind : selector.chooseUpdateKind(links);
        if (kind != UpdateKind.CATALOG) {
            return new UpdateChoice(kind, null);
        }
        if (!links.allowCatalogUpdate()) {
            throw new SimulatorException(ErrorCode.MANUAL_REJECTED,
                    "la película " + movieId + " no tiene colección ni keywords que renombrar");
        }
        return new UpdateChoice(kind, selector.chooseCatalogTarget(links));
    }

    private TransactionOutcome runTransaction(PlannedOperation operation, UpdateChoice update) throws SQLException {
        long movieId = operation.movieId();
        return switch (operation.type()) {
            case INSERT -> operations.insert(movieId);
            case DELETE -> operations.delete(movieId);
            case UPDATE -> update.kind() == UpdateKind.CATALOG
                    ? operations.updateCatalog(movieId, update.target())
                    : operations.update(movieId, update.kind());
        };
    }

    private void applyToRegistry(PlannedOperation operation) {
        switch (operation.type()) {
            case INSERT -> registry.markAlive(operation.movieId());
            case DELETE -> registry.markDeleted(operation.movieId());
            case UPDATE -> { }
        }
    }

    private void publish(TransactionRecord record) {
        board.add(record);
        LOG.info(record.logLine());
    }

    // ------------------------------------------------------------------
    // Fallos
    // ------------------------------------------------------------------

    /**
     * La transacción ya está revertida. Un dato inconsistente se registra y la
     * simulación continúa (RF-12); cualquier otro fallo descarta la conexión
     * para que la siguiente operación abra otra.
     */
    private void handleFailure(PlannedOperation operation, String kindLabel, boolean manual, Exception failure) {
        String reason = describeFailure(failure);
        if (isInconsistentData(failure)) {
            giveUpOnMovie(operation, failure);
        } else if (failure instanceof SQLException) {
            operations.discardConnection();
            pauseAfterFailure();
        }
        TransactionRecord record = TransactionRecord.failed(board.nextSequence(), operation, kindLabel,
                dataset.title(operation.movieId()), manual, reason);
        board.add(record);
        LOG.severe(record.logLine());
    }

    private boolean isInconsistentData(Exception failure) {
        if (failure instanceof SQLException sqlFailure) {
            return SqlErrors.isIntegrityViolation(sqlFailure);
        }
        return true;
    }

    private String describeFailure(Exception failure) {
        if (failure instanceof SimulatorException) {
            return failure.getMessage();
        }
        String databaseMessage = oneLine(failure.getMessage());
        ErrorCode code = isInconsistentData(failure) ? ErrorCode.DATA_INCONSISTENT : ErrorCode.TRANSACTION_FAILED;
        return code.message(databaseMessage);
    }

    /**
     * Una película cuya alta falla cuenta como borrada: no se reintenta en el
     * orden normal, pero se puede reinsertar (diseño, sección 9.5). Lo mismo
     * si el simulador la daba por viva y PostgreSQL no la tiene.
     */
    private void giveUpOnMovie(PlannedOperation operation, Exception failure) {
        boolean failedInsert = operation.type() == OperationType.INSERT;
        boolean missing = failure instanceof SimulatorException simulatorFailure
                && simulatorFailure.errorCode() == ErrorCode.MOVIE_MISSING;
        if (failedInsert || missing) {
            registry.markDeleted(operation.movieId());
        }
    }

    private void pauseAfterFailure() {
        try {
            Thread.sleep(FAILURE_PAUSE_MILLIS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    /** El mensaje de PostgreSQL trae el detalle en una segunda línea; aquí va todo en una. */
    private static String oneLine(String text) {
        if (text == null) {
            return "sin mensaje";
        }
        return text.replaceAll("\\s*\\R\\s*", " · ");
    }
}
