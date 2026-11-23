package com.elastiflix.simulator.simulation;

/**
 * Estado de la simulación automática, tal como lo muestra la cabecera de la
 * pantalla (diseño, sección 9.3).
 */
public enum SimulationStatus {

    RUNNING("EN MARCHA", "▶"),
    PAUSED("EN PAUSA", "■"),
    /** Se agotó {@code movie.csv} y el modo continuo está desactivado. */
    FINISHED("TERMINADO", "✓");

    private final String label;
    private final String symbol;

    SimulationStatus(String label, String symbol) {
        this.label = label;
        this.symbol = symbol;
    }

    /** @return el texto de la cabecera */
    public String label() {
        return label;
    }

    /** @return el símbolo que acompaña al texto */
    public String symbol() {
        return symbol;
    }
}
