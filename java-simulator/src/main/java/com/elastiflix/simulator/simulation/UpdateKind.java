package com.elastiflix.simulator.simulation;

/**
 * Las cuatro clases de UPDATE (diseño, sección 9.5). Cada una ejercita un
 * camino distinto de Silver.
 */
public enum UpdateKind {

    /** Cambia {@code title}, {@code tagline}, {@code overview} u {@code homepage}. */
    DESCRIPTIVE("descriptivo"),

    /** Cambia popularidad, votos, puntuaciones, presupuesto y recaudación. */
    MEASURES("medidas"),

    /** Añade o quita un género o una keyword de la película. */
    RELATIONS("relaciones"),

    /** Renombra la colección de la película o una de sus keywords. */
    CATALOG("catálogo");

    private final String label;

    UpdateKind(String label) {
        this.label = label;
    }

    /** @return el nombre que se muestra en la pantalla y en el log */
    public String label() {
        return label;
    }
}
