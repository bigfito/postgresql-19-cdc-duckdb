package com.elastiflix.simulator.ui;

import com.elastiflix.simulator.simulation.CatalogLinks;
import com.elastiflix.simulator.simulation.ManualAction;
import com.elastiflix.simulator.simulation.MovieState;

import com.googlecode.lanterna.TerminalPosition;
import com.googlecode.lanterna.TerminalSize;
import com.googlecode.lanterna.graphics.TextGraphics;
import com.googlecode.lanterna.input.KeyStroke;
import com.googlecode.lanterna.input.KeyType;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.OptionalLong;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.logging.Logger;

/**
 * Diálogo de operación manual (tecla {@code M}; RF-08). Tiene dos pasos:
 *
 * <ol>
 *   <li>elegir la película, escribiendo su {@code movie_id} o parte del título;</li>
 *   <li>elegir la operación, entre las que esa película admite en su situación.</li>
 * </ol>
 *
 * <p>El diálogo no ejecuta nada: deja la petición al hilo de la simulación,
 * que la ejecuta como una transacción normal.</p>
 */
final class ManualDialog implements Dialog {

    private static final Logger LOG = Logger.getLogger(ManualDialog.class.getName());

    private static final int WIDTH = 84;
    private static final int HEIGHT = 16;
    private static final int MAX_MATCHES = 8;
    private static final int MAX_QUERY_LENGTH = 40;
    private static final String PROMPT = "Película (movie_id o parte del título): ";
    private static final long LINKS_TIMEOUT_MILLIS = 2_000;

    private enum Step { CHOOSE_MOVIE, CHOOSE_ACTION }

    private final UiContext context;
    private final StringBuilder query = new StringBuilder();
    private Step step = Step.CHOOSE_MOVIE;
    private List<Long> matches = List.of();
    private int selectedMatch;
    private long chosenMovieId;
    private List<ManualAction> actions = List.of();
    private int selectedAction;
    private String notice = "";
    private TerminalPosition cursor;

    /**
     * @param context dataset para buscar, situación de cada película y el hilo
     *                de la simulación al que se le pide la operación
     */
    ManualDialog(UiContext context) {
        this.context = context;
    }

    // ------------------------------------------------------------------
    // Teclas
    // ------------------------------------------------------------------

    @Override
    public boolean handleKey(KeyStroke key) {
        return step == Step.CHOOSE_MOVIE ? handleMovieKey(key) : handleActionKey(key);
    }

    private boolean handleMovieKey(KeyStroke key) {
        switch (key.getKeyType()) {
            case Escape -> {
                return false;
            }
            case Enter -> {
                return confirmMovie();
            }
            case ArrowDown -> selectedMatch = Math.min(selectedMatch + 1, Math.max(0, matches.size() - 1));
            case ArrowUp -> selectedMatch = Math.max(selectedMatch - 1, 0);
            case Backspace -> {
                if (!query.isEmpty()) {
                    query.setLength(query.length() - 1);
                    search();
                }
            }
            case Character -> {
                if (query.length() < MAX_QUERY_LENGTH && !key.isCtrlDown() && !key.isAltDown()) {
                    query.append(key.getCharacter());
                    search();
                }
            }
            default -> { }
        }
        return true;
    }

    /**
     * Con el campo vacío, Enter pide el INSERT de la siguiente película
     * pendiente. Con texto, pasa a elegir la operación sobre la película marcada.
     *
     * @return {@code true} si el diálogo sigue abierto
     */
    private boolean confirmMovie() {
        if (query.isEmpty()) {
            if (context.registry().nextPending().isEmpty()) {
                notice = "No quedan películas pendientes de alta.";
                return true;
            }
            context.engine().submitManual(ManualAction.INSERT_NEXT, 0);
            return false;
        }
        if (matches.isEmpty()) {
            notice = "Ninguna película coincide con la búsqueda.";
            return true;
        }
        chosenMovieId = matches.get(selectedMatch);
        actions = actionsFor(chosenMovieId);
        selectedAction = 0;
        step = Step.CHOOSE_ACTION;
        return true;
    }

    private boolean handleActionKey(KeyStroke key) {
        switch (key.getKeyType()) {
            case Escape -> {
                step = Step.CHOOSE_MOVIE;
                notice = "";
            }
            case ArrowDown -> selectedAction = Math.min(selectedAction + 1, actions.size() - 1);
            case ArrowUp -> selectedAction = Math.max(selectedAction - 1, 0);
            case Enter -> {
                context.engine().submitManual(actions.get(selectedAction), chosenMovieId);
                return false;
            }
            default -> { }
        }
        return true;
    }

    // ------------------------------------------------------------------
    // Búsqueda y operaciones disponibles
    // ------------------------------------------------------------------

    /** Busca por {@code movie_id} si el texto son dígitos, y siempre por título. */
    private void search() {
        String text = query.toString().strip();
        List<Long> found = new ArrayList<>();
        if (!text.isEmpty()) {
            addIdMatches(text, found);
            addTitleMatches(text.toLowerCase(Locale.ROOT), found);
        }
        matches = found;
        selectedMatch = 0;
        notice = "";
    }

    /** Primero el identificador exacto y después los que empiezan por esos dígitos. */
    private void addIdMatches(String text, List<Long> found) {
        if (!text.chars().allMatch(Character::isDigit) || text.length() > 18) {
            return;
        }
        long exactId = Long.parseLong(text);
        if (context.dataset().hasMovie(exactId)) {
            found.add(exactId);
        }
        for (long movieId : context.dataset().movieIds()) {
            if (found.size() >= MAX_MATCHES) {
                return;
            }
            if (movieId != exactId && String.valueOf(movieId).startsWith(text)) {
                found.add(movieId);
            }
        }
    }

    private void addTitleMatches(String lowerCaseText, List<Long> found) {
        for (long movieId : context.dataset().movieIds()) {
            if (found.size() >= MAX_MATCHES) {
                return;
            }
            boolean matchesTitle = context.dataset().title(movieId).toLowerCase(Locale.ROOT).contains(lowerCaseText);
            if (matchesTitle && !found.contains(movieId)) {
                found.add(movieId);
            }
        }
    }

    /** Las operaciones que la película admite según su situación (diseño, sección 9.3). */
    private List<ManualAction> actionsFor(long movieId) {
        MovieState state = context.registry().stateOf(movieId);
        if (state == MovieState.PENDING) {
            return List.of(ManualAction.INSERT);
        }
        if (state == MovieState.DELETED) {
            return List.of(ManualAction.REINSERT);
        }
        List<ManualAction> available = new ArrayList<>(List.of(
                ManualAction.UPDATE_DESCRIPTIVE, ManualAction.UPDATE_MEASURES, ManualAction.UPDATE_RELATIONS));
        if (allowsCatalogUpdate(movieId)) {
            available.add(ManualAction.UPDATE_CATALOG);
        }
        available.add(ManualAction.DELETE);
        return available;
    }

    /** El UPDATE de catálogo solo se ofrece si la película tiene colección o keywords. */
    private boolean allowsCatalogUpdate(long movieId) {
        try {
            CatalogLinks links = context.engine().askCatalogLinks(movieId)
                    .get(LINKS_TIMEOUT_MILLIS, TimeUnit.MILLISECONDS);
            return links.allowCatalogUpdate();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } catch (ExecutionException | TimeoutException e) {
            LOG.warning("No se pudo comprobar si la película " + movieId + " admite UPDATE de catálogo: " + e);
        }
        notice = "No se pudo comprobar si admite UPDATE de catálogo.";
        return false;
    }

    // ------------------------------------------------------------------
    // Dibujo
    // ------------------------------------------------------------------

    @Override
    public void paint(TextGraphics graphics, TerminalSize size) {
        int left = Math.max(0, (size.getColumns() - WIDTH) / 2);
        int top = Math.max(0, (size.getRows() - HEIGHT) / 2);
        Draw.clear(graphics, left, top, WIDTH, HEIGHT);
        Draw.box(graphics, left, top, WIDTH, HEIGHT, "Operación manual");
        if (step == Step.CHOOSE_MOVIE) {
            paintMovieStep(graphics, left + 2, top, WIDTH - 4);
        } else {
            paintActionStep(graphics, left + 2, top, WIDTH - 4);
        }
        Draw.text(graphics, left + 2, top + HEIGHT - 3, WIDTH - 4, notice, Draw.WARNING);
    }

    private void paintMovieStep(TextGraphics graphics, int column, int top, int inner) {
        Draw.text(graphics, column, top + 2, inner, PROMPT + query, Draw.LABEL);
        for (int index = 0; index < matches.size(); index++) {
            long movieId = matches.get(index);
            boolean selected = index == selectedMatch;
            Draw.text(graphics, column, top + 4 + index, inner, movieLine(selected, movieId, inner),
                    selected ? Draw.LABEL : Draw.NORMAL);
        }
        if (query.isEmpty()) {
            Draw.text(graphics, column, top + 4, inner, nextPendingHint(), Draw.NORMAL);
        }
        Draw.text(graphics, column, top + HEIGHT - 2, inner, "↑ ↓ elige · Enter continúa · Esc cancela", Draw.FRAME);
        cursor = new TerminalPosition(column + PROMPT.length() + query.length(), top + 2);
    }

    private String nextPendingHint() {
        OptionalLong pending = context.registry().nextPending();
        if (pending.isEmpty()) {
            return "No quedan películas pendientes. Escribe para buscar una viva o una borrada.";
        }
        long movieId = pending.getAsLong();
        return "Enter con el campo vacío: INSERT de la siguiente pendiente, " + movieId + " · "
                + context.dataset().title(movieId);
    }

    private String movieLine(boolean selected, long movieId, int inner) {
        MovieState state = context.registry().stateOf(movieId);
        String stateLabel = state == null ? "" : state.label();
        int titleWidth = inner - 2 - 9 - 10;
        return (selected ? "▸ " : "  ") + Draw.right(String.valueOf(movieId), 8) + " "
                + Draw.fit(context.dataset().title(movieId), titleWidth) + " " + Draw.fit(stateLabel, 9);
    }

    private void paintActionStep(TextGraphics graphics, int column, int top, int inner) {
        MovieState state = context.registry().stateOf(chosenMovieId);
        Draw.text(graphics, column, top + 2, inner, "Película " + chosenMovieId + " · "
                + context.dataset().title(chosenMovieId) + " · " + (state == null ? "" : state.label()), Draw.LABEL);
        for (int index = 0; index < actions.size(); index++) {
            boolean selected = index == selectedAction;
            Draw.text(graphics, column, top + 4 + index, inner,
                    (selected ? "▸ " : "  ") + actions.get(index).label(), selected ? Draw.LABEL : Draw.NORMAL);
        }
        Draw.text(graphics, column, top + HEIGHT - 2, inner, "↑ ↓ elige · Enter ejecuta · Esc vuelve", Draw.FRAME);
        cursor = null;
    }

    @Override
    public TerminalPosition cursor() {
        return cursor;
    }
}
