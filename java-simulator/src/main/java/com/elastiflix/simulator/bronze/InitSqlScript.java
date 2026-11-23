package com.elastiflix.simulator.bronze;

import com.elastiflix.simulator.error.ErrorCode;
import com.elastiflix.simulator.error.SimulatorException;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Prepara el SQL de inicialización de DuckDB (diseño, sección 34) para
 * ejecutarlo sentencia a sentencia.
 *
 * <p>El archivo lleva marcadores como {@code ${AWS_ACCESS_KEY_ID}} en lugar de
 * las claves. Aquí se sustituyen justo antes de ejecutarlo, se descartan las
 * líneas de comentario y el resto se parte por {@code ;}. Por eso el archivo
 * no puede llevar {@code ;} dentro de un comentario.</p>
 */
public final class InitSqlScript {

    private InitSqlScript() {
    }

    /**
     * Lee el archivo y devuelve sus sentencias listas para ejecutar.
     *
     * @param file      ruta de {@code attach_lakehouse.sql}
     * @param variables valor de cada marcador, por nombre
     * @return las sentencias, en orden
     * @throws SimulatorException si el archivo no se puede leer o queda algún
     *                            marcador sin valor
     */
    public static List<String> load(Path file, Map<String, String> variables) {
        try {
            return statements(Files.readString(file, StandardCharsets.UTF_8), variables);
        } catch (IOException e) {
            throw new SimulatorException(ErrorCode.BRONZE_INIT_SQL, "no se pudo leer " + file, e);
        }
    }

    /**
     * Convierte el texto del archivo en sentencias.
     *
     * @param script    contenido del archivo
     * @param variables valor de cada marcador, por nombre
     * @return las sentencias, sin comentarios, sin el {@code ;} final y sin vacías
     * @throws SimulatorException si queda algún marcador sin valor
     */
    public static List<String> statements(String script, Map<String, String> variables) {
        String sql = replaceMarkers(withoutCommentLines(script), variables);
        if (sql.contains("${")) {
            throw new SimulatorException(ErrorCode.BRONZE_INIT_SQL,
                    "el SQL de inicialización lleva un marcador ${...} para el que no hay valor");
        }
        List<String> statements = new ArrayList<>();
        for (String statement : sql.split(";")) {
            if (!statement.isBlank()) {
                statements.add(statement.strip());
            }
        }
        return statements;
    }

    private static String withoutCommentLines(String script) {
        StringBuilder kept = new StringBuilder(script.length());
        for (String line : script.split("\\R")) {
            if (!line.strip().startsWith("--")) {
                kept.append(line).append('\n');
            }
        }
        return kept.toString();
    }

    /** Cada valor va dentro de comillas simples en el SQL, así que una comilla simple se duplica. */
    private static String replaceMarkers(String sql, Map<String, String> variables) {
        String result = sql;
        for (Map.Entry<String, String> variable : variables.entrySet()) {
            String marker = "${" + variable.getKey() + "}";
            result = result.replace(marker, variable.getValue().replace("'", "''"));
        }
        return result;
    }
}
