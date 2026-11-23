package com.elastiflix.simulator.simulation;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Conjunto de identificadores del que se puede tomar un elemento por posición
 * en tiempo constante. Sirve para elegir una película al azar con la semilla.
 *
 * <p>El orden interno depende solo de la secuencia de altas y bajas, no del
 * reloj ni de la memoria: con las mismas operaciones, la misma posición
 * devuelve siempre el mismo elemento. De eso depende la reproducibilidad
 * (RF-05).</p>
 */
final class IndexedSet {

    private final List<Long> items = new ArrayList<>();
    private final Map<Long, Integer> positions = new HashMap<>();

    /** Añade el identificador al final; si ya estaba, no hace nada. */
    void add(long id) {
        if (positions.containsKey(id)) {
            return;
        }
        positions.put(id, items.size());
        items.add(id);
    }

    /** Quita el identificador; el último elemento ocupa su hueco. */
    void remove(long id) {
        Integer position = positions.remove(id);
        if (position == null) {
            return;
        }
        int lastPosition = items.size() - 1;
        Long lastItem = items.remove(lastPosition);
        if (position != lastPosition) {
            items.set(position, lastItem);
            positions.put(lastItem, position);
        }
    }

    long get(int position) {
        return items.get(position);
    }

    boolean contains(long id) {
        return positions.containsKey(id);
    }

    int size() {
        return items.size();
    }
}
