package com.elastiflix.simulator.db;

import com.elastiflix.simulator.dataset.CatalogTable;
import com.elastiflix.simulator.dataset.Dataset;
import com.elastiflix.simulator.error.ErrorCode;
import com.elastiflix.simulator.error.SimulatorException;
import com.elastiflix.simulator.simulation.CatalogTarget;
import com.elastiflix.simulator.simulation.DescriptiveChange;
import com.elastiflix.simulator.simulation.DescriptiveChangeGenerator;
import com.elastiflix.simulator.simulation.DescriptiveField;
import com.elastiflix.simulator.simulation.DescriptiveValues;
import com.elastiflix.simulator.simulation.MeasureChangeGenerator;
import com.elastiflix.simulator.simulation.MeasureValues;
import com.elastiflix.simulator.simulation.RevisionName;
import com.elastiflix.simulator.simulation.TransactionOutcome;

import java.math.BigDecimal;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.Random;

/**
 * Los UPDATE descriptivo, de medidas y de catálogo sobre una película viva
 * (RF-03; diseño, sección 9.5). El de relaciones está en
 * {@link MovieRelationUpdater}.
 *
 * <p>Todo UPDATE actualiza {@code updated_at}; el de catálogo, además del de
 * la colección o la keyword, el de la película: así el cambio deja rastro en
 * {@code movie} y el seguimiento hasta Bronze lo ve.</p>
 */
public final class MovieUpdater {

    private static final String SELECT_DESCRIPTIVE =
            "SELECT title, tagline, overview, homepage FROM catalog.movie WHERE movie_id = ?";

    private static final String SELECT_MEASURES =
            "SELECT popularity, vote_count, vote_average, user_score, budget_usd, revenue_usd"
                    + " FROM catalog.movie WHERE movie_id = ?";

    private static final String UPDATE_MEASURES =
            "UPDATE catalog.movie SET popularity = ?, vote_count = ?, vote_average = ?, user_score = ?,"
                    + " budget_usd = ?, revenue_usd = ?, updated_at = now() WHERE movie_id = ?";

    /** Usado también por el UPDATE de relaciones. */
    static final String TOUCH_MOVIE = "UPDATE catalog.movie SET updated_at = now() WHERE movie_id = ?";

    private static final int MAX_TEXT_IN_DETAIL = 60;

    private final Dataset dataset;
    private final TransactionRunner transactions;
    private final Random random;
    private final DescriptiveChangeGenerator descriptiveChanges = new DescriptiveChangeGenerator();
    private final MeasureChangeGenerator measureChanges = new MeasureChangeGenerator();

    /**
     * @param dataset      dataset en memoria, con los valores originales
     * @param transactions ejecutor de transacciones
     * @param random       generador de la simulación
     */
    public MovieUpdater(Dataset dataset, TransactionRunner transactions, Random random) {
        this.dataset = dataset;
        this.transactions = transactions;
        this.random = random;
    }

    /**
     * Cambia uno de los textos de la película: título, lema, sinopsis o página web.
     *
     * @param movieId película viva
     * @return lo que dejó la transacción
     * @throws SQLException si PostgreSQL rechaza el cambio
     */
    public TransactionOutcome updateDescriptive(long movieId) throws SQLException {
        return transactions.run((connection, rows) -> {
            DescriptiveValues current = readDescriptive(connection, movieId);
            DescriptiveChange change = descriptiveChanges.next(movieId, originalDescriptive(movieId), current, random);
            String sql = "UPDATE catalog.movie SET " + change.field().columnName()
                    + " = ?, updated_at = now() WHERE movie_id = ?";
            try (PreparedStatement statement = connection.prepareStatement(sql)) {
                statement.setString(1, change.newValue());
                statement.setLong(2, movieId);
                rows.add(CatalogTable.MOVIE, statement.executeUpdate());
            }
            return describeDescriptive(change, current.get(change.field()));
        });
    }

    /** La sinopsis cambia por el final, así que de ella se muestra el final. */
    private String describeDescriptive(DescriptiveChange change, String currentValue) {
        boolean showEnd = change.field() == DescriptiveField.OVERVIEW;
        String before = showEnd ? quotedEnd(currentValue) : quoted(currentValue);
        String after = showEnd ? quotedEnd(change.newValue()) : quoted(change.newValue());
        return change.field().columnName() + ": " + before + " → " + after;
    }

    /**
     * Cambia las seis medidas de la película.
     *
     * @param movieId película viva
     * @return lo que dejó la transacción
     * @throws SQLException si PostgreSQL rechaza el cambio
     */
    public TransactionOutcome updateMeasures(long movieId) throws SQLException {
        return transactions.run((connection, rows) -> {
            MeasureValues current = readMeasures(connection, movieId);
            MeasureValues next = measureChanges.next(current, random);
            try (PreparedStatement statement = connection.prepareStatement(UPDATE_MEASURES)) {
                statement.setBigDecimal(1, next.popularity());
                statement.setObject(2, next.voteCount());
                statement.setBigDecimal(3, next.voteAverage());
                statement.setBigDecimal(4, next.userScore());
                statement.setBigDecimal(5, next.budgetUsd());
                statement.setBigDecimal(6, next.revenueUsd());
                statement.setLong(7, movieId);
                rows.add(CatalogTable.MOVIE, statement.executeUpdate());
            }
            return describeMeasures(current, next);
        });
    }

    /**
     * Renombra la colección de la película o una de sus keywords con el sufijo
     * {@code  (rev N)}. El número sale del nombre que hay en PostgreSQL.
     *
     * @param movieId película viva a la que pertenece lo que se renombra
     * @param target  colección o keyword elegida
     * @return lo que dejó la transacción
     * @throws SQLException si PostgreSQL rechaza el cambio
     */
    public TransactionOutcome updateCatalog(long movieId, CatalogTarget target) throws SQLException {
        CatalogTable table = target.table();
        String keyColumn = table.keyColumn().name();
        return transactions.run((connection, rows) -> {
            String currentName = readName(connection, table, keyColumn, target.id());
            String newName = RevisionName.next(currentName);
            String sql = "UPDATE " + table.qualifiedName() + " SET name = ?, updated_at = now() WHERE "
                    + keyColumn + " = ?";
            try (PreparedStatement statement = connection.prepareStatement(sql)) {
                statement.setString(1, newName);
                statement.setLong(2, target.id());
                rows.add(table, statement.executeUpdate());
            }
            rows.add(CatalogTable.MOVIE, touchMovie(connection, movieId));
            return table.tableName() + " " + target.id() + ": " + quoted(currentName) + " → " + quoted(newName);
        });
    }

    /**
     * Actualiza solo {@code updated_at} de la película.
     *
     * @return 1, la fila actualizada
     * @throws SimulatorException si la película no está en {@code catalog.movie}
     */
    static int touchMovie(Connection connection, long movieId) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(TOUCH_MOVIE)) {
            statement.setLong(1, movieId);
            if (statement.executeUpdate() == 0) {
                throw movieNotFound(movieId);
            }
            return 1;
        }
    }

    static SimulatorException movieNotFound(long movieId) {
        return new SimulatorException(ErrorCode.MOVIE_MISSING,
                "la película " + movieId + " no está en catalog.movie");
    }

    private DescriptiveValues originalDescriptive(long movieId) {
        return new DescriptiveValues(
                (String) dataset.movieValue(movieId, "title"),
                (String) dataset.movieValue(movieId, "tagline"),
                (String) dataset.movieValue(movieId, "overview"),
                (String) dataset.movieValue(movieId, "homepage"));
    }

    private DescriptiveValues readDescriptive(Connection connection, long movieId) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(SELECT_DESCRIPTIVE)) {
            statement.setLong(1, movieId);
            try (ResultSet result = statement.executeQuery()) {
                if (!result.next()) {
                    throw movieNotFound(movieId);
                }
                return new DescriptiveValues(result.getString(1), result.getString(2),
                        result.getString(3), result.getString(4));
            }
        }
    }

    private MeasureValues readMeasures(Connection connection, long movieId) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(SELECT_MEASURES)) {
            statement.setLong(1, movieId);
            try (ResultSet result = statement.executeQuery()) {
                if (!result.next()) {
                    throw movieNotFound(movieId);
                }
                return new MeasureValues(result.getBigDecimal(1), result.getObject(2, Integer.class),
                        result.getBigDecimal(3), result.getBigDecimal(4),
                        result.getBigDecimal(5), result.getBigDecimal(6));
            }
        }
    }

    private String readName(Connection connection, CatalogTable table, String keyColumn, long id)
            throws SQLException {
        String sql = "SELECT name FROM " + table.qualifiedName() + " WHERE " + keyColumn + " = ?";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setLong(1, id);
            try (ResultSet result = statement.executeQuery()) {
                if (!result.next()) {
                    throw new SimulatorException(ErrorCode.DATA_INCONSISTENT,
                            "no existe " + table.qualifiedName() + " con clave " + id);
                }
                return result.getString(1);
            }
        }
    }

    private String describeMeasures(MeasureValues current, MeasureValues next) {
        return "popularity " + current.popularity() + " → " + next.popularity()
                + " · vote_count " + shown(current.voteCount()) + " → " + next.voteCount()
                + " · vote_average " + shown(current.voteAverage()) + " → " + next.voteAverage()
                + " · user_score " + shown(current.userScore()) + " → " + next.userScore()
                + " · budget_usd " + shown(current.budgetUsd()) + " → " + shown(next.budgetUsd())
                + " · revenue_usd " + shown(current.revenueUsd()) + " → " + shown(next.revenueUsd());
    }

    private static String shown(Object value) {
        if (value == null) {
            return "NULL";
        }
        return value instanceof BigDecimal decimal ? decimal.toPlainString() : value.toString();
    }

    /** Entre comillas angulares y recortado, para que quepa en una línea. */
    static String quoted(String text) {
        if (text == null) {
            return "NULL";
        }
        String oneLine = text.replace('\n', ' ');
        if (oneLine.length() > MAX_TEXT_IN_DETAIL) {
            oneLine = oneLine.substring(0, MAX_TEXT_IN_DETAIL - 1) + "…";
        }
        return "«" + oneLine + "»";
    }

    /** Como {@link #quoted(String)}, pero conserva el final del texto en lugar del principio. */
    static String quotedEnd(String text) {
        if (text == null) {
            return "NULL";
        }
        String oneLine = text.replace('\n', ' ');
        if (oneLine.length() > MAX_TEXT_IN_DETAIL) {
            oneLine = "…" + oneLine.substring(oneLine.length() - MAX_TEXT_IN_DETAIL + 1);
        }
        return "«" + oneLine + "»";
    }
}
