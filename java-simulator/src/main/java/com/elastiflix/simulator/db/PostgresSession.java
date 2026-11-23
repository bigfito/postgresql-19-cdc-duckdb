package com.elastiflix.simulator.db;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * La conexión del simulador con PostgreSQL, con la cuenta {@code elastiflix_app}
 * (diseño, sección 45.3).
 *
 * <p>Hay una sola conexión y la usa solo el hilo de la simulación. Trabaja sin
 * autocommit: cada transacción termina con un COMMIT o un ROLLBACK explícito.
 * Si la conexión se pierde, se descarta y la siguiente operación abre otra.</p>
 */
public final class PostgresSession implements AutoCloseable {

    private static final Logger LOG = Logger.getLogger(PostgresSession.class.getName());

    private final String url;
    private final String user;
    private final String password;
    private Connection connection;
    private volatile boolean connected;

    /**
     * @param url      dirección JDBC de la base operacional
     * @param user     cuenta con la que se conecta
     * @param password contraseña de esa cuenta
     */
    public PostgresSession(String url, String user, String password) {
        this.url = url;
        this.user = user;
        this.password = password;
    }

    /**
     * @return la conexión abierta; la abre si aún no existe o si se descartó
     * @throws SQLException si PostgreSQL no acepta la conexión
     */
    public synchronized Connection connection() throws SQLException {
        if (connection == null || connection.isClosed()) {
            connection = DriverManager.getConnection(url, user, password);
            connection.setAutoCommit(false);
            connected = true;
            LOG.info("Conectado a PostgreSQL como " + user);
        }
        return connection;
    }

    /** Revierte la transacción en curso. Si no se puede, descarta la conexión. */
    public synchronized void rollbackQuietly() {
        if (connection == null) {
            return;
        }
        try {
            connection.rollback();
        } catch (SQLException e) {
            LOG.log(Level.WARNING, "No se pudo revertir la transacción; se descarta la conexión: " + e.getMessage());
            discard();
        }
    }

    /** Cierra la conexión y la olvida; la siguiente operación abrirá otra. */
    public synchronized void discard() {
        connected = false;
        if (connection == null) {
            return;
        }
        try {
            connection.close();
        } catch (SQLException e) {
            LOG.log(Level.FINE, "Error al cerrar la conexión con PostgreSQL: " + e.getMessage());
        }
        connection = null;
    }

    /** @return {@code true} si la última vez que se usó la conexión estaba abierta */
    public boolean isConnected() {
        return connected;
    }

    /** @return la cuenta con la que se conecta */
    public String user() {
        return user;
    }

    @Override
    public void close() {
        discard();
    }
}
