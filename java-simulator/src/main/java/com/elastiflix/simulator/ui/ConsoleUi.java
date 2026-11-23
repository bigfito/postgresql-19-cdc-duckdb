package com.elastiflix.simulator.ui;

import com.elastiflix.simulator.config.SimulatorConfig;
import com.elastiflix.simulator.error.ErrorCode;
import com.elastiflix.simulator.logging.SimulatorLogging;
import com.elastiflix.simulator.simulation.TransactionRecord;

import com.googlecode.lanterna.TerminalSize;
import com.googlecode.lanterna.graphics.TextGraphics;
import com.googlecode.lanterna.input.KeyStroke;
import com.googlecode.lanterna.input.KeyType;
import com.googlecode.lanterna.screen.Screen;
import com.googlecode.lanterna.screen.TerminalScreen;
import com.googlecode.lanterna.terminal.Terminal;
import com.googlecode.lanterna.terminal.ansi.UnixLikeTerminal.CtrlCBehaviour;
import com.googlecode.lanterna.terminal.ansi.UnixTerminal;

import java.io.Console;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * El hilo de la interfaz de consola (diseño, secciones 9.3, 9.4 y 9.8).
 *
 * <p>Tiene dos modos:</p>
 * <ul>
 *   <li><b>modo de líneas</b>, que es como arranca: no dibuja nada, solo
 *       espera una tecla. Las líneas del log las escribe el propio log;</li>
 *   <li><b>interfaz abierta</b>: dibuja la pantalla, atiende las teclas y
 *       silencia el log en la salida estándar. {@code Q} vuelve al modo de
 *       líneas.</li>
 * </ul>
 *
 * <p>Ninguna tecla detiene el simulador, tampoco {@code Ctrl-C}: la terminal
 * se crea con {@code CtrlCBehaviour.TRAP} y lo recibe como una tecla más. La
 * simulación corre en otro hilo, así que una terminal lenta o cerrada no la
 * frena.</p>
 */
public final class ConsoleUi implements Runnable {

    private static final Logger LOG = Logger.getLogger(ConsoleUi.class.getName());

    /** Pausa entre dos vueltas del bucle: decide lo rápido que responde a una tecla. */
    private static final long LOOP_PAUSE_MILLIS = 40;

    /** Cada cuánto se redibuja la pantalla aunque no se pulse nada. */
    private static final long REPAINT_MILLIS = 250;

    /**
     * Cada cuánto se reescribe la pantalla entera. Lanterna solo envía las
     * celdas que cambian; sin esto, quien se conecta con la interfaz ya
     * abierta la vería a medias.
     */
    private static final long FULL_REFRESH_MILLIS = 2_000;

    /** Espera tras un error de la terminal antes de seguir en modo de líneas. */
    private static final long ERROR_PAUSE_MILLIS = 1_000;

    private final UiContext context;
    private final TransactionListView listView = new TransactionListView();
    private final MainScreenPainter painter;

    private Terminal terminal;
    private TerminalScreen screen;
    private boolean screenOpen;
    private boolean running = true;
    private Dialog dialog;
    private long lastPaintAt;
    private long lastFullRefreshAt;

    /**
     * @param context de dónde se lee lo que se muestra y a quién se dirigen las órdenes
     */
    public ConsoleUi(UiContext context) {
        this.context = context;
        this.painter = new MainScreenPainter(context, listView);
    }

    /** Bucle del hilo de la interfaz. Sin terminal termina enseguida y el simulador sigue en modo de líneas. */
    @Override
    public void run() {
        if (!openTerminal()) {
            return;
        }
        LOG.info("Modo de líneas. Tras `docker compose attach java-simulator`, cualquier tecla abre la interfaz.");
        while (running) {
            try {
                if (screenOpen) {
                    screenStep();
                } else {
                    lineModeStep();
                }
                Thread.sleep(LOOP_PAUSE_MILLIS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                running = false;
            } catch (IOException | RuntimeException e) {
                recoverFromTerminalError(e);
            }
        }
    }

    // ------------------------------------------------------------------
    // Terminal y cambio de modo
    // ------------------------------------------------------------------

    /** @return {@code true} si hay una terminal con la que abrir la interfaz */
    private boolean openTerminal() {
        Console console = System.console();
        if (console == null || !console.isTerminal()) {
            LOG.info("El proceso no tiene terminal: el simulador sigue en modo de líneas, sin interfaz.");
            return false;
        }
        try {
            terminal = new UnixTerminal(System.in, System.out, StandardCharsets.UTF_8, CtrlCBehaviour.TRAP);
            return true;
        } catch (IOException | RuntimeException e) {
            LOG.warning(ErrorCode.TERMINAL.message(String.valueOf(e.getMessage())));
            return false;
        }
    }

    /** En modo de líneas solo se espera la primera tecla. */
    private void lineModeStep() throws IOException {
        KeyStroke key = terminal.pollInput();
        if (key == null) {
            return;
        }
        if (key.getKeyType() == KeyType.EOF) {
            stopWithoutInput();
        } else if (isRealKey(key)) {
            openScreen();
        }
    }

    /** Las respuestas automáticas de la terminal no cuentan como una tecla pulsada. */
    private static boolean isRealKey(KeyStroke key) {
        KeyType type = key.getKeyType();
        return type != KeyType.CursorLocation && type != KeyType.MouseEvent && type != KeyType.Unknown;
    }

    private void stopWithoutInput() {
        LOG.info("La entrada estándar está cerrada: el simulador sigue en modo de líneas, sin interfaz.");
        running = false;
    }

    private void openScreen() throws IOException {
        LOG.info("Interfaz abierta. El log sigue en " + SimulatorConfig.LOG_FILE + ".");
        SimulatorLogging.setConsoleEnabled(false);
        if (screen == null) {
            screen = new TerminalScreen(terminal);
        }
        screen.startScreen();
        screenOpen = true;
        dialog = null;
        listView.followNewest();
        lastPaintAt = 0;
        lastFullRefreshAt = 0;
    }

    private void closeScreen() throws IOException {
        screenOpen = false;
        dialog = null;
        try {
            screen.stopScreen();
        } finally {
            SimulatorLogging.setConsoleEnabled(true);
        }
        LOG.info("Interfaz cerrada: modo de líneas. El simulador sigue en marcha; cualquier tecla vuelve a abrirla.");
    }

    private void recoverFromTerminalError(Exception error) {
        screenOpen = false;
        dialog = null;
        SimulatorLogging.setConsoleEnabled(true);
        LOG.log(Level.WARNING, ErrorCode.TERMINAL.message(String.valueOf(error)));
        try {
            Thread.sleep(ERROR_PAUSE_MILLIS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            running = false;
        }
    }

    // ------------------------------------------------------------------
    // Interfaz abierta
    // ------------------------------------------------------------------

    private void screenStep() throws IOException {
        boolean keyPressed = handlePendingKeys();
        if (!screenOpen) {
            return;
        }
        boolean resized = screen.doResizeIfNecessary() != null;
        long now = System.currentTimeMillis();
        if (keyPressed || resized || now - lastPaintAt >= REPAINT_MILLIS) {
            paint();
            refresh(resized || now - lastFullRefreshAt >= FULL_REFRESH_MILLIS, now);
            lastPaintAt = now;
        }
    }

    /** @return {@code true} si se atendió alguna tecla */
    private boolean handlePendingKeys() throws IOException {
        boolean any = false;
        KeyStroke key = screen.pollInput();
        while (key != null && screenOpen) {
            if (key.getKeyType() == KeyType.EOF) {
                closeScreen();
                stopWithoutInput();
                return true;
            }
            handleKey(key);
            any = true;
            key = screenOpen ? screen.pollInput() : null;
        }
        return any;
    }

    private void handleKey(KeyStroke key) throws IOException {
        if (dialog != null) {
            if (!dialog.handleKey(key)) {
                dialog = null;
                listView.followNewest();
            }
            return;
        }
        // Ctrl-C llega como la letra «c» con Ctrl; ninguna combinación con Ctrl o Alt hace nada.
        if (key.isCtrlDown() || key.isAltDown()) {
            return;
        }
        List<TransactionRecord> recent = context.board().recent();
        switch (key.getKeyType()) {
            case ArrowUp -> listView.moveUp(recent);
            case ArrowDown -> listView.moveDown(recent);
            case Character -> handleCharacter(Character.toLowerCase(key.getCharacter()));
            default -> { }
        }
    }

    private void handleCharacter(char character) throws IOException {
        switch (character) {
            case ' ' -> context.control().togglePause();
            case '+' -> context.control().faster();
            case '-' -> context.control().slower();
            case 'p' -> dialog = new WeightsDialog(context.control());
            case 'm' -> dialog = new ManualDialog(context);
            case 'q' -> closeScreen();
            default -> { }
        }
    }

    private void paint() {
        screen.clear();
        TextGraphics graphics = screen.newTextGraphics();
        TerminalSize size = screen.getTerminalSize();
        screen.setCursorPosition(null);
        if (MainScreenPainter.isTooSmall(size)) {
            // Un diálogo abierto se cierra: no cabría, y sin verlo no se podría salir de él.
            dialog = null;
            painter.paintTooSmall(graphics, size);
            return;
        }
        painter.paint(graphics, size);
        if (dialog != null) {
            dialog.paint(graphics, size);
            screen.setCursorPosition(dialog.cursor());
        }
    }

    private void refresh(boolean complete, long now) throws IOException {
        if (complete) {
            screen.refresh(Screen.RefreshType.COMPLETE);
            lastFullRefreshAt = now;
        } else {
            screen.refresh(Screen.RefreshType.DELTA);
        }
    }
}
