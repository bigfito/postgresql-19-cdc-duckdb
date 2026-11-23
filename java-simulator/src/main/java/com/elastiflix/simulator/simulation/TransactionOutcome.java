package com.elastiflix.simulator.simulation;

import java.util.Map;

/**
 * Lo que deja una transacción que terminó con COMMIT.
 *
 * @param referenceMillis instante de referencia para el seguimiento hasta
 *                        Bronze: el inicio de la transacción según PostgreSQL,
 *                        truncado a milisegundos (diseño, sección 9.3)
 * @param rowsByTable     filas afectadas en cada tabla, en el orden en que se tocaron
 * @param durationMillis  cuánto tardó la transacción completa
 * @param detail          descripción breve del cambio, para la zona de detalle y el log
 */
public record TransactionOutcome(
        long referenceMillis,
        Map<String, Integer> rowsByTable,
        long durationMillis,
        String detail) {

    /** @return la suma de las filas afectadas en todas las tablas */
    public int totalRows() {
        return rowsByTable.values().stream().mapToInt(Integer::intValue).sum();
    }
}
