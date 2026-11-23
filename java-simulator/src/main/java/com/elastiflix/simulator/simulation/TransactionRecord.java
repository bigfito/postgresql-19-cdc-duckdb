package com.elastiflix.simulator.simulation;

import java.time.Instant;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Una transacción ya terminada, tal como se muestra en la lista de la pantalla
 * y en el log (RF-06 y RF-11).
 *
 * <p>Sus datos no cambian, salvo el seguimiento hasta Bronze, que actualiza
 * otro hilo; por eso ese campo es {@code volatile} y guarda un valor
 * inmutable.</p>
 */
public final class TransactionRecord {

    /**
     * Estado del seguimiento junto con el tiempo que tardó en llegar.
     *
     * @param status      estado actual
     * @param delayMillis tiempo desde el COMMIT hasta que se vio en Bronze;
     *                    solo tiene sentido con {@link BronzeStatus#ARRIVED}
     */
    public record BronzeTracking(BronzeStatus status, long delayMillis) {
    }

    private final long sequence;
    private final Instant finishedAt;
    private final OperationType type;
    private final String kindLabel;
    private final long movieId;
    private final String title;
    private final boolean manual;
    private final boolean failed;
    private final Map<String, Integer> rowsByTable;
    private final int totalRows;
    private final long durationMillis;
    private final long referenceMillis;
    private final String detail;
    private volatile BronzeTracking bronze;

    private TransactionRecord(long sequence, PlannedOperation operation, String kindLabel, String title,
                              boolean manual, boolean failed, TransactionOutcome outcome, BronzeStatus status) {
        this.sequence = sequence;
        this.finishedAt = Instant.now();
        this.type = operation.type();
        this.kindLabel = kindLabel;
        this.movieId = operation.movieId();
        this.title = title;
        this.manual = manual;
        this.failed = failed;
        this.rowsByTable = outcome.rowsByTable();
        this.totalRows = outcome.totalRows();
        this.durationMillis = outcome.durationMillis();
        this.referenceMillis = outcome.referenceMillis();
        this.detail = outcome.detail();
        this.bronze = new BronzeTracking(status, 0);
    }

    /**
     * Crea el registro de una transacción confirmada.
     *
     * @param sequence    número de orden dentro de esta ejecución
     * @param operation   operación ejecutada
     * @param kindLabel   tipo de UPDATE, «reinserción» o cadena vacía
     * @param title       título de la película en el dataset
     * @param manual      si se lanzó a mano
     * @param outcome     lo que dejó la transacción
     * @param trackBronze si hay que seguirla hasta Bronze
     * @return el registro
     */
    public static TransactionRecord committed(long sequence, PlannedOperation operation, String kindLabel,
                                              String title, boolean manual, TransactionOutcome outcome,
                                              boolean trackBronze) {
        BronzeStatus status = trackBronze ? BronzeStatus.PENDING : BronzeStatus.NOT_TRACKED;
        return new TransactionRecord(sequence, operation, kindLabel, title, manual, false, outcome, status);
    }

    /**
     * Crea el registro de una transacción revertida.
     *
     * @param sequence  número de orden dentro de esta ejecución
     * @param operation operación que se intentó
     * @param kindLabel tipo de UPDATE, «reinserción» o cadena vacía
     * @param title     título de la película en el dataset
     * @param manual    si se lanzó a mano
     * @param reason    por qué falló
     * @return el registro
     */
    public static TransactionRecord failed(long sequence, PlannedOperation operation, String kindLabel,
                                           String title, boolean manual, String reason) {
        TransactionOutcome nothing = new TransactionOutcome(0, Map.of(), 0, reason);
        return new TransactionRecord(sequence, operation, kindLabel, title, manual, true, nothing,
                BronzeStatus.NOT_TRACKED);
    }

    /** @return número de orden de la transacción dentro de esta ejecución */
    public long sequence() {
        return sequence;
    }

    /** @return cuándo terminó la transacción, según el reloj del simulador */
    public Instant finishedAt() {
        return finishedAt;
    }

    /** @return INSERT, UPDATE o DELETE */
    public OperationType type() {
        return type;
    }

    /** @return la operación con su variante, por ejemplo {@code UPDATE (medidas)} */
    public String operationLabel() {
        return kindLabel.isEmpty() ? type.name() : type.name() + " (" + kindLabel + ")";
    }

    /** @return la película sobre la que se ejecutó */
    public long movieId() {
        return movieId;
    }

    /** @return el título de la película en el dataset */
    public String title() {
        return title;
    }

    /** @return {@code true} si se lanzó a mano desde la interfaz */
    public boolean manual() {
        return manual;
    }

    /** @return {@code true} si la transacción se revirtió */
    public boolean failed() {
        return failed;
    }

    /** @return filas afectadas en cada tabla, en el orden en que se tocaron */
    public Map<String, Integer> rowsByTable() {
        return rowsByTable;
    }

    /** @return total de filas afectadas */
    public int totalRows() {
        return totalRows;
    }

    /** @return duración de la transacción en milisegundos */
    public long durationMillis() {
        return durationMillis;
    }

    /** @return instante de referencia para el seguimiento, en milisegundos */
    public long referenceMillis() {
        return referenceMillis;
    }

    /** @return descripción del cambio, o el motivo del fallo; puede estar vacía */
    public String detail() {
        return detail;
    }

    /** @return estado actual del seguimiento hasta Bronze */
    public BronzeTracking bronze() {
        return bronze;
    }

    /**
     * Anota que el cambio ya se vio en Bronze.
     *
     * @param delayMillis tiempo transcurrido desde el COMMIT
     */
    public void markArrived(long delayMillis) {
        bronze = new BronzeTracking(BronzeStatus.ARRIVED, delayMillis);
    }

    /** Anota que el cambio lleva más tiempo del esperado sin aparecer en Bronze. */
    public void markLate() {
        bronze = new BronzeTracking(BronzeStatus.LATE, 0);
    }

    /** @return el desglose por tabla, por ejemplo {@code movie=1 movie_genre=3} */
    public String rowsBreakdown() {
        return rowsByTable.entrySet().stream()
                .map(entry -> entry.getKey() + "=" + entry.getValue())
                .collect(Collectors.joining(" "));
    }

    /**
     * @return la línea de log de esta transacción, con los mismos datos que su
     *         fila en la pantalla (diseño, sección 9.4)
     */
    public String logLine() {
        StringBuilder line = new StringBuilder(200);
        line.append("TX #").append(sequence).append(' ').append(operationLabel());
        line.append(" movie_id=").append(movieId);
        line.append(" título=\"").append(title).append('"');
        line.append(" origen=").append(manual ? "manual" : "auto");
        if (failed) {
            return line.append(" REVERTIDA: ").append(detail).toString();
        }
        line.append(" filas=").append(totalRows);
        line.append(" ms=").append(durationMillis);
        line.append(" tablas=[").append(rowsBreakdown()).append(']');
        if (!detail.isEmpty()) {
            line.append(" cambio=[").append(detail).append(']');
        }
        return line.toString();
    }
}
