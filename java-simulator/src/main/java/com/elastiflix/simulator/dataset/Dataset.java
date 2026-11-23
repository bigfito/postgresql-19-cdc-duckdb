package com.elastiflix.simulator.dataset;

import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * El dataset completo en memoria (RF-01): los catálogos y las entidades
 * indexados por su clave, las películas en el orden de {@code movie.csv} y las
 * relaciones indexadas por {@code movie_id}.
 *
 * <p>Cada fila es un arreglo con un valor por columna, en el orden de
 * {@link CatalogTable#columns()}. Tras construirse no cambia, así que se puede
 * leer desde varios hilos.</p>
 */
public final class Dataset {

    private static final int MOVIE_ID_INDEX = 0;
    private static final int TITLE_INDEX = CatalogTable.MOVIE.columnIndex("title");

    private final Map<CatalogTable, Map<Object, Object[]>> sharedRows = new EnumMap<>(CatalogTable.class);
    private final Map<CatalogTable, Map<Long, List<Object[]>>> relationRows = new EnumMap<>(CatalogTable.class);
    private final Map<CatalogTable, Integer> rowCounts = new EnumMap<>(CatalogTable.class);
    private final List<Long> movieIds = new ArrayList<>();
    private final Map<Long, Object[]> movies = new HashMap<>();

    /**
     * Añade las filas de una tabla. Solo lo usa {@link DatasetLoader}.
     *
     * @param table tabla a la que pertenecen
     * @param rows  filas leídas de su CSV, en el orden del archivo
     */
    void addTable(CatalogTable table, List<Object[]> rows) {
        rowCounts.put(table, rows.size());
        if (table.isShared()) {
            sharedRows.put(table, indexByKey(rows));
        } else if (table.isRelation()) {
            relationRows.put(table, groupByMovie(rows));
        } else {
            addMovies(rows);
        }
    }

    private static Map<Object, Object[]> indexByKey(List<Object[]> rows) {
        Map<Object, Object[]> byKey = new HashMap<>(rows.size() * 2);
        for (Object[] row : rows) {
            byKey.put(row[0], row);
        }
        return byKey;
    }

    private static Map<Long, List<Object[]>> groupByMovie(List<Object[]> rows) {
        Map<Long, List<Object[]>> byMovie = new HashMap<>();
        for (Object[] row : rows) {
            byMovie.computeIfAbsent((Long) row[MOVIE_ID_INDEX], movieId -> new ArrayList<>(4)).add(row);
        }
        return byMovie;
    }

    private void addMovies(List<Object[]> rows) {
        for (Object[] row : rows) {
            Long movieId = (Long) row[MOVIE_ID_INDEX];
            movieIds.add(movieId);
            movies.put(movieId, row);
        }
    }

    /** @return los {@code movie_id} en el orden de {@code movie.csv}, que es el orden de alta */
    public List<Long> movieIds() {
        return Collections.unmodifiableList(movieIds);
    }

    /** @return cuántas películas tiene el dataset */
    public int movieCount() {
        return movieIds.size();
    }

    /**
     * @param movieId identificador de la película
     * @return {@code true} si el dataset la contiene
     */
    public boolean hasMovie(long movieId) {
        return movies.containsKey(movieId);
    }

    /**
     * @param movieId identificador de la película
     * @return su fila de {@code movie.csv}, o {@code null} si no existe
     */
    public Object[] movie(long movieId) {
        return movies.get(movieId);
    }

    /**
     * @param movieId identificador de la película
     * @return su título en el dataset, o una cadena vacía si no existe
     */
    public String title(long movieId) {
        Object[] row = movies.get(movieId);
        return row == null ? "" : (String) row[TITLE_INDEX];
    }

    /**
     * @param movieId    identificador de la película
     * @param columnName nombre de una columna de {@code movie}
     * @return el valor de esa columna en el dataset; puede ser {@code null}
     */
    public Object movieValue(long movieId, String columnName) {
        return movies.get(movieId)[CatalogTable.MOVIE.columnIndex(columnName)];
    }

    /**
     * @param table catálogo o entidad compartida
     * @param key   clave buscada
     * @return la fila con esa clave, o {@code null} si el dataset no la trae
     */
    public Object[] sharedRow(CatalogTable table, Object key) {
        return sharedRows.get(table).get(key);
    }

    /**
     * @param table   tabla de relación
     * @param movieId identificador de la película
     * @return las filas de esa película en la tabla, en el orden del archivo;
     *         una lista vacía si no tiene ninguna
     */
    public List<Object[]> relationRows(CatalogTable table, long movieId) {
        return relationRows.get(table).getOrDefault(movieId, List.of());
    }

    /**
     * @param table cualquiera de las 20 tablas
     * @return cuántas filas trae su CSV
     */
    public int rowCount(CatalogTable table) {
        return rowCounts.getOrDefault(table, 0);
    }

    /** @return la suma de las filas de los 20 archivos */
    public int totalRowCount() {
        return rowCounts.values().stream().mapToInt(Integer::intValue).sum();
    }
}
