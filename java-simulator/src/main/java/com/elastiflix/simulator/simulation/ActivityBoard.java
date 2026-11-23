package com.elastiflix.simulator.simulation;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;

/**
 * Lo que el simulador ha hecho en esta ejecución: los contadores y las últimas
 * transacciones (RF-06).
 *
 * <p>Lo escribe el hilo de la simulación y lo leen la interfaz y el
 * seguimiento hasta Bronze, por eso sus métodos están sincronizados. Los
 * contadores empiezan en cero en cada arranque (diseño, sección 9.5).</p>
 */
public final class ActivityBoard {

    /** Cuántas transacciones recientes se conservan para la lista y el seguimiento. */
    public static final int HISTORY_SIZE = 2_000;

    /** Ventana sobre la que se calcula el ritmo de transacciones. */
    private static final long RATE_WINDOW_NANOS = 10_000_000_000L;

    /**
     * Foto de los contadores en un instante.
     *
     * @param inserts INSERT confirmados, incluidas las reinserciones
     * @param updates UPDATE confirmados
     * @param deletes DELETE confirmados
     * @param errors  transacciones revertidas
     * @param manual  operaciones lanzadas a mano
     */
    public record Counters(long inserts, long updates, long deletes, long errors, long manual) {
    }

    private final Deque<TransactionRecord> recent = new ArrayDeque<>();
    private final Deque<Long> commitTimesNanos = new ArrayDeque<>();
    private long sequence;
    private long inserts;
    private long updates;
    private long deletes;
    private long errors;
    private long manual;

    /** @return el número de orden para la siguiente transacción, empezando en 1 */
    public synchronized long nextSequence() {
        return ++sequence;
    }

    /**
     * Añade una transacción terminada y actualiza los contadores.
     *
     * @param record transacción confirmada o revertida
     */
    public synchronized void add(TransactionRecord record) {
        recent.addFirst(record);
        if (recent.size() > HISTORY_SIZE) {
            recent.removeLast();
        }
        if (record.manual()) {
            manual++;
        }
        if (record.failed()) {
            errors++;
            return;
        }
        count(record.type());
        commitTimesNanos.addLast(System.nanoTime());
    }

    private void count(OperationType type) {
        switch (type) {
            case INSERT -> inserts++;
            case UPDATE -> updates++;
            case DELETE -> deletes++;
        }
    }

    /** @return las últimas transacciones, de la más reciente a la más antigua */
    public synchronized List<TransactionRecord> recent() {
        return new ArrayList<>(recent);
    }

    /** @return las transacciones recientes cuyo cambio aún no se ha visto en Bronze */
    public synchronized List<TransactionRecord> awaitingBronze() {
        List<TransactionRecord> waiting = new ArrayList<>();
        for (TransactionRecord record : recent) {
            if (record.bronze().status().isWaiting()) {
                waiting.add(record);
            }
        }
        return waiting;
    }

    /** @return los contadores en este instante */
    public synchronized Counters counters() {
        return new Counters(inserts, updates, deletes, errors, manual);
    }

    /** @return las transacciones confirmadas por segundo, en los últimos 10 segundos */
    public synchronized double transactionsPerSecond() {
        long oldestAllowed = System.nanoTime() - RATE_WINDOW_NANOS;
        while (!commitTimesNanos.isEmpty() && commitTimesNanos.peekFirst() < oldestAllowed) {
            commitTimesNanos.removeFirst();
        }
        return commitTimesNanos.size() / (RATE_WINDOW_NANOS / 1_000_000_000.0);
    }
}
