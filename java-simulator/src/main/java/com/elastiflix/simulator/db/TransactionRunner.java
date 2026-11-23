package com.elastiflix.simulator.db;

import com.elastiflix.simulator.simulation.TransactionOutcome;

import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;

/**
 * Ejecuta un trabajo dentro de una transacción de PostgreSQL: lo confirma si
 * termina bien y lo revierte entero si falla (diseño, sección 9.7).
 */
public final class TransactionRunner {

    /**
     * Instante de inicio de la transacción, truncado a milisegundos. Tiene que
     * ser {@code floor} y no un redondeo: un umbral redondeado hacia arriba
     * deja transacciones pendientes para siempre (diseño, sección 9.3).
     */
    private static final String REFERENCE_INSTANT_SQL =
            "SELECT floor(extract(epoch FROM now()) * 1000)::bigint";

    /** El trabajo de una transacción. */
    @FunctionalInterface
    public interface Work {

        /**
         * @param connection conexión con la transacción ya abierta
         * @param rows       donde se anotan las filas afectadas
         * @return una descripción breve del cambio; puede ser una cadena vacía
         * @throws SQLException si PostgreSQL rechaza alguna sentencia
         */
        String execute(Connection connection, RowCounter rows) throws SQLException;
    }

    private final PostgresSession session;

    /**
     * @param session conexión con PostgreSQL
     */
    public TransactionRunner(PostgresSession session) {
        this.session = session;
    }

    /**
     * Ejecuta el trabajo en una transacción.
     *
     * @param work sentencias de la transacción
     * @return lo que dejó la transacción ya confirmada
     * @throws SQLException     si PostgreSQL rechaza una sentencia o el COMMIT;
     *                          la transacción queda revertida
     * @throws RuntimeException si el trabajo detecta un dato inconsistente; la
     *                          transacción queda revertida
     */
    public TransactionOutcome run(Work work) throws SQLException {
        long startedAt = System.nanoTime();
        try {
            Connection connection = session.connection();
            long referenceMillis = readReferenceInstant(connection);
            RowCounter rows = new RowCounter();
            String detail = work.execute(connection, rows);
            connection.commit();
            long durationMillis = (System.nanoTime() - startedAt) / 1_000_000;
            return new TransactionOutcome(referenceMillis, rows.rowsByTable(), durationMillis, detail);
        } catch (SQLException | RuntimeException e) {
            session.rollbackQuietly();
            throw e;
        }
    }

    /** Es la primera sentencia de la transacción, así que fija su instante de inicio. */
    private long readReferenceInstant(Connection connection) throws SQLException {
        try (Statement statement = connection.createStatement();
             ResultSet result = statement.executeQuery(REFERENCE_INSTANT_SQL)) {
            result.next();
            return result.getLong(1);
        }
    }
}
