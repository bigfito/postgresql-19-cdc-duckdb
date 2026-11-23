package com.elastiflix.simulator.db;

import com.elastiflix.simulator.dataset.CatalogTable;
import com.elastiflix.simulator.simulation.TransactionOutcome;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * El UPDATE de relaciones: añade o quita un género o una keyword de una
 * película viva (RF-03; diseño, sección 9.5).
 *
 * <p>Lo que se añade se toma de los géneros o las keywords que ya existen en
 * PostgreSQL; no se crea ninguno nuevo. La transacción no cambia ninguna
 * columna de {@code movie}, pero actualiza su {@code updated_at}: sin eso el
 * cambio no dejaría rastro en la película y el seguimiento hasta Bronze no lo
 * vería nunca.</p>
 */
public final class MovieRelationUpdater {

    private final TransactionRunner transactions;
    private final Random random;

    /**
     * @param transactions ejecutor de transacciones
     * @param random       generador de la simulación
     */
    public MovieRelationUpdater(TransactionRunner transactions, Random random) {
        this.transactions = transactions;
        this.random = random;
    }

    /**
     * Añade o quita un género o una keyword, y actualiza {@code updated_at} de
     * la película.
     *
     * <p>La semilla decide entre género y keyword, y entre añadir y quitar. Si
     * lo elegido no se puede hacer (no queda nada que añadir, o la película no
     * tiene nada que quitar), se hace lo contrario; y si tampoco, se prueba
     * con la otra relación.</p>
     *
     * @param movieId película viva
     * @return lo que dejó la transacción
     * @throws SQLException si PostgreSQL rechaza el cambio
     */
    public TransactionOutcome update(long movieId) throws SQLException {
        boolean genreFirst = random.nextBoolean();
        boolean preferAdd = random.nextBoolean();
        List<CatalogTable> relations = genreFirst
                ? List.of(CatalogTable.MOVIE_GENRE, CatalogTable.MOVIE_KEYWORD)
                : List.of(CatalogTable.MOVIE_KEYWORD, CatalogTable.MOVIE_GENRE);
        return transactions.run((connection, rows) -> {
            String detail = "sin géneros ni keywords que añadir o quitar";
            for (CatalogTable relation : relations) {
                String change = changeOne(connection, relation, movieId, preferAdd, rows);
                if (change != null) {
                    detail = change;
                    break;
                }
            }
            rows.add(CatalogTable.MOVIE, MovieUpdater.touchMovie(connection, movieId));
            return detail;
        });
    }

    /** @return la descripción del cambio, o {@code null} si en esta relación no se puede hacer ninguno */
    private String changeOne(Connection connection, CatalogTable relation, long movieId, boolean preferAdd,
                             RowCounter rows) throws SQLException {
        List<Long> current = currentIds(connection, relation, movieId);
        List<Long> candidates = candidateIds(connection, relation, movieId);
        boolean canAdd = !candidates.isEmpty();
        boolean canRemove = !current.isEmpty();
        if (!canAdd && !canRemove) {
            return null;
        }
        boolean add = canAdd && (preferAdd || !canRemove);
        if (add) {
            return addOne(connection, relation, movieId, pick(candidates), rows);
        }
        return removeOne(connection, relation, movieId, pick(current), rows);
    }

    private long pick(List<Long> ids) {
        return ids.get(random.nextInt(ids.size()));
    }

    private String addOne(Connection connection, CatalogTable relation, long movieId, long id, RowCounter rows)
            throws SQLException {
        int position = nextPosition(connection, relation, movieId);
        String sql = "INSERT INTO " + relation.qualifiedName() + " (movie_id, " + idColumn(relation)
                + ", source_position) VALUES (?, ?, ?)";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setLong(1, movieId);
            statement.setLong(2, id);
            statement.setInt(3, position);
            rows.add(relation, statement.executeUpdate());
        }
        return "+ " + describe(connection, relation, id) + " en la posición " + position;
    }

    private String removeOne(Connection connection, CatalogTable relation, long movieId, long id, RowCounter rows)
            throws SQLException {
        String sql = "DELETE FROM " + relation.qualifiedName() + " WHERE movie_id = ? AND " + idColumn(relation)
                + " = ?";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setLong(1, movieId);
            statement.setLong(2, id);
            rows.add(relation, statement.executeUpdate());
        }
        return "− " + describe(connection, relation, id);
    }

    /** Géneros o keywords que la película tiene ahora, en su orden. */
    private List<Long> currentIds(Connection connection, CatalogTable relation, long movieId) throws SQLException {
        String sql = "SELECT " + idColumn(relation) + " FROM " + relation.qualifiedName()
                + " WHERE movie_id = ? ORDER BY source_position";
        return readIds(connection, sql, movieId);
    }

    /** Géneros o keywords que existen en PostgreSQL y la película no tiene. Ordenados, para que la elección sea reproducible. */
    private List<Long> candidateIds(Connection connection, CatalogTable relation, long movieId) throws SQLException {
        String id = idColumn(relation);
        String sql = "SELECT s." + id + " FROM " + relation.referencedTable().qualifiedName() + " s"
                + " WHERE NOT EXISTS (SELECT 1 FROM " + relation.qualifiedName() + " r"
                + " WHERE r.movie_id = ? AND r." + id + " = s." + id + ") ORDER BY s." + id;
        return readIds(connection, sql, movieId);
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

    /** La posición siguiente a la última: no reutiliza huecos, así que nunca choca con la restricción de unicidad. */
    private int nextPosition(Connection connection, CatalogTable relation, long movieId) throws SQLException {
        String sql = "SELECT COALESCE(MAX(source_position), 0) + 1 FROM " + relation.qualifiedName()
                + " WHERE movie_id = ?";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setLong(1, movieId);
            try (ResultSet result = statement.executeQuery()) {
                result.next();
                return result.getInt(1);
            }
        }
    }

    /** Por ejemplo: {@code keyword 30 «rogue tart»}. */
    private String describe(Connection connection, CatalogTable relation, long id) throws SQLException {
        CatalogTable shared = relation.referencedTable();
        String sql = "SELECT name FROM " + shared.qualifiedName() + " WHERE " + idColumn(relation) + " = ?";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setLong(1, id);
            try (ResultSet result = statement.executeQuery()) {
                String name = result.next() ? result.getString(1) : null;
                return shared.tableName() + " " + id + " " + MovieUpdater.quoted(name);
            }
        }
    }

    /** {@code genre_id} o {@code keyword_id}: se llama igual en la relación y en su entidad. */
    private static String idColumn(CatalogTable relation) {
        return relation.columns().get(CatalogTable.RELATION_REFERENCE_INDEX).name();
    }
}
