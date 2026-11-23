package com.elastiflix.simulator.simulation;

/**
 * Operaciones que se pueden lanzar a mano desde la interfaz (RF-08).
 */
public enum ManualAction {

    /** INSERT de la siguiente película pendiente en el orden de {@code movie.csv}. */
    INSERT_NEXT("INSERT de la siguiente película pendiente", null),

    /** INSERT de una película concreta que aún no está en {@code catalog}. */
    INSERT("INSERT de esta película", null),

    UPDATE_DESCRIPTIVE("UPDATE descriptivo", UpdateKind.DESCRIPTIVE),
    UPDATE_MEASURES("UPDATE de medidas", UpdateKind.MEASURES),
    UPDATE_RELATIONS("UPDATE de relaciones", UpdateKind.RELATIONS),
    UPDATE_CATALOG("UPDATE de catálogo", UpdateKind.CATALOG),

    /** DELETE de una película viva. */
    DELETE("DELETE de esta película", null),

    /** Reinserción de una película borrada. */
    REINSERT("Reinserción de esta película", null);

    private final String label;
    private final UpdateKind updateKind;

    ManualAction(String label, UpdateKind updateKind) {
        this.label = label;
        this.updateKind = updateKind;
    }

    /** @return el texto que se muestra en el diálogo y en el log */
    public String label() {
        return label;
    }

    /** @return el tipo de UPDATE, o {@code null} si la operación no es un UPDATE */
    public UpdateKind updateKind() {
        return updateKind;
    }
}
