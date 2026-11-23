package com.elastiflix.simulator.simulation;

/**
 * La siguiente operación que el simulador va a ejecutar.
 *
 * @param type        INSERT, UPDATE o DELETE
 * @param movieId     película sobre la que se ejecuta
 * @param reinsertion {@code true} si es el INSERT de una película borrada
 */
public record PlannedOperation(OperationType type, long movieId, boolean reinsertion) {

    /** @return el alta de una película pendiente */
    public static PlannedOperation insert(long movieId) {
        return new PlannedOperation(OperationType.INSERT, movieId, false);
    }

    /** @return la reinserción de una película borrada */
    public static PlannedOperation reinsert(long movieId) {
        return new PlannedOperation(OperationType.INSERT, movieId, true);
    }

    /** @return un UPDATE sobre una película viva */
    public static PlannedOperation update(long movieId) {
        return new PlannedOperation(OperationType.UPDATE, movieId, false);
    }

    /** @return el DELETE de una película viva */
    public static PlannedOperation delete(long movieId) {
        return new PlannedOperation(OperationType.DELETE, movieId, false);
    }
}
