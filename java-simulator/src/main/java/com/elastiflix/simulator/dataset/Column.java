package com.elastiflix.simulator.dataset;

/**
 * Una columna de una tabla del esquema {@code catalog}.
 *
 * @param name nombre de la columna, igual en el CSV y en PostgreSQL
 * @param type tipo con el que se lee y se envía
 */
public record Column(String name, ColumnType type) {

    static Column bigint(String name) {
        return new Column(name, ColumnType.BIGINT);
    }

    static Column integer(String name) {
        return new Column(name, ColumnType.INTEGER);
    }

    static Column text(String name) {
        return new Column(name, ColumnType.TEXT);
    }

    static Column numeric(String name) {
        return new Column(name, ColumnType.NUMERIC);
    }

    static Column date(String name) {
        return new Column(name, ColumnType.DATE);
    }

    static Column bool(String name) {
        return new Column(name, ColumnType.BOOLEAN);
    }
}
