package com.elastiflix.simulator.bronze;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.stream.Collectors;

/**
 * La conexión de DuckDB con la que el simulador lee Bronze (diseño, secciones
 * 9.8 y 34).
 *
 * <p>DuckDB corre embebido y en memoria, con hilos y memoria limitados para
 * caber en el contenedor. La conexión es de larga vida: ve cada snapshot nuevo
 * de Iceberg sin reconectar. Solo la usa el hilo del seguimiento.</p>
 */
final class BronzeConnection implements AutoCloseable {

    /**
     * Una fila de {@code bronze.movie}, con lo único que el seguimiento necesita.
     *
     * @param cdcOpType operación del último evento: {@code +I}, {@code +U} o {@code -D}
     * @param cdcOpTs   instante del último evento, en milisegundos
     */
    record BronzeRow(String cdcOpType, long cdcOpTs) {
    }

    private static final String JDBC_URL = "jdbc:duckdb:";

    /** Una sola tabla: DuckDB 1.5.6 falla al combinar varias tablas con borrados (diseño, sección 34). */
    private static final String TRACKING_SQL =
            "SELECT movie_id, cdc_op_type, cdc_op_ts FROM lake.bronze.movie WHERE movie_id IN (%s)";

    private final Connection connection;

    private BronzeConnection(Connection connection) {
        this.connection = connection;
    }

    /**
     * Abre DuckDB y ejecuta el SQL de inicialización: carga las extensiones,
     * declara el acceso a RustFS y adjunta el catálogo.
     *
     * @param threads        hilos de DuckDB
     * @param memoryLimit    memoria de DuckDB, por ejemplo {@code 128MB}
     * @param initStatements sentencias de {@code attach_lakehouse.sql}, con las claves ya puestas
     * @return la conexión lista para consultar
     * @throws SQLException si DuckDB no abre o alguna sentencia falla
     */
    static BronzeConnection open(int threads, String memoryLimit, List<String> initStatements)
            throws SQLException {
        Properties limits = new Properties();
        limits.setProperty("threads", String.valueOf(threads));
        limits.setProperty("memory_limit", memoryLimit);
        Connection connection = DriverManager.getConnection(JDBC_URL, limits);
        try (Statement statement = connection.createStatement()) {
            for (String sql : initStatements) {
                statement.execute(sql);
            }
        } catch (SQLException e) {
            connection.close();
            throw e;
        }
        return new BronzeConnection(connection);
    }

    /**
     * Consulta de seguimiento: una sola consulta por lote (diseño, sección 9.3).
     *
     * @param movieIds películas con alguna transacción pendiente de ver en Bronze
     * @return la fila de Bronze de cada película que ya tiene una
     * @throws SQLException si la consulta falla
     */
    Map<Long, BronzeRow> readMovieRows(Collection<Long> movieIds) throws SQLException {
        Map<Long, BronzeRow> rows = new HashMap<>();
        if (movieIds.isEmpty()) {
            return rows;
        }
        String idList = movieIds.stream().map(String::valueOf).collect(Collectors.joining(","));
        try (Statement statement = connection.createStatement();
             ResultSet result = statement.executeQuery(String.format(TRACKING_SQL, idList))) {
            while (result.next()) {
                rows.put(result.getLong(1), new BronzeRow(result.getString(2), result.getLong(3)));
            }
        }
        return rows;
    }

    @Override
    public void close() throws SQLException {
        connection.close();
    }
}
