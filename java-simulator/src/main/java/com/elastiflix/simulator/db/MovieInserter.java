package com.elastiflix.simulator.db;

import com.elastiflix.simulator.dataset.CatalogTable;
import com.elastiflix.simulator.dataset.Dataset;
import com.elastiflix.simulator.error.ErrorCode;
import com.elastiflix.simulator.error.SimulatorException;
import com.elastiflix.simulator.simulation.TransactionOutcome;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Da de alta una película en una sola transacción (RF-02; diseño, sección 9.7):
 * primero los catálogos y las entidades que aún no existen, después
 * {@code movie} y por último sus relaciones.
 *
 * <p>Sirve igual para la primera alta y para reinsertar una película borrada:
 * en los dos casos los datos salen de los archivos.</p>
 */
public final class MovieInserter {

    private static final String[] MOVIE_REFERENCE_COLUMNS = {"status_code", "rating_code", "original_language_code"};
    private static final CatalogTable[] MOVIE_REFERENCE_TABLES = {
        CatalogTable.MOVIE_STATUS, CatalogTable.CONTENT_RATING, CatalogTable.ORIGINAL_LANGUAGE};

    private final Dataset dataset;
    private final TransactionRunner transactions;
    private final InsertedKeys insertedKeys;

    /**
     * @param dataset      dataset en memoria
     * @param transactions ejecutor de transacciones
     * @param insertedKeys claves de catálogos y entidades que ya están en PostgreSQL
     */
    public MovieInserter(Dataset dataset, TransactionRunner transactions, InsertedKeys insertedKeys) {
        this.dataset = dataset;
        this.transactions = transactions;
        this.insertedKeys = insertedKeys;
    }

    /**
     * Inserta la película con todo lo que cuelga de ella.
     *
     * @param movieId película del dataset
     * @return lo que dejó la transacción
     * @throws SQLException       si PostgreSQL rechaza alguna fila, por ejemplo
     *                            por una clave duplicada o una referencia
     *                            inexistente; no queda nada insertado
     * @throws SimulatorException si el dataset no contiene esa película
     */
    public TransactionOutcome insert(long movieId) throws SQLException {
        Object[] movie = dataset.movie(movieId);
        if (movie == null) {
            throw new SimulatorException(ErrorCode.DATA_INCONSISTENT, "el dataset no contiene la película " + movieId);
        }
        Map<CatalogTable, Set<Object>> missingKeys = missingSharedKeys(movieId, movie);
        TransactionOutcome outcome = transactions.run((connection, rows) -> {
            insertSharedRows(connection, missingKeys, rows);
            insertRows(connection, CatalogTable.MOVIE, Collections.singletonList(movie), rows);
            insertRelations(connection, movieId, rows);
            return "";
        });
        // Solo tras el COMMIT: si la transacción se revierte, esas filas no existen.
        missingKeys.forEach(insertedKeys::addAll);
        return outcome;
    }

    /** Reúne, tabla por tabla, las claves que la película necesita y aún no están en PostgreSQL. */
    private Map<CatalogTable, Set<Object>> missingSharedKeys(long movieId, Object[] movie) {
        Map<CatalogTable, Set<Object>> missing = new EnumMap<>(CatalogTable.class);
        for (int index = 0; index < MOVIE_REFERENCE_COLUMNS.length; index++) {
            Object key = movie[CatalogTable.MOVIE.columnIndex(MOVIE_REFERENCE_COLUMNS[index])];
            addIfMissing(missing, MOVIE_REFERENCE_TABLES[index], key);
        }
        for (CatalogTable relation : CatalogTable.relationTables()) {
            for (Object[] row : dataset.relationRows(relation, movieId)) {
                addIfMissing(missing, relation.referencedTable(), row[CatalogTable.RELATION_REFERENCE_INDEX]);
            }
        }
        return missing;
    }

    private void addIfMissing(Map<CatalogTable, Set<Object>> missing, CatalogTable table, Object key) {
        if (key != null && !insertedKeys.contains(table, key)) {
            missing.computeIfAbsent(table, unused -> new LinkedHashSet<>()).add(key);
        }
    }

    /** El mapa es un EnumMap, así que las tablas salen en el orden de inserción del diseño. */
    private void insertSharedRows(Connection connection, Map<CatalogTable, Set<Object>> missingKeys, RowCounter rows)
            throws SQLException {
        for (Map.Entry<CatalogTable, Set<Object>> entry : missingKeys.entrySet()) {
            insertRows(connection, entry.getKey(), sharedRowsOf(entry.getKey(), entry.getValue()), rows);
        }
    }

    /**
     * Si el dataset no trae la fila de una clave, no se inserta nada: la
     * referencia fallará en PostgreSQL y la transacción se revertirá (RF-12).
     */
    private List<Object[]> sharedRowsOf(CatalogTable table, Set<Object> keys) {
        List<Object[]> rows = new ArrayList<>(keys.size());
        for (Object key : keys) {
            Object[] row = dataset.sharedRow(table, key);
            if (row != null) {
                rows.add(row);
            }
        }
        return rows;
    }

    private void insertRelations(Connection connection, long movieId, RowCounter rows) throws SQLException {
        for (CatalogTable relation : CatalogTable.relationTables()) {
            insertRows(connection, relation, dataset.relationRows(relation, movieId), rows);
        }
    }

    /** Inserta las filas de una tabla en un solo lote. */
    private void insertRows(Connection connection, CatalogTable table, List<Object[]> tableRows, RowCounter rows)
            throws SQLException {
        if (tableRows.isEmpty()) {
            return;
        }
        try (PreparedStatement statement = connection.prepareStatement(table.insertSql())) {
            for (Object[] row : tableRows) {
                for (int index = 0; index < row.length; index++) {
                    statement.setObject(index + 1, row[index]);
                }
                statement.addBatch();
            }
            statement.executeBatch();
        }
        rows.add(table, tableRows.size());
    }
}
