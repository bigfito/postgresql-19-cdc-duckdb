package com.elastiflix.simulator.simulation;

import com.elastiflix.simulator.dataset.CatalogTable;

/**
 * Lo que renombra un UPDATE de catálogo: una colección o una keyword.
 *
 * @param table {@link CatalogTable#COLLECTION} o {@link CatalogTable#KEYWORD}
 * @param id    clave de la fila que se renombra
 */
public record CatalogTarget(CatalogTable table, long id) {
}
