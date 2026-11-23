package com.elastiflix.simulator.simulation;

/**
 * El cambio que hace un UPDATE descriptivo: un campo y su valor nuevo.
 *
 * @param field    campo que cambia
 * @param newValue valor nuevo; nunca {@code null}
 */
public record DescriptiveChange(DescriptiveField field, String newValue) {
}
