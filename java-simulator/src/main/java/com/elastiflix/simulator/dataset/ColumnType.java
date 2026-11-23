package com.elastiflix.simulator.dataset;

import java.math.BigDecimal;
import java.time.LocalDate;

/**
 * Tipos de columna del modelo relacional (diseño, sección 12) y cómo se lee
 * cada uno del texto de un CSV (diseño, sección 8.3).
 */
public enum ColumnType {

    /** Entero de 64 bits: identificadores. */
    BIGINT {
        @Override
        Object parse(String text) {
            return Long.valueOf(text);
        }
    },

    /** Entero de 32 bits: posiciones, minutos, votos. */
    INTEGER {
        @Override
        Object parse(String text) {
            return Integer.valueOf(text);
        }
    },

    /** Texto, tal como viene. */
    TEXT {
        @Override
        Object parse(String text) {
            return text;
        }
    },

    /** Decimal con punto y la escala de su columna. */
    NUMERIC {
        @Override
        Object parse(String text) {
            return new BigDecimal(text);
        }
    },

    /** Fecha con formato {@code YYYY-MM-DD}. */
    DATE {
        @Override
        Object parse(String text) {
            return LocalDate.parse(text);
        }
    },

    /** Booleano escrito como {@code true} o {@code false}. */
    BOOLEAN {
        @Override
        Object parse(String text) {
            if (text.equals("true")) {
                return Boolean.TRUE;
            }
            if (text.equals("false")) {
                return Boolean.FALSE;
            }
            throw new IllegalArgumentException("se esperaba true o false");
        }
    };

    /**
     * Convierte el texto de una celda al objeto Java que JDBC enviará a
     * PostgreSQL.
     *
     * @param text contenido de la celda; nunca nulo ni vacío
     * @return el valor con su tipo
     * @throws RuntimeException si el texto no corresponde al tipo
     */
    abstract Object parse(String text);
}
