package com.elastiflix.simulator.simulation;

import com.elastiflix.simulator.config.Weights;

import java.util.logging.Logger;

/**
 * Lo que se puede cambiar en caliente desde la interfaz (RF-07): pausa,
 * intervalo entre transacciones y pesos.
 *
 * <p>La interfaz escribe y el hilo de la simulación lee; cada campo es
 * {@code volatile}. Todo cambio queda en el log (RF-11).</p>
 */
public final class SimulationControl {

    private static final Logger LOG = Logger.getLogger(SimulationControl.class.getName());

    /** Intervalos, en milisegundos, por los que se mueven las teclas {@code +} y {@code -}. */
    private static final long[] DELAY_STEPS = {10, 25, 50, 100, 250, 500, 1_000, 2_000, 5_000, 10_000};

    private volatile boolean paused;
    private volatile long delayMillis;
    private volatile Weights weights;

    /**
     * @param paused      si la simulación arranca en pausa
     * @param delayMillis intervalo inicial entre transacciones
     * @param weights     pesos iniciales
     */
    public SimulationControl(boolean paused, long delayMillis, Weights weights) {
        this.paused = paused;
        this.delayMillis = delayMillis;
        this.weights = weights;
    }

    /** @return {@code true} si la simulación automática está en pausa */
    public boolean isPaused() {
        return paused;
    }

    /** @return el intervalo vigente entre transacciones, en milisegundos */
    public long delayMillis() {
        return delayMillis;
    }

    /** @return los pesos vigentes */
    public Weights weights() {
        return weights;
    }

    /** Pausa la simulación automática si está en marcha, o la reanuda si está en pausa. */
    public void togglePause() {
        paused = !paused;
        LOG.info("CONFIG simulación automática " + (paused ? "en pausa" : "reanudada"));
    }

    /** Reduce el intervalo al escalón anterior; en el más corto no hace nada. */
    public void faster() {
        for (int index = DELAY_STEPS.length - 1; index >= 0; index--) {
            if (DELAY_STEPS[index] < delayMillis) {
                changeDelay(DELAY_STEPS[index]);
                return;
            }
        }
    }

    /** Aumenta el intervalo al escalón siguiente; en el más largo no hace nada. */
    public void slower() {
        for (long step : DELAY_STEPS) {
            if (step > delayMillis) {
                changeDelay(step);
                return;
            }
        }
    }

    private void changeDelay(long newDelayMillis) {
        LOG.info("CONFIG intervalo entre transacciones: " + delayMillis + " ms → " + newDelayMillis + " ms");
        delayMillis = newDelayMillis;
    }

    /**
     * Cambia los pesos de INSERT, UPDATE y DELETE.
     *
     * @param newWeights pesos nuevos, ya validados
     */
    public void changeWeights(Weights newWeights) {
        LOG.info("CONFIG pesos INSERT/UPDATE/DELETE: " + describe(weights) + " → " + describe(newWeights));
        weights = newWeights;
    }

    private static String describe(Weights weights) {
        return weights.insert() + "/" + weights.update() + "/" + weights.delete();
    }
}
