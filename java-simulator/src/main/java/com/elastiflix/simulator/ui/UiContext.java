package com.elastiflix.simulator.ui;

import com.elastiflix.simulator.bronze.BronzeTracker;
import com.elastiflix.simulator.dataset.Dataset;
import com.elastiflix.simulator.db.PostgresSession;
import com.elastiflix.simulator.engine.SimulationEngine;
import com.elastiflix.simulator.simulation.ActivityBoard;
import com.elastiflix.simulator.simulation.MovieRegistry;
import com.elastiflix.simulator.simulation.SimulationControl;

/**
 * Todo lo que la interfaz necesita para mostrar y dirigir la simulación.
 *
 * @param dataset  dataset en memoria, para buscar películas por título
 * @param registry situación de cada película
 * @param board    contadores y últimas transacciones
 * @param control  pausa, intervalo y pesos
 * @param engine   hilo de la simulación, al que se piden las operaciones manuales
 * @param tracker  seguimiento hasta Bronze
 * @param session  conexión con PostgreSQL, para mostrar su estado
 * @param seed     semilla de la secuencia automática
 */
public record UiContext(
        Dataset dataset,
        MovieRegistry registry,
        ActivityBoard board,
        SimulationControl control,
        SimulationEngine engine,
        BronzeTracker tracker,
        PostgresSession session,
        long seed) {
}
