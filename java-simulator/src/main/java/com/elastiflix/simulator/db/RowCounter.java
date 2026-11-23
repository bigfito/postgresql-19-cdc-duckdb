package com.elastiflix.simulator.db;

import com.elastiflix.simulator.dataset.CatalogTable;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Cuenta las filas que una transacción afecta en cada tabla, en el orden en
 * que las toca. De aquí sale el desglose de la zona de detalle.
 */
public final class RowCounter {

    private final Map<String, Integer> rowsByTable = new LinkedHashMap<>();

    /**
     * Suma filas a una tabla. Un cero no se anota.
     *
     * @param table tabla afectada
     * @param rows  cuántas filas
     */
    public void add(CatalogTable table, int rows) {
        if (rows > 0) {
            rowsByTable.merge(table.tableName(), rows, Integer::sum);
        }
    }

    /** @return las filas por tabla, en orden; no se puede modificar */
    public Map<String, Integer> rowsByTable() {
        return Collections.unmodifiableMap(rowsByTable);
    }
}
