package com.elastiflix.simulator.db;

import com.elastiflix.simulator.dataset.CatalogTable;

import java.util.Collection;
import java.util.EnumMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/**
 * Recuerda qué claves de catálogos y entidades compartidas ya están en
 * PostgreSQL, para insertar cada una solo la primera vez que una película la
 * necesita (diseño, sección 9.5).
 *
 * <p>Al arrancar se llena con lo que ya hay en la base (RF-13). Después solo
 * la toca el hilo de la simulación.</p>
 */
public final class InsertedKeys {

    private final Map<CatalogTable, Set<Object>> keysByTable = new EnumMap<>(CatalogTable.class);

    /** Crea el registro vacío, con un conjunto por cada tabla compartida. */
    public InsertedKeys() {
        for (CatalogTable table : CatalogTable.sharedTables()) {
            keysByTable.put(table, new HashSet<>());
        }
    }

    /**
     * @param table catálogo o entidad compartida
     * @param key   clave de la fila
     * @return {@code true} si esa fila ya está en PostgreSQL
     */
    public boolean contains(CatalogTable table, Object key) {
        return keysByTable.get(table).contains(key);
    }

    /**
     * Anota una clave como insertada.
     *
     * @param table catálogo o entidad compartida
     * @param key   clave de la fila
     */
    public void add(CatalogTable table, Object key) {
        keysByTable.get(table).add(key);
    }

    /**
     * Anota varias claves como insertadas.
     *
     * @param table catálogo o entidad compartida
     * @param keys  claves de las filas
     */
    public void addAll(CatalogTable table, Collection<?> keys) {
        keysByTable.get(table).addAll(keys);
    }

    /** @return cuántas claves hay anotadas entre todas las tablas */
    public int totalCount() {
        return keysByTable.values().stream().mapToInt(Set::size).sum();
    }
}
