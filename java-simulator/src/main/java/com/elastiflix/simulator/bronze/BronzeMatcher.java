package com.elastiflix.simulator.bronze;

import com.elastiflix.simulator.simulation.OperationType;

/**
 * La regla con la que se decide si el cambio de una transacción ya llegó a
 * {@code bronze.movie} (RF-09; diseño, sección 9.3).
 */
public final class BronzeMatcher {

    /** Valor de {@code cdc_op_type} en la fila de una película borrada (diseño, sección 17). */
    public static final String TOMBSTONE = "-D";

    private BronzeMatcher() {
    }

    /**
     * Bronze guarda una fila por película, con el último cambio conocido. El
     * cambio de una transacción ha llegado cuando esa fila es igual o posterior
     * a su instante de referencia.
     *
     * <p>Para un DELETE se pide además que la fila sea el tombstone, o que sea
     * estrictamente posterior: una fila posterior que ya no es tombstone
     * significa que la película se reinsertó después, así que el borrado
     * también pasó por Bronze.</p>
     *
     * @param type            operación de la transacción
     * @param referenceMillis inicio de la transacción en PostgreSQL, truncado a milisegundos
     * @param cdcOpType       {@code cdc_op_type} de la fila en Bronze
     * @param cdcOpTs         {@code cdc_op_ts} de la fila en Bronze, en milisegundos
     * @return {@code true} si el cambio ya está en Bronze
     */
    public static boolean hasArrived(OperationType type, long referenceMillis, String cdcOpType, long cdcOpTs) {
        if (cdcOpTs < referenceMillis) {
            return false;
        }
        if (type != OperationType.DELETE) {
            return true;
        }
        return TOMBSTONE.equals(cdcOpType) || cdcOpTs > referenceMillis;
    }
}
