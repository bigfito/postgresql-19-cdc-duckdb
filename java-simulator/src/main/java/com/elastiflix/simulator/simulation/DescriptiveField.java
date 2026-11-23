package com.elastiflix.simulator.simulation;

/**
 * Columnas de {@code movie} que cambia un UPDATE descriptivo (diseño,
 * sección 9.5).
 */
public enum DescriptiveField {
    TITLE("title"),
    TAGLINE("tagline"),
    OVERVIEW("overview"),
    HOMEPAGE("homepage");

    private final String columnName;

    DescriptiveField(String columnName) {
        this.columnName = columnName;
    }

    /** @return el nombre de la columna en {@code catalog.movie} */
    public String columnName() {
        return columnName;
    }
}
