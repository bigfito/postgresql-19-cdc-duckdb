package com.elastiflix.simulator.ui;

import com.elastiflix.simulator.bronze.BronzeTracker;
import com.elastiflix.simulator.config.Weights;
import com.elastiflix.simulator.simulation.ActivityBoard.Counters;
import com.elastiflix.simulator.simulation.BronzeStatus;
import com.elastiflix.simulator.simulation.MovieRegistry;
import com.elastiflix.simulator.simulation.OperationType;
import com.elastiflix.simulator.simulation.SimulationStatus;
import com.elastiflix.simulator.simulation.TransactionRecord;

import com.googlecode.lanterna.TerminalSize;
import com.googlecode.lanterna.TerminalTextUtils;
import com.googlecode.lanterna.TextColor;
import com.googlecode.lanterna.graphics.TextGraphics;

import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Dibuja la pantalla del simulador con sus cinco zonas fijas (diseño, sección
 * 9.3): cabecera, avance, operaciones, últimas transacciones y detalle, más la
 * barra de teclas al pie.
 *
 * <p>No guarda estado propio: en cada repintado lee la situación actual y lo
 * dibuja todo de nuevo.</p>
 */
final class MainScreenPainter {

    /** Tamaño mínimo de la terminal (diseño, sección 9.2). */
    static final int MIN_COLUMNS = 100;
    static final int MIN_ROWS = 30;

    private static final int HEADER_HEIGHT = 4;
    private static final int SUMMARY_HEIGHT = 6;
    private static final int DETAIL_HEIGHT = 6;
    private static final int KEYS_HEIGHT = 1;

    /** Anchos de las columnas fijas de la lista; el título ocupa lo que sobra. */
    private static final int TIME_WIDTH = 8;
    private static final int OPERATION_WIDTH = 20;
    private static final int MOVIE_ID_WIDTH = 8;
    private static final int ROWS_WIDTH = 9;
    private static final int DURATION_WIDTH = 8;
    private static final int BRONZE_WIDTH = 11;
    private static final int MANUAL_WIDTH = 1;

    private static final DateTimeFormatter CLOCK =
            DateTimeFormatter.ofPattern("HH:mm:ss").withZone(ZoneId.systemDefault());

    private final UiContext context;
    private final TransactionListView listView;

    /**
     * @param context  de dónde se lee lo que se muestra
     * @param listView selección y tramo visible de la lista de transacciones
     */
    MainScreenPainter(UiContext context, TransactionListView listView) {
        this.context = context;
        this.listView = listView;
    }

    /**
     * @param size tamaño de la terminal
     * @return {@code true} si la pantalla no cabe y hay que mostrar el aviso
     */
    static boolean isTooSmall(TerminalSize size) {
        return size.getColumns() < MIN_COLUMNS || size.getRows() < MIN_ROWS;
    }

    /** Dibuja el aviso de terminal pequeña en lugar de la pantalla. */
    void paintTooSmall(TextGraphics graphics, TerminalSize size) {
        int width = size.getColumns();
        String[] lines = {
            "Terminal demasiado pequeña: " + width + "×" + size.getRows(),
            "La interfaz necesita " + MIN_COLUMNS + "×" + MIN_ROWS + " como mínimo.",
            "Amplía la ventana, o pulsa Q para cerrar.",
        };
        int firstRow = Math.max(0, size.getRows() / 2 - 1);
        for (int index = 0; index < lines.length; index++) {
            String line = Draw.fitWithoutPadding(lines[index], width);
            int column = Math.max(0, (width - TerminalTextUtils.getColumnWidth(line)) / 2);
            Draw.text(graphics, column, firstRow + index, line.length(), line, Draw.WARNING);
        }
    }

    /** Dibuja las cinco zonas y la barra de teclas. */
    void paint(TextGraphics graphics, TerminalSize size) {
        int width = size.getColumns();
        int height = size.getRows();
        int summaryTop = HEADER_HEIGHT;
        int listTop = summaryTop + SUMMARY_HEIGHT;
        int detailTop = height - KEYS_HEIGHT - DETAIL_HEIGHT;
        int leftWidth = width / 2;
        List<TransactionRecord> recent = context.board().recent();

        paintHeader(graphics, width);
        paintProgress(graphics, 0, summaryTop, leftWidth);
        paintOperations(graphics, leftWidth, summaryTop, width - leftWidth);
        paintTransactions(graphics, listTop, width, detailTop - listTop, recent);
        paintDetail(graphics, detailTop, width, recent);
        paintKeys(graphics, height - 1, width);
    }

    // ------------------------------------------------------------------
    // Cabecera
    // ------------------------------------------------------------------

    private void paintHeader(TextGraphics graphics, int width) {
        Draw.box(graphics, 0, 0, width, HEADER_HEIGHT, "ElastiFlix Event Simulator");
        int cellWidth = (width - 2) / 4;
        SimulationStatus status = context.engine().status();
        boolean postgresUp = context.session().isConnected();
        BronzeTracker.State bronze = context.tracker().state();

        paintCell(graphics, 0, cellWidth, status.symbol() + " " + status.label(), statusColor(status),
                "semilla " + context.seed());
        paintCell(graphics, 1, cellWidth, "PostgreSQL", Draw.LABEL,
                postgresUp ? "conectado (" + context.session().user() + ")" : "sin conexión",
                postgresUp ? Draw.GOOD : Draw.BAD);
        paintCell(graphics, 2, cellWidth, "Bronze", Draw.LABEL, bronze.label(), bronzeColor(bronze));
        paintCell(graphics, 3, cellWidth, "Intervalo", Draw.LABEL, context.control().delayMillis() + " ms");
    }

    private void paintCell(TextGraphics graphics, int index, int cellWidth, String label, TextColor labelColor,
                           String value) {
        paintCell(graphics, index, cellWidth, label, labelColor, value, Draw.NORMAL);
    }

    /** Una celda de la cabecera: el rótulo arriba, en negrita, y su valor debajo. */
    private void paintCell(TextGraphics graphics, int index, int cellWidth, String label, TextColor labelColor,
                           String value, TextColor valueColor) {
        int column = 2 + index * cellWidth;
        Draw.boldText(graphics, column, 1, cellWidth - 1, label, labelColor);
        Draw.text(graphics, column, 2, cellWidth - 1, value, valueColor);
    }

    private static TextColor statusColor(SimulationStatus status) {
        return switch (status) {
            case RUNNING -> Draw.GOOD;
            case PAUSED -> Draw.WARNING;
            case FINISHED -> Draw.LABEL;
        };
    }

    private static TextColor bronzeColor(BronzeTracker.State state) {
        return switch (state) {
            case CONNECTED -> Draw.GOOD;
            case CONNECTING, DISABLED -> Draw.NORMAL;
            case NO_DATA -> Draw.WARNING;
            case STALLED -> Draw.BAD;
        };
    }

    // ------------------------------------------------------------------
    // Avance y operaciones
    // ------------------------------------------------------------------

    private void paintProgress(TextGraphics graphics, int left, int top, int width) {
        Draw.box(graphics, left, top, width, SUMMARY_HEIGHT, "Avance");
        MovieRegistry registry = context.registry();
        int inner = width - 4;
        int column = left + 2;
        int inserted = registry.insertedCount();
        int total = registry.totalCount();
        double fraction = total == 0 ? 0 : (double) inserted / total;

        Draw.text(graphics, column, top + 1, inner, "Películas insertadas  " + Draw.number(inserted) + " / "
                + Draw.number(total) + " · " + String.format(Locale.US, "%.1f %%", fraction * 100), Draw.NORMAL);
        Draw.text(graphics, column, top + 2, inner, progressBar(fraction, inner), Draw.GOOD);
        Draw.text(graphics, column, top + 3, inner, "Vivas en catalog  " + Draw.number(registry.aliveCount())
                + "     Ritmo  " + String.format(Locale.US, "%.1f tx/s", context.board().transactionsPerSecond()),
                Draw.NORMAL);
        Draw.text(graphics, column, top + 4, inner, "Pendientes  " + Draw.number(registry.pendingCount())
                + "     Borradas  " + Draw.number(registry.deletedCount()), Draw.NORMAL);
    }

    private static String progressBar(double fraction, int width) {
        int filled = (int) Math.round(Math.min(1, Math.max(0, fraction)) * width);
        return "█".repeat(filled) + "░".repeat(width - filled);
    }

    private void paintOperations(TextGraphics graphics, int left, int top, int width) {
        Draw.box(graphics, left, top, width, SUMMARY_HEIGHT, "Operaciones");
        Counters counters = context.board().counters();
        Weights weights = context.control().weights();
        int inner = width - 4;
        int column = left + 2;

        paintCounter(graphics, column, top + 1, inner, OperationType.INSERT, counters.inserts(), weights.insert());
        paintCounter(graphics, column, top + 2, inner, OperationType.UPDATE, counters.updates(), weights.update());
        paintCounter(graphics, column, top + 3, inner, OperationType.DELETE, counters.deletes(), weights.delete());
        Draw.text(graphics, column, top + 4, inner / 2, "Errores  " + Draw.number(counters.errors()),
                counters.errors() > 0 ? Draw.BAD : Draw.NORMAL);
        Draw.text(graphics, column + inner / 2, top + 4, inner - inner / 2,
                "Manuales  " + Draw.number(counters.manual()), Draw.NORMAL);
    }

    private void paintCounter(TextGraphics graphics, int column, int row, int width, OperationType type,
                              long count, int weight) {
        Draw.boldText(graphics, column, row, 7, type.name(), operationColor(type));
        Draw.text(graphics, column + 7, row, width - 7, Draw.right(Draw.number(count), 10) + " · peso " + weight,
                Draw.NORMAL);
    }

    private static TextColor operationColor(OperationType type) {
        return switch (type) {
            case INSERT -> Draw.GOOD;
            case UPDATE -> Draw.WARNING;
            case DELETE -> Draw.BAD;
        };
    }

    // ------------------------------------------------------------------
    // Últimas transacciones
    // ------------------------------------------------------------------

    private void paintTransactions(TextGraphics graphics, int top, int width, int height,
                                   List<TransactionRecord> recent) {
        Draw.box(graphics, 0, top, width, height, "Últimas transacciones");
        int inner = width - 2;
        int titleWidth = titleWidth(inner);
        Draw.boldText(graphics, 1, top + 1, inner, listRow("", "Hora", "Operación", "movie_id", "Título",
                "Filas", "Duración", "Bronze", "M", titleWidth), Draw.LABEL);

        int visibleRows = height - 3;
        int first = listView.firstVisible(recent, visibleRows);
        int selected = listView.selectedIndex(recent);
        for (int line = 0; line < visibleRows && first + line < recent.size(); line++) {
            TransactionRecord record = recent.get(first + line);
            paintTransaction(graphics, top + 2 + line, inner, titleWidth, record, first + line == selected);
        }
    }

    /** El título se queda con las columnas que dejan libres las demás. */
    private static int titleWidth(int inner) {
        int fixed = 2 + TIME_WIDTH + OPERATION_WIDTH + MOVIE_ID_WIDTH + ROWS_WIDTH + DURATION_WIDTH
                + BRONZE_WIDTH + MANUAL_WIDTH;
        int separators = 7;
        return Math.max(4, inner - fixed - separators);
    }

    private static String listRow(String mark, String time, String operation, String movieId, String title,
                                  String rows, String duration, String bronze, String manual, int titleWidth) {
        return Draw.fit(mark, 2)
                + Draw.fit(time, TIME_WIDTH) + " "
                + Draw.fit(operation, OPERATION_WIDTH) + " "
                + Draw.right(movieId, MOVIE_ID_WIDTH) + " "
                + Draw.fit(title, titleWidth) + " "
                + Draw.right(rows, ROWS_WIDTH) + " "
                + Draw.right(duration, DURATION_WIDTH) + " "
                + Draw.fit(bronze, BRONZE_WIDTH) + " "
                + Draw.fit(manual, MANUAL_WIDTH);
    }

    private void paintTransaction(TextGraphics graphics, int row, int inner, int titleWidth,
                                  TransactionRecord record, boolean selected) {
        String line = listRow(selected ? "▸" : "",
                CLOCK.format(record.finishedAt()),
                record.operationLabel(),
                String.valueOf(record.movieId()),
                record.title(),
                record.failed() ? "ERROR" : rowsText(record.totalRows()),
                record.failed() ? "" : record.durationMillis() + " ms",
                bronzeText(record),
                record.manual() ? "M" : "",
                titleWidth);
        if (selected) {
            Draw.boldText(graphics, 1, row, inner, line, rowColor(record));
        } else {
            Draw.text(graphics, 1, row, inner, line, rowColor(record));
        }
    }

    private static String rowsText(int rows) {
        return rows == 1 ? "1 fila" : rows + " filas";
    }

    private static TextColor rowColor(TransactionRecord record) {
        return record.failed() ? Draw.BAD : operationColor(record.type());
    }

    /** Estado en Bronze: «… pendiente», «✓» con el tiempo, «demorada» o «sin datos». */
    private String bronzeText(TransactionRecord record) {
        TransactionRecord.BronzeTracking bronze = record.bronze();
        if (bronze.status() == BronzeStatus.ARRIVED) {
            return "✓ " + Math.max(1, Math.round(bronze.delayMillis() / 1000.0)) + " s";
        }
        if (bronze.status() == BronzeStatus.LATE) {
            return "demorada";
        }
        if (bronze.status() == BronzeStatus.NOT_TRACKED) {
            return "—";
        }
        return context.tracker().state() == BronzeTracker.State.NO_DATA ? "sin datos" : "… pendiente";
    }

    // ------------------------------------------------------------------
    // Detalle
    // ------------------------------------------------------------------

    private void paintDetail(TextGraphics graphics, int top, int width, List<TransactionRecord> recent) {
        Draw.box(graphics, 0, top, width, DETAIL_HEIGHT, "Detalle");
        int inner = width - 4;
        if (recent.isEmpty()) {
            Draw.text(graphics, 2, top + 1, inner, "Aún no hay transacciones.", Draw.NORMAL);
            return;
        }
        TransactionRecord record = recent.get(listView.selectedIndex(recent));
        Draw.boldText(graphics, 2, top + 1, inner, detailTitle(record), rowColor(record));
        List<String> lines = new ArrayList<>(wrap(breakdown(record.rowsByTable()), inner));
        int breakdownLines = lines.size();
        lines.addAll(wrap(record.detail(), inner));
        for (int index = 0; index < DETAIL_HEIGHT - 3 && index < lines.size(); index++) {
            boolean cut = index == DETAIL_HEIGHT - 4 && lines.size() > DETAIL_HEIGHT - 3;
            boolean isReason = record.failed() && index >= breakdownLines;
            Draw.text(graphics, 2, top + 2 + index, inner, cut ? lines.get(index) + "…" : lines.get(index),
                    isReason ? Draw.BAD : Draw.NORMAL);
        }
    }

    /** Parte un texto en líneas que caben en el ancho; un texto vacío no ocupa ninguna. */
    private static List<String> wrap(String text, int width) {
        if (text.isBlank()) {
            return List.of();
        }
        return TerminalTextUtils.getWordWrappedText(width, text.replace('\n', ' '));
    }

    private static String detailTitle(TransactionRecord record) {
        return "#" + record.sequence() + "  " + record.operationLabel() + " " + record.movieId()
                + " · " + record.title()
                + (record.manual() ? " · manual" : "")
                + (record.failed() ? " · REVERTIDA" : "");
    }

    /** Por ejemplo: {@code movie 1 · movie_genre 3 · movie_keyword 16}. */
    private static String breakdown(Map<String, Integer> rowsByTable) {
        return rowsByTable.entrySet().stream()
                .map(entry -> entry.getKey() + " " + entry.getValue())
                .collect(Collectors.joining(" · "));
    }

    // ------------------------------------------------------------------
    // Barra de teclas
    // ------------------------------------------------------------------

    private void paintKeys(TextGraphics graphics, int row, int width) {
        String action = context.control().isPaused() ? "reanudar" : "pausar";
        String keys = " Espacio " + action + " │ + / - velocidad │ P pesos │ M manual │ ↑ ↓ recorrer │ Q salir";
        Draw.text(graphics, 0, row, width, keys, Draw.FRAME);
    }
}
