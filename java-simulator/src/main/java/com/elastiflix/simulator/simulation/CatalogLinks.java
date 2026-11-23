package com.elastiflix.simulator.simulation;

import java.util.List;

/**
 * Lo que una película tiene hoy en PostgreSQL y un UPDATE de catálogo puede
 * renombrar: su colección y sus keywords.
 *
 * @param collectionId colección de la película, o {@code null} si no tiene
 * @param keywordIds   sus keywords, en el orden de {@code source_position}
 */
public record CatalogLinks(Long collectionId, List<Long> keywordIds) {

    /** @return {@code true} si la película tiene colección */
    public boolean hasCollection() {
        return collectionId != null;
    }

    /** @return {@code true} si la película tiene al menos una keyword */
    public boolean hasKeywords() {
        return !keywordIds.isEmpty();
    }

    /** @return {@code true} si la película admite un UPDATE de catálogo */
    public boolean allowCatalogUpdate() {
        return hasCollection() || hasKeywords();
    }
}
