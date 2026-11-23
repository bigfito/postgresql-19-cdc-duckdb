package com.elastiflix.simulator.db;

import com.elastiflix.simulator.dataset.CatalogTable;
import com.elastiflix.simulator.dataset.ColumnType;
import com.elastiflix.simulator.simulation.CatalogLinks;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Consultas de solo lectura sobre PostgreSQL: lo que ya hay al arrancar
 * (RF-13) y lo que una película tiene hoy.
 *
 * <p>Cada lectura termina con un ROLLBACK para no dejar una transacción
 * abierta entre operación y operación.</p>
 */
public final class DatabaseStateReader {

    private static final String SELECT_COLLECTION =
            "SELECT collection_id FROM catalog.movie_collection WHERE movie_id = ?";

    private static final String SELECT_KEYWORDS =
            "SELECT keyword_id FROM catalog.movie_keyword WHERE movie_id = ? ORDER BY source_position";

    private final PostgresSession session;

    /**
     * @param session conexión con PostgreSQL
     */
    public DatabaseStateReader(PostgresSession session) {
        this.session = session;
    }

    /**
     * @return los {@code movie_id} que ya están en {@code catalog.movie}
     * @throws SQLException si la consulta falla
     */
    public Set<Long> readMovieIds() throws SQLException {
        Set<Long> movieIds = new HashSet<>();
        for (Object key : readKeys(CatalogTable.MOVIE)) {
            movieIds.add((Long) key);
        }
        return movieIds;
    }

    /**
     * Lee las claves de las once tablas de catálogos y entidades compartidas.
     *
     * @return las claves que ya están en PostgreSQL, que se dan por insertadas
     * @throws SQLException si alguna consulta falla
     */
    public InsertedKeys readInsertedKeys() throws SQLException {
        InsertedKeys insertedKeys = new InsertedKeys();
        for (CatalogTable table : CatalogTable.sharedTables()) {
            insertedKeys.addAll(table, readKeys(table));
        }
        return insertedKeys;
    }

    private List<Object> readKeys(CatalogTable table) throws SQLException {
        String keyColumn = table.keyColumn().name();
        boolean numericKey = table.keyColumn().type() == ColumnType.BIGINT;
        String sql = "SELECT " + keyColumn + " FROM " + table.qualifiedName();
        Connection connection = session.connection();
        List<Object> keys = new ArrayList<>();
        try (Statement statement = connection.createStatement();
             ResultSet result = statement.executeQuery(sql)) {
            while (result.next()) {
                keys.add(numericKey ? (Object) result.getLong(1) : result.getString(1));
            }
        } finally {
            session.rollbackQuietly();
        }
        return keys;
    }

    /**
     * Lee la colección y las keywords que una película tiene ahora. De esto
     * depende que admita o no un UPDATE de catálogo (diseño, sección 9.5).
     *
     * @param movieId película viva
     * @return su colección, si tiene, y sus keywords en orden
     * @throws SQLException si la consulta falla
     */
    public CatalogLinks readCatalogLinks(long movieId) throws SQLException {
        Connection connection = session.connection();
        try {
            List<Long> collections = readIds(connection, SELECT_COLLECTION, movieId);
            List<Long> keywords = readIds(connection, SELECT_KEYWORDS, movieId);
            return new CatalogLinks(collections.isEmpty() ? null : collections.get(0), keywords);
        } finally {
            session.rollbackQuietly();
        }
    }

    private List<Long> readIds(Connection connection, String sql, long movieId) throws SQLException {
        List<Long> ids = new ArrayList<>();
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setLong(1, movieId);
            try (ResultSet result = statement.executeQuery()) {
                while (result.next()) {
                    ids.add(result.getLong(1));
                }
            }
        }
        return ids;
    }
}
