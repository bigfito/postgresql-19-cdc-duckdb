package com.elastiflix.simulator.config;

import com.elastiflix.simulator.error.ErrorCode;
import com.elastiflix.simulator.error.SimulatorException;

/**
 * Pesos con los que se elige la siguiente operación automática (RF-04).
 *
 * <p>No son porcentajes: con 70, 25 y 5, de cada 100 operaciones salen unas 70
 * INSERT, 25 UPDATE y 5 DELETE.</p>
 *
 * @param insert peso de INSERT
 * @param update peso de UPDATE
 * @param delete peso de DELETE
 */
public record Weights(int insert, int update, int delete) {

    /**
     * Comprueba que ningún peso es negativo y que al menos uno es mayor que cero.
     */
    public Weights {
        if (insert < 0 || update < 0 || delete < 0) {
            throw new SimulatorException(ErrorCode.CONFIG_INVALID,
                    "los pesos no pueden ser negativos (" + insert + ", " + update + ", " + delete + ")");
        }
        if (insert + update + delete == 0) {
            throw new SimulatorException(ErrorCode.CONFIG_INVALID,
                    "al menos un peso debe ser mayor que cero");
        }
    }

    /** @return la suma de los tres pesos */
    public int total() {
        return insert + update + delete;
    }
}
