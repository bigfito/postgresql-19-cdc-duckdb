package com.elastiflix.simulator.dataset;

import java.nio.file.Path;
import java.util.List;
import java.util.logging.Logger;

/**
 * Carga en memoria los 20 archivos de {@code raw_data/}, uno por tabla (RF-01).
 */
public final class DatasetLoader {

    private static final Logger LOG = Logger.getLogger(DatasetLoader.class.getName());

    private final CsvTableReader reader = new CsvTableReader();

    /**
     * @param directory directorio que contiene los 20 CSV
     * @return el dataset completo
     * @throws com.elastiflix.simulator.error.SimulatorException si falta un
     *         archivo o alguno no tiene el formato esperado
     */
    public Dataset load(Path directory) {
        long startedAt = System.nanoTime();
        Dataset dataset = new Dataset();
        for (CatalogTable table : CatalogTable.values()) {
            List<Object[]> rows = reader.read(table, directory.resolve(table.fileName()));
            dataset.addTable(table, rows);
            LOG.fine(() -> "Leído " + table.fileName() + ": " + rows.size() + " filas");
        }
        long elapsedMillis = (System.nanoTime() - startedAt) / 1_000_000;
        LOG.info("Dataset cargado en memoria: " + CatalogTable.values().length + " archivos, "
                + dataset.totalRowCount() + " filas, " + dataset.movieCount() + " películas, en "
                + elapsedMillis + " ms");
        return dataset;
    }
}
