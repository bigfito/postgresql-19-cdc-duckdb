package com.elastiflix.simulator.simulation;

/**
 * Situación de una película del dataset respecto a PostgreSQL.
 */
public enum MovieState {

    /** Aún no se ha insertado. */
    PENDING("pendiente"),

    /** Está en {@code catalog.movie}. */
    ALIVE("viva"),

    /** Se borró, o su alta falló por un dato inconsistente; se puede reinsertar. */
    DELETED("borrada");

    private final String label;

    MovieState(String label) {
        this.label = label;
    }

    /** @return el nombre que se muestra en la pantalla */
    public String label() {
        return label;
    }
}
