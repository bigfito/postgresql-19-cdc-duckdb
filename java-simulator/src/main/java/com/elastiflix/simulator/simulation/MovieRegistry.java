package com.elastiflix.simulator.simulation;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.OptionalLong;
import java.util.Set;

/**
 * Lleva la cuenta de en qué situación está cada película del dataset:
 * pendiente, viva o borrada.
 *
 * <p>Lo modifica el hilo de la simulación y lo leen la interfaz y el log, por
 * eso sus métodos están sincronizados.</p>
 */
public final class MovieRegistry {

    private final List<Long> movieIdsInOrder;
    private final Map<Long, MovieState> states = new HashMap<>();
    private final IndexedSet alive = new IndexedSet();
    private final IndexedSet deleted = new IndexedSet();
    private final Set<Long> everInserted = new HashSet<>();
    private int nextPendingIndex;
    private int pendingCount;

    /**
     * Reconstruye la situación de cada película a partir de lo que ya hay en
     * PostgreSQL (RF-13; diseño, sección 9.5): continúa después de la última
     * película de {@code movie.csv} presente en la base. Las posteriores quedan
     * pendientes; las anteriores que faltan cuentan como borradas.
     *
     * @param movieIdsInOrder   los {@code movie_id} en el orden de {@code movie.csv}
     * @param presentInDatabase los {@code movie_id} que ya están en {@code catalog.movie}
     */
    public MovieRegistry(List<Long> movieIdsInOrder, Set<Long> presentInDatabase) {
        this.movieIdsInOrder = List.copyOf(movieIdsInOrder);
        int lastPresentIndex = lastPresentIndex(presentInDatabase);
        for (int index = 0; index < this.movieIdsInOrder.size(); index++) {
            long movieId = this.movieIdsInOrder.get(index);
            if (index > lastPresentIndex) {
                states.put(movieId, MovieState.PENDING);
                pendingCount++;
            } else if (presentInDatabase.contains(movieId)) {
                putAlive(movieId);
            } else {
                putDeleted(movieId);
            }
        }
        nextPendingIndex = lastPresentIndex + 1;
    }

    private int lastPresentIndex(Set<Long> presentInDatabase) {
        for (int index = movieIdsInOrder.size() - 1; index >= 0; index--) {
            if (presentInDatabase.contains(movieIdsInOrder.get(index))) {
                return index;
            }
        }
        return -1;
    }

    /**
     * @return la primera película pendiente en el orden de {@code movie.csv},
     *         o vacío si ya no queda ninguna
     */
    public synchronized OptionalLong nextPending() {
        while (nextPendingIndex < movieIdsInOrder.size()) {
            long movieId = movieIdsInOrder.get(nextPendingIndex);
            if (states.get(movieId) == MovieState.PENDING) {
                return OptionalLong.of(movieId);
            }
            // Ya no está pendiente: se insertó a mano fuera de orden, o su alta falló.
            nextPendingIndex++;
        }
        return OptionalLong.empty();
    }

    /**
     * Registra que la película está en PostgreSQL: se insertó o se reinsertó.
     *
     * @param movieId identificador de la película
     */
    public synchronized void markAlive(long movieId) {
        leaveCurrentState(movieId);
        putAlive(movieId);
    }

    /**
     * Registra que la película no está en PostgreSQL y se puede reinsertar: se
     * borró, o su alta falló por un dato inconsistente (RF-12).
     *
     * @param movieId identificador de la película
     */
    public synchronized void markDeleted(long movieId) {
        leaveCurrentState(movieId);
        putDeleted(movieId);
    }

    private void leaveCurrentState(long movieId) {
        MovieState current = states.get(movieId);
        if (current == MovieState.PENDING) {
            pendingCount--;
        } else if (current == MovieState.ALIVE) {
            alive.remove(movieId);
        } else if (current == MovieState.DELETED) {
            deleted.remove(movieId);
        }
    }

    private void putAlive(long movieId) {
        states.put(movieId, MovieState.ALIVE);
        alive.add(movieId);
        everInserted.add(movieId);
    }

    private void putDeleted(long movieId) {
        states.put(movieId, MovieState.DELETED);
        deleted.add(movieId);
    }

    /**
     * @param movieId identificador de la película
     * @return su situación, o {@code null} si el dataset no la contiene
     */
    public synchronized MovieState stateOf(long movieId) {
        return states.get(movieId);
    }

    /**
     * @param position posición entre 0 y {@link #aliveCount()} menos 1
     * @return la película viva que ocupa esa posición
     */
    public synchronized long aliveAt(int position) {
        return alive.get(position);
    }

    /**
     * @param position posición entre 0 y {@link #deletedCount()} menos 1
     * @return la película borrada que ocupa esa posición
     */
    public synchronized long deletedAt(int position) {
        return deleted.get(position);
    }

    /** @return cuántas películas tiene el dataset */
    public synchronized int totalCount() {
        return movieIdsInOrder.size();
    }

    /** @return cuántas películas siguen pendientes de su primera alta */
    public synchronized int pendingCount() {
        return pendingCount;
    }

    /** @return cuántas películas están ahora en {@code catalog.movie} */
    public synchronized int aliveCount() {
        return alive.size();
    }

    /** @return cuántas películas se pueden reinsertar */
    public synchronized int deletedCount() {
        return deleted.size();
    }

    /** @return cuántas películas distintas han llegado a estar en PostgreSQL */
    public synchronized int insertedCount() {
        return everInserted.size();
    }
}
