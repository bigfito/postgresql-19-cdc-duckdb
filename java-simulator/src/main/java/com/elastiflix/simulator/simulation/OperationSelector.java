package com.elastiflix.simulator.simulation;

import com.elastiflix.simulator.config.Weights;
import com.elastiflix.simulator.dataset.CatalogTable;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.OptionalLong;
import java.util.Random;

/**
 * Decide la siguiente operación automática con los pesos y la semilla (RF-04
 * y RF-05), aplicando las reglas de carga del diseño (sección 9.5).
 *
 * <p>Todas las decisiones salen del mismo generador de números aleatorios, que
 * solo usa el hilo de la simulación. Con la misma semilla y la misma historia,
 * las decisiones son las mismas.</p>
 */
public final class OperationSelector {

    private final Random random;

    /**
     * @param random generador creado con la semilla de la simulación
     */
    public OperationSelector(Random random) {
        this.random = random;
    }

    /**
     * Elige la siguiente operación.
     *
     * <ul>
     *   <li>Los pesos deciden entre INSERT, UPDATE y DELETE.</li>
     *   <li>Un UPDATE o un DELETE sin ninguna película viva se convierte en INSERT.</li>
     *   <li>Un INSERT toma la siguiente película pendiente. Si ya no quedan y el
     *       modo es continuo, reinserta una borrada; si tampoco hay borradas,
     *       hace un UPDATE.</li>
     * </ul>
     *
     * @param weights    pesos vigentes
     * @param registry   situación de cada película
     * @param continuous si el simulador sigue al agotar {@code movie.csv}
     * @return la operación, o vacío si no hay nada que se pueda hacer
     */
    public Optional<PlannedOperation> next(Weights weights, MovieRegistry registry, boolean continuous) {
        OperationType wanted = pickByWeights(weights);
        if (wanted != OperationType.INSERT && registry.aliveCount() == 0) {
            wanted = OperationType.INSERT;
        }
        if (wanted == OperationType.INSERT) {
            return planInsert(registry, continuous);
        }
        long movieId = pickAlive(registry);
        return Optional.of(wanted == OperationType.UPDATE
                ? PlannedOperation.update(movieId)
                : PlannedOperation.delete(movieId));
    }

    private OperationType pickByWeights(Weights weights) {
        int roll = random.nextInt(weights.total());
        if (roll < weights.insert()) {
            return OperationType.INSERT;
        }
        if (roll < weights.insert() + weights.update()) {
            return OperationType.UPDATE;
        }
        return OperationType.DELETE;
    }

    private Optional<PlannedOperation> planInsert(MovieRegistry registry, boolean continuous) {
        OptionalLong pending = registry.nextPending();
        if (pending.isPresent()) {
            return Optional.of(PlannedOperation.insert(pending.getAsLong()));
        }
        if (!continuous) {
            return Optional.empty();
        }
        if (registry.deletedCount() > 0) {
            long movieId = registry.deletedAt(random.nextInt(registry.deletedCount()));
            return Optional.of(PlannedOperation.reinsert(movieId));
        }
        if (registry.aliveCount() > 0) {
            return Optional.of(PlannedOperation.update(pickAlive(registry)));
        }
        return Optional.empty();
    }

    private long pickAlive(MovieRegistry registry) {
        return registry.aliveAt(random.nextInt(registry.aliveCount()));
    }

    /**
     * Elige el tipo de UPDATE, con la misma probabilidad entre los que la
     * película admite. El de catálogo solo entra si tiene colección o keywords.
     *
     * @param links colección y keywords que la película tiene en PostgreSQL
     * @return el tipo elegido
     */
    public UpdateKind chooseUpdateKind(CatalogLinks links) {
        List<UpdateKind> allowed = new ArrayList<>(List.of(
                UpdateKind.DESCRIPTIVE, UpdateKind.MEASURES, UpdateKind.RELATIONS));
        if (links.allowCatalogUpdate()) {
            allowed.add(UpdateKind.CATALOG);
        }
        return allowed.get(random.nextInt(allowed.size()));
    }

    /**
     * Elige qué renombra un UPDATE de catálogo. Si la película tiene colección
     * y keywords, decide entre las dos al 50 %; entre sus keywords, con la
     * misma probabilidad.
     *
     * @param links colección y keywords de la película; debe tener alguna
     * @return la colección o la keyword que se renombra
     * @throws IllegalArgumentException si la película no tiene ni colección ni keywords
     */
    public CatalogTarget chooseCatalogTarget(CatalogLinks links) {
        if (!links.allowCatalogUpdate()) {
            throw new IllegalArgumentException("la película no tiene colección ni keywords");
        }
        boolean collection = links.hasCollection() && (!links.hasKeywords() || random.nextBoolean());
        if (collection) {
            return new CatalogTarget(CatalogTable.COLLECTION, links.collectionId());
        }
        List<Long> keywordIds = links.keywordIds();
        return new CatalogTarget(CatalogTable.KEYWORD, keywordIds.get(random.nextInt(keywordIds.size())));
    }
}
