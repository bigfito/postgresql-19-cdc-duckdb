package com.elastiflix.simulator.db;

import com.elastiflix.simulator.dataset.CatalogTable;
import com.elastiflix.simulator.simulation.TransactionOutcome;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.stream.Collectors;

/**
 * El DELETE de una película (RF-03; diseño, secciones 9.5 y 13).
 *
 * <p>Se borra solo la fila de {@code movie}; sus relaciones caen por
 * {@code ON DELETE CASCADE} y las entidades compartidas se quedan. Como JDBC
 * solo informa de la fila de {@code movie}, las filas de cada relación se
 * cuentan antes de borrar, dentro de la misma transacción.</p>
 */
public final class MovieDeleter {

    private static final String DELETE_MOVIE = "DELETE FROM catalog.movie WHERE movie_id = ?";

    private static final List<CatalogTable> RELATIONS = CatalogTable.relationTables();

    /** Una sola consulta con un conteo por tabla de relación. */
    private static final String COUNT_RELATIONS = "SELECT " + RELATIONS.stream()
            .map(relation -> "(SELECT count(*) FROM " + relation.qualifiedName() + " WHERE movie_id = ?)")
            .collect(Collectors.joining(", "));

    private final TransactionRunner transactions;

    /**
     * @param transactions ejecutor de transacciones
     */
    public MovieDeleter(TransactionRunner transactions) {
        this.transactions = transactions;
    }

    /**
     * Borra la película y, por cascada, sus relaciones.
     *
     * @param movieId película viva
     * @return lo que dejó la transacción, con las filas borradas en cada tabla
     * @throws SQLException si PostgreSQL rechaza el borrado
     */
    public TransactionOutcome delete(long movieId) throws SQLException {
        return transactions.run((connection, rows) -> {
            int[] relationRows = countRelationRows(connection, movieId);
            try (PreparedStatement statement = connection.prepareStatement(DELETE_MOVIE)) {
                statement.setLong(1, movieId);
                if (statement.executeUpdate() == 0) {
                    throw MovieUpdater.movieNotFound(movieId);
                }
            }
            rows.add(CatalogTable.MOVIE, 1);
            for (int index = 0; index < relationRows.length; index++) {
                rows.add(RELATIONS.get(index), relationRows[index]);
            }
            return "relaciones borradas por cascada";
        });
    }

    private int[] countRelationRows(Connection connection, long movieId) throws SQLException {
        int[] counts = new int[RELATIONS.size()];
        try (PreparedStatement statement = connection.prepareStatement(COUNT_RELATIONS)) {
            for (int index = 0; index < counts.length; index++) {
                statement.setLong(index + 1, movieId);
            }
            try (ResultSet result = statement.executeQuery()) {
                result.next();
                for (int index = 0; index < counts.length; index++) {
                    counts[index] = result.getInt(index + 1);
                }
            }
        }
        return counts;
    }
}
