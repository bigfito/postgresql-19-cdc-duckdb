package com.elastiflix.simulator.simulation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.OptionalLong;
import java.util.Set;

/**
 * Situación de cada película, incluida la reanudación sobre una base con datos
 * (RF-13; diseño, sección 9.5).
 */
class MovieRegistryTest {

    private static final List<Long> MOVIES = List.of(11L, 23L, 46L, 58L, 60L, 77L);

    @Test
    void sobreUnaBaseVaciaTodasQuedanPendientes() {
        MovieRegistry registry = new MovieRegistry(MOVIES, Set.of());

        assertEquals(6, registry.pendingCount());
        assertEquals(0, registry.aliveCount());
        assertEquals(0, registry.insertedCount());
        assertEquals(OptionalLong.of(11), registry.nextPending());
    }

    @Test
    void alReanudarContinuaTrasLaUltimaPeliculaPresente() {
        MovieRegistry registry = new MovieRegistry(MOVIES, Set.of(11L, 23L, 58L));

        assertEquals(OptionalLong.of(60), registry.nextPending(), "la siguiente a la 58, última presente");
        assertEquals(MovieState.ALIVE, registry.stateOf(11));
        assertEquals(MovieState.DELETED, registry.stateOf(46), "anterior a la última presente y ausente: borrada");
        assertEquals(MovieState.PENDING, registry.stateOf(60));
        assertEquals(MovieState.PENDING, registry.stateOf(77));
        assertEquals(3, registry.aliveCount());
        assertEquals(1, registry.deletedCount());
        assertEquals(2, registry.pendingCount());
        assertEquals(3, registry.insertedCount(), "el avance parte de las películas presentes");
    }

    @Test
    void conElDatasetCompletoNoQuedaNingunaPendiente() {
        MovieRegistry registry = new MovieRegistry(MOVIES, Set.copyOf(MOVIES));

        assertTrue(registry.nextPending().isEmpty());
        assertEquals(6, registry.aliveCount());
    }

    @Test
    void ignoraLasPeliculasDeLaBaseQueNoEstanEnElDataset() {
        MovieRegistry registry = new MovieRegistry(MOVIES, Set.of(11L, 999L));

        assertEquals(1, registry.aliveCount());
        assertNull(registry.stateOf(999));
        assertEquals(OptionalLong.of(23), registry.nextPending());
    }

    @Test
    void elCicloDeUnaPeliculaActualizaLosContadores() {
        MovieRegistry registry = new MovieRegistry(MOVIES, Set.of());

        registry.markAlive(11);
        assertEquals(MovieState.ALIVE, registry.stateOf(11));
        assertEquals(OptionalLong.of(23), registry.nextPending());

        registry.markDeleted(11);
        assertEquals(MovieState.DELETED, registry.stateOf(11));
        assertEquals(0, registry.aliveCount());
        assertEquals(1, registry.deletedCount());
        assertEquals(11, registry.deletedAt(0));

        registry.markAlive(11);
        assertEquals(1, registry.aliveCount());
        assertEquals(0, registry.deletedCount());
        assertEquals(1, registry.insertedCount(), "una reinserción no cuenta dos veces en el avance");
        assertEquals(5, registry.pendingCount());
    }

    @Test
    void unaPeliculaInsertadaAManoFueraDeOrdenNoSeRepite() {
        MovieRegistry registry = new MovieRegistry(MOVIES, Set.of());

        registry.markAlive(23);
        registry.markAlive(11);

        assertEquals(OptionalLong.of(46), registry.nextPending(), "salta la 23, que ya se insertó a mano");
    }

    @Test
    void unAltaFallidaCuentaComoBorradaYNoSeReintentaEnOrden() {
        MovieRegistry registry = new MovieRegistry(MOVIES, Set.of());

        registry.markDeleted(11);

        assertEquals(OptionalLong.of(23), registry.nextPending());
        assertEquals(MovieState.DELETED, registry.stateOf(11));
        assertEquals(0, registry.insertedCount(), "no llegó a insertarse");
        assertEquals(5, registry.pendingCount());
    }
}
