package com.elastiflix.simulator.db;

import com.elastiflix.simulator.dataset.Dataset;
import com.elastiflix.simulator.simulation.CatalogLinks;
import com.elastiflix.simulator.simulation.CatalogTarget;
import com.elastiflix.simulator.simulation.TransactionOutcome;
import com.elastiflix.simulator.simulation.UpdateKind;

import java.sql.SQLException;
import java.util.Random;

/**
 * Punto único desde el que la simulación ejecuta sus transacciones sobre
 * PostgreSQL. Reúne el alta, los cuatro UPDATE y el DELETE de una película.
 *
 * <p>Cada método es una transacción completa: o queda confirmada, o lanza una
 * excepción y no deja nada escrito.</p>
 */
public final class MovieOperations {

    private final PostgresSession session;
    private final DatabaseStateReader stateReader;
    private final MovieInserter inserter;
    private final MovieUpdater updater;
    private final MovieRelationUpdater relationUpdater;
    private final MovieDeleter deleter;

    /**
     * @param session      conexión con PostgreSQL
     * @param dataset      dataset en memoria
     * @param insertedKeys claves de catálogos y entidades que ya están en PostgreSQL
     * @param random       generador de la simulación, del que salen los valores nuevos
     */
    public MovieOperations(PostgresSession session, Dataset dataset, InsertedKeys insertedKeys, Random random) {
        TransactionRunner transactions = new TransactionRunner(session);
        this.session = session;
        this.stateReader = new DatabaseStateReader(session);
        this.inserter = new MovieInserter(dataset, transactions, insertedKeys);
        this.updater = new MovieUpdater(dataset, transactions, random);
        this.relationUpdater = new MovieRelationUpdater(transactions, random);
        this.deleter = new MovieDeleter(transactions);
    }

    /**
     * Alta o reinserción de una película, con sus catálogos, entidades y relaciones.
     *
     * @param movieId película del dataset
     * @return lo que dejó la transacción
     * @throws SQLException si PostgreSQL rechaza algún dato
     */
    public TransactionOutcome insert(long movieId) throws SQLException {
        return inserter.insert(movieId);
    }

    /**
     * UPDATE descriptivo, de medidas o de relaciones.
     *
     * @param movieId película viva
     * @param kind    tipo de UPDATE; el de catálogo usa {@link #updateCatalog}
     * @return lo que dejó la transacción
     * @throws SQLException si PostgreSQL rechaza el cambio
     */
    public TransactionOutcome update(long movieId, UpdateKind kind) throws SQLException {
        return switch (kind) {
            case DESCRIPTIVE -> updater.updateDescriptive(movieId);
            case MEASURES -> updater.updateMeasures(movieId);
            case RELATIONS -> relationUpdater.update(movieId);
            case CATALOG -> throw new IllegalArgumentException("el UPDATE de catálogo necesita su objetivo");
        };
    }

    /**
     * UPDATE de catálogo: renombra la colección o la keyword indicada.
     *
     * @param movieId película viva a la que pertenece
     * @param target  colección o keyword que se renombra
     * @return lo que dejó la transacción
     * @throws SQLException si PostgreSQL rechaza el cambio
     */
    public TransactionOutcome updateCatalog(long movieId, CatalogTarget target) throws SQLException {
        return updater.updateCatalog(movieId, target);
    }

    /**
     * DELETE de una película; sus relaciones caen por cascada.
     *
     * @param movieId película viva
     * @return lo que dejó la transacción
     * @throws SQLException si PostgreSQL rechaza el borrado
     */
    public TransactionOutcome delete(long movieId) throws SQLException {
        return deleter.delete(movieId);
    }

    /**
     * @param movieId película viva
     * @return la colección y las keywords que tiene ahora en PostgreSQL
     * @throws SQLException si la consulta falla
     */
    public CatalogLinks readCatalogLinks(long movieId) throws SQLException {
        return stateReader.readCatalogLinks(movieId);
    }

    /** Descarta la conexión tras un fallo; la siguiente operación abrirá otra. */
    public void discardConnection() {
        session.discard();
    }
}
