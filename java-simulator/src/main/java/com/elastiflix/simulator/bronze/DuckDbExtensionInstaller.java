package com.elastiflix.simulator.bronze;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;

/**
 * Instala las extensiones de DuckDB durante el build de la imagen (diseño,
 * sección 34). No se usa al ejecutar el simulador.
 *
 * <p>Son tres: {@code httpfs}, {@code iceberg} y {@code avro}. {@code iceberg}
 * necesita {@code avro} y, si no la encuentra, intenta descargarla al
 * cargarse. Con las tres ya instaladas, el contenedor no descarga nada.</p>
 *
 * <p>Uso: {@code java -cp ... DuckDbExtensionInstaller /opt/duckdb_extensions}</p>
 */
public final class DuckDbExtensionInstaller {

    private static final String[] EXTENSIONS = {"httpfs", "avro", "iceberg"};

    private DuckDbExtensionInstaller() {
    }

    /**
     * @param args un único argumento: el directorio donde se instalan
     * @throws SQLException si alguna extensión no se puede instalar o cargar;
     *                      el build de la imagen falla
     */
    public static void main(String[] args) throws SQLException {
        if (args.length != 1) {
            throw new IllegalArgumentException("Uso: DuckDbExtensionInstaller <directorio de extensiones>");
        }
        String directory = args[0];
        try (Connection connection = DriverManager.getConnection("jdbc:duckdb:");
             Statement statement = connection.createStatement()) {
            statement.execute("SET extension_directory = '" + directory + "'");
            for (String extension : EXTENSIONS) {
                statement.execute("INSTALL " + extension);
            }
            // Cargarlas aquí comprueba que lo instalado sirve.
            for (String extension : EXTENSIONS) {
                statement.execute("LOAD " + extension);
            }
            printInstalled(statement, directory);
        }
    }

    private static void printInstalled(Statement statement, String directory) throws SQLException {
        String sql = "SELECT extension_name, extension_version FROM duckdb_extensions()"
                + " WHERE installed AND extension_name IN ('httpfs', 'avro', 'iceberg') ORDER BY 1";
        try (ResultSet result = statement.executeQuery(sql)) {
            while (result.next()) {
                System.out.println("Extensión de DuckDB instalada en " + directory + ": "
                        + result.getString(1) + " " + result.getString(2));
            }
        }
    }
}
