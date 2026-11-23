package com.elastiflix.simulator.simulation;

/**
 * Estado del seguimiento de una transacción hasta Bronze (RF-09; diseño,
 * sección 9.3).
 */
public enum BronzeStatus {

    /** Aún no se ha visto el cambio en {@code bronze.movie}. */
    PENDING,

    /** El cambio ya está en Bronze. */
    ARRIVED,

    /** Lleva más tiempo del esperado sin aparecer; se sigue comprobando. */
    LATE,

    /** No se sigue: el seguimiento está desactivado o la transacción falló. */
    NOT_TRACKED;

    /** @return {@code true} mientras haya que seguir consultando Bronze por esta transacción */
    public boolean isWaiting() {
        return this == PENDING || this == LATE;
    }
}
