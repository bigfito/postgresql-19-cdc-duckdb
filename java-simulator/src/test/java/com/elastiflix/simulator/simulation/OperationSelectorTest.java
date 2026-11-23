package com.elastiflix.simulator.simulation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.elastiflix.simulator.config.Weights;
import com.elastiflix.simulator.dataset.CatalogTable;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.EnumSet;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Random;
import java.util.Set;
import java.util.stream.LongStream;

/**
 * Selección de la siguiente operación con los pesos y la semilla (RF-04 y
 * RF-05) y reglas de carga del diseño (sección 9.5).
 */
class OperationSelectorTest {

    private static final Weights DEFAULT_WEIGHTS = new Weights(70, 25, 5);
    private static final Weights ONLY_INSERT = new Weights(1, 0, 0);
    private static final Weights ONLY_UPDATE = new Weights(0, 1, 0);
    private static final Weights ONLY_DELETE = new Weights(0, 0, 1);
    private static final CatalogLinks NO_LINKS = new CatalogLinks(null, List.of());

    // ------------------------------------------------------------------
    // Reproducibilidad (RF-05)
    // ------------------------------------------------------------------

    @Test
    void laMismaSemillaRepiteLaMismaSecuencia() {
        List<String> first = simulate(42, 2_000);
        List<String> second = simulate(42, 2_000);

        assertEquals(first, second);
    }

    @Test
    void otraSemillaDaOtraSecuencia() {
        assertNotEquals(simulate(42, 500), simulate(43, 500));
    }

    @Test
    void laSecuenciaMezclaLasTresOperacionesYLosCuatroTiposDeUpdate() {
        List<String> sequence = simulate(42, 2_000);

        assertTrue(sequence.stream().anyMatch(step -> step.startsWith("INSERT")));
        assertTrue(sequence.stream().anyMatch(step -> step.startsWith("DELETE")));
        for (UpdateKind kind : UpdateKind.values()) {
            assertTrue(sequence.stream().anyMatch(step -> step.endsWith(kind.name())), "falta " + kind);
        }
    }

    // ------------------------------------------------------------------
    // Pesos (RF-04)
    // ------------------------------------------------------------------

    @Test
    void elRepartoSigueLosPesos() {
        OperationSelector selector = new OperationSelector(new Random(7));
        MovieRegistry registry = registryWith(100_000, 0);
        registry.markAlive(1);
        Map<OperationType, Integer> counts = new EnumMap<>(OperationType.class);

        for (int step = 0; step < 20_000; step++) {
            PlannedOperation operation = selector.next(DEFAULT_WEIGHTS, registry, true).orElseThrow();
            counts.merge(operation.type(), 1, Integer::sum);
            if (operation.type() == OperationType.INSERT) {
                registry.markAlive(operation.movieId());
            }
        }

        assertEquals(0.70, counts.get(OperationType.INSERT) / 20_000.0, 0.02);
        assertEquals(0.25, counts.get(OperationType.UPDATE) / 20_000.0, 0.02);
        assertEquals(0.05, counts.get(OperationType.DELETE) / 20_000.0, 0.02);
    }

    @Test
    void unPesoCeroNoSaleNunca() {
        OperationSelector selector = new OperationSelector(new Random(1));
        MovieRegistry registry = registryWith(50, 10);

        for (int step = 0; step < 500; step++) {
            PlannedOperation operation = selector.next(new Weights(0, 5, 5), registry, true).orElseThrow();
            assertNotEquals(OperationType.INSERT, operation.type());
        }
    }

    // ------------------------------------------------------------------
    // Reglas de carga (diseño, sección 9.5)
    // ------------------------------------------------------------------

    @Test
    void elInsertSigueElOrdenDeMovieCsv() {
        OperationSelector selector = new OperationSelector(new Random(42));
        MovieRegistry registry = new MovieRegistry(List.of(11L, 23L, 46L), Set.of());
        List<Long> inserted = new ArrayList<>();

        for (int step = 0; step < 3; step++) {
            PlannedOperation operation = selector.next(ONLY_INSERT, registry, true).orElseThrow();
            assertFalse(operation.reinsertion());
            registry.markAlive(operation.movieId());
            inserted.add(operation.movieId());
        }

        assertEquals(List.of(11L, 23L, 46L), inserted);
    }

    @Test
    void sinPeliculasVivasUnUpdateOUnDeleteSeConvierteEnInsert() {
        MovieRegistry registry = registryWith(5, 0);

        PlannedOperation fromUpdate = new OperationSelector(new Random(1)).next(ONLY_UPDATE, registry, true)
                .orElseThrow();
        PlannedOperation fromDelete = new OperationSelector(new Random(1)).next(ONLY_DELETE, registry, true)
                .orElseThrow();

        assertEquals(PlannedOperation.insert(1), fromUpdate);
        assertEquals(PlannedOperation.insert(1), fromDelete);
    }

    @Test
    void elUpdateYElDeleteEligenUnaPeliculaViva() {
        OperationSelector selector = new OperationSelector(new Random(42));
        MovieRegistry registry = registryWith(20, 10);

        for (int step = 0; step < 200; step++) {
            PlannedOperation update = selector.next(ONLY_UPDATE, registry, true).orElseThrow();
            PlannedOperation delete = selector.next(ONLY_DELETE, registry, true).orElseThrow();
            assertEquals(OperationType.UPDATE, update.type());
            assertEquals(OperationType.DELETE, delete.type());
            assertEquals(MovieState.ALIVE, registry.stateOf(update.movieId()));
            assertEquals(MovieState.ALIVE, registry.stateOf(delete.movieId()));
        }
    }

    @Test
    void enModoContinuoSinPendientesSeReinsertaUnaBorrada() {
        OperationSelector selector = new OperationSelector(new Random(42));
        MovieRegistry registry = registryWith(4, 4);
        registry.markDeleted(2);
        registry.markDeleted(3);

        PlannedOperation operation = selector.next(ONLY_INSERT, registry, true).orElseThrow();

        assertEquals(OperationType.INSERT, operation.type());
        assertTrue(operation.reinsertion());
        assertTrue(Set.of(2L, 3L).contains(operation.movieId()));
    }

    @Test
    void mientrasQuedenPendientesNoSeReinsertaAutomaticamente() {
        OperationSelector selector = new OperationSelector(new Random(42));
        MovieRegistry registry = registryWith(4, 2);
        registry.markDeleted(1);

        PlannedOperation operation = selector.next(ONLY_INSERT, registry, true).orElseThrow();

        assertEquals(PlannedOperation.insert(3), operation);
    }

    @Test
    void enModoContinuoSinPendientesNiBorradasSeHaceUnUpdate() {
        OperationSelector selector = new OperationSelector(new Random(42));
        MovieRegistry registry = registryWith(4, 4);

        PlannedOperation operation = selector.next(ONLY_INSERT, registry, true).orElseThrow();

        assertEquals(OperationType.UPDATE, operation.type());
    }

    @Test
    void sinModoContinuoNoHayInsertAlAgotarMovieCsv() {
        OperationSelector selector = new OperationSelector(new Random(42));
        MovieRegistry registry = registryWith(4, 4);
        registry.markDeleted(2);

        Optional<PlannedOperation> operation = selector.next(ONLY_INSERT, registry, false);

        assertTrue(operation.isEmpty());
    }

    @Test
    void sinNadaQueHacerNoDevuelveOperacion() {
        OperationSelector selector = new OperationSelector(new Random(42));
        MovieRegistry registry = new MovieRegistry(List.of(), Set.of());

        assertTrue(selector.next(DEFAULT_WEIGHTS, registry, true).isEmpty());
    }

    // ------------------------------------------------------------------
    // Tipo de UPDATE (diseño, sección 9.5)
    // ------------------------------------------------------------------

    @Test
    void sinColeccionNiKeywordsNoSeEligeElUpdateDeCatalogo() {
        OperationSelector selector = new OperationSelector(new Random(42));
        Set<UpdateKind> chosen = EnumSet.noneOf(UpdateKind.class);

        for (int step = 0; step < 500; step++) {
            chosen.add(selector.chooseUpdateKind(NO_LINKS));
        }

        assertEquals(EnumSet.of(UpdateKind.DESCRIPTIVE, UpdateKind.MEASURES, UpdateKind.RELATIONS), chosen);
    }

    @Test
    void conColeccionOKeywordsLosCuatroTiposTienenLaMismaProbabilidad() {
        OperationSelector selector = new OperationSelector(new Random(42));
        CatalogLinks links = new CatalogLinks(10L, List.of());
        Map<UpdateKind, Integer> counts = new EnumMap<>(UpdateKind.class);

        for (int step = 0; step < 20_000; step++) {
            counts.merge(selector.chooseUpdateKind(links), 1, Integer::sum);
        }

        for (UpdateKind kind : UpdateKind.values()) {
            assertEquals(0.25, counts.get(kind) / 20_000.0, 0.02, kind.name());
        }
    }

    @Test
    void conSoloColeccionSeRenombraLaColeccion() {
        OperationSelector selector = new OperationSelector(new Random(42));

        CatalogTarget target = selector.chooseCatalogTarget(new CatalogLinks(10L, List.of()));

        assertEquals(new CatalogTarget(CatalogTable.COLLECTION, 10), target);
    }

    @Test
    void conSoloKeywordsSeRenombraUnaDeEllas() {
        OperationSelector selector = new OperationSelector(new Random(42));
        Set<Long> chosen = new HashSet<>();

        for (int step = 0; step < 200; step++) {
            CatalogTarget target = selector.chooseCatalogTarget(new CatalogLinks(null, List.of(30L, 62L, 99L)));
            assertEquals(CatalogTable.KEYWORD, target.table());
            chosen.add(target.id());
        }

        assertEquals(Set.of(30L, 62L, 99L), chosen);
    }

    @Test
    void conColeccionYKeywordsSeDecideAlCincuentaPorCiento() {
        OperationSelector selector = new OperationSelector(new Random(42));
        CatalogLinks links = new CatalogLinks(10L, List.of(30L, 62L));
        int collections = 0;

        for (int step = 0; step < 10_000; step++) {
            if (selector.chooseCatalogTarget(links).table() == CatalogTable.COLLECTION) {
                collections++;
            }
        }

        assertEquals(0.50, collections / 10_000.0, 0.02);
    }

    @Test
    void elegirObjetivoDeCatalogoSinColeccionNiKeywordsEsUnError() {
        OperationSelector selector = new OperationSelector(new Random(42));

        assertThrows(IllegalArgumentException.class, () -> selector.chooseCatalogTarget(NO_LINKS));
    }

    // ------------------------------------------------------------------
    // Apoyo
    // ------------------------------------------------------------------

    /** Un registro con las películas 1..total, de las que las primeras {@code alive} ya están vivas. */
    private static MovieRegistry registryWith(int total, int alive) {
        List<Long> movieIds = LongStream.rangeClosed(1, total).boxed().toList();
        Set<Long> present = new HashSet<>(movieIds.subList(0, alive));
        return new MovieRegistry(movieIds, present);
    }

    /**
     * Ejecuta la secuencia automática sin base de datos: aplica cada operación
     * al registro, como haría el simulador, y anota lo decidido.
     */
    private static List<String> simulate(long seed, int steps) {
        OperationSelector selector = new OperationSelector(new Random(seed));
        MovieRegistry registry = registryWith(300, 0);
        List<String> sequence = new ArrayList<>();
        for (int step = 0; step < steps; step++) {
            PlannedOperation operation = selector.next(DEFAULT_WEIGHTS, registry, true).orElseThrow();
            String line = operation.type() + (operation.reinsertion() ? "*" : "") + " " + operation.movieId();
            if (operation.type() == OperationType.INSERT) {
                registry.markAlive(operation.movieId());
            } else if (operation.type() == OperationType.DELETE) {
                registry.markDeleted(operation.movieId());
            } else {
                line += " " + selector.chooseUpdateKind(linksOf(operation.movieId()));
            }
            sequence.add(line);
        }
        return sequence;
    }

    /** Colección y keywords inventadas a partir del identificador, para que no dependan del azar. */
    private static CatalogLinks linksOf(long movieId) {
        Long collectionId = movieId % 3 == 0 ? movieId : null;
        List<Long> keywordIds = movieId % 2 == 0 ? List.of(movieId, movieId + 1) : List.of();
        return new CatalogLinks(collectionId, keywordIds);
    }
}
