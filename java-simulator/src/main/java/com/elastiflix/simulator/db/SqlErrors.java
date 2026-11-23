package com.elastiflix.simulator.db;

import java.sql.SQLException;

/**
 * Clasifica los errores que devuelve PostgreSQL.
 */
public final class SqlErrors {

    /** Clase 23 de SQLSTATE: violación de una restricción de integridad. */
    private static final String INTEGRITY_VIOLATION_CLASS = "23";

    private SqlErrors() {
    }

    /**
     * Dice si el error es un dato inconsistente (RF-12): una clave duplicada,
     * una referencia inexistente o cualquier otra restricción incumplida.
     *
     * @param error error devuelto por JDBC
     * @return {@code true} si la base rechazó el dato; {@code false} si el
     *         fallo es de otra clase, como una conexión perdida
     */
    public static boolean isIntegrityViolation(SQLException error) {
        // Un lote fallido encadena el error original en getNextException().
        for (SQLException current = error; current != null; current = current.getNextException()) {
            String state = current.getSQLState();
            if (state != null && state.startsWith(INTEGRITY_VIOLATION_CLASS)) {
                return true;
            }
        }
        return false;
    }
}
