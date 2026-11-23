package com.elastiflix.simulator.dataset;

import com.elastiflix.simulator.error.ErrorCode;
import com.elastiflix.simulator.error.SimulatorException;

import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;

import java.io.IOException;
import java.io.Reader;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * Lee el CSV de una tabla y devuelve sus filas con cada valor ya convertido a
 * su tipo.
 *
 * <p>Formato (diseño, sección 8.3): UTF-8, RFC 4180, una fila de cabecera con
 * los nombres de columna, y {@code NULL} escrito como campo vacío. Una celda
 * puede contener comas, comillas y saltos de línea.</p>
 */
public final class CsvTableReader {

    private static final CSVFormat FORMAT = CSVFormat.RFC4180.builder()
            .setHeader()
            .setSkipHeaderRecord(true)
            .get();

    /**
     * Lee el archivo de una tabla.
     *
     * @param table tabla a la que pertenece el archivo
     * @param file  ruta del CSV
     * @return una fila por registro; cada fila es un arreglo con un valor por
     *         columna, en el orden de {@link CatalogTable#columns()}, y
     *         {@code null} donde la celda está vacía
     * @throws SimulatorException si el archivo falta, su cabecera no coincide
     *                            con la tabla o un valor no es de su tipo
     */
    public List<Object[]> read(CatalogTable table, Path file) {
        if (!Files.isRegularFile(file)) {
            throw new SimulatorException(ErrorCode.DATASET_FILE_MISSING, "no existe " + file);
        }
        try (Reader reader = Files.newBufferedReader(file, StandardCharsets.UTF_8);
             CSVParser parser = FORMAT.parse(reader)) {
            checkHeader(table, file, parser.getHeaderNames());
            return readRows(table, file, parser);
        } catch (IOException | UncheckedIOException e) {
            throw new SimulatorException(ErrorCode.DATASET_FORMAT, "no se pudo leer " + file, e);
        }
    }

    private void checkHeader(CatalogTable table, Path file, List<String> header) {
        List<String> expected = table.columns().stream().map(Column::name).toList();
        if (!expected.equals(header)) {
            throw new SimulatorException(ErrorCode.DATASET_FORMAT,
                    file.getFileName() + " tiene la cabecera " + header + " y se esperaba " + expected);
        }
    }

    private List<Object[]> readRows(CatalogTable table, Path file, CSVParser parser) {
        List<Object[]> rows = new ArrayList<>();
        for (CSVRecord record : parser) {
            rows.add(toRow(table, file, record));
        }
        return rows;
    }

    private Object[] toRow(CatalogTable table, Path file, CSVRecord record) {
        List<Column> columns = table.columns();
        if (record.size() != columns.size()) {
            throw formatError(file, record, "tiene " + record.size() + " campos y se esperaban " + columns.size());
        }
        Object[] row = new Object[columns.size()];
        for (int index = 0; index < row.length; index++) {
            row[index] = toValue(columns.get(index), record.get(index), file, record);
        }
        return row;
    }

    /** Una celda vacía es NULL; el dataset no contiene cadenas vacías. */
    private Object toValue(Column column, String text, Path file, CSVRecord record) {
        if (text.isEmpty()) {
            return null;
        }
        try {
            return column.type().parse(text);
        } catch (RuntimeException e) {
            throw formatError(file, record,
                    "el valor «" + text + "» de la columna " + column.name() + " no es de tipo " + column.type());
        }
    }

    private static SimulatorException formatError(Path file, CSVRecord record, String problem) {
        return new SimulatorException(ErrorCode.DATASET_FORMAT,
                file.getFileName() + ", registro " + record.getRecordNumber() + ": " + problem);
    }
}
