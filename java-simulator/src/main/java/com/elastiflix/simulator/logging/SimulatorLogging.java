package com.elastiflix.simulator.logging;

import java.io.FileDescriptor;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.logging.FileHandler;
import java.util.logging.Handler;
import java.util.logging.Level;
import java.util.logging.LogRecord;
import java.util.logging.Logger;

/**
 * Configura el log del simulador con java.util.logging, que viene con el JDK.
 *
 * <p>Cada línea va a dos destinos (diseño, sección 9.8):</p>
 * <ul>
 *   <li>la salida estándar, que es el modo de líneas y lo que muestra
 *       {@code docker compose logs}; se silencia mientras la interfaz está
 *       abierta, para no escribir encima de la pantalla;</li>
 *   <li>un archivo dentro del contenedor, que no se silencia nunca.</li>
 * </ul>
 */
public final class SimulatorLogging {

    /** Tamaño a partir del cual el archivo de log vuelve a empezar. */
    private static final int LOG_FILE_LIMIT_BYTES = 20 * 1024 * 1024;

    private static final ConsoleLineHandler CONSOLE = new ConsoleLineHandler();

    private static volatile Path logFilePath;

    private SimulatorLogging() {
    }

    /**
     * Sustituye la configuración por defecto del JDK por la del simulador.
     *
     * @param logFile archivo donde se copia el log; si no se puede abrir, el
     *                simulador avisa y sigue solo con la salida estándar
     */
    public static void configure(Path logFile) {
        Logger root = Logger.getLogger("");
        for (Handler handler : root.getHandlers()) {
            root.removeHandler(handler);
        }
        root.setLevel(Level.INFO);
        root.addHandler(CONSOLE);
        addFileHandler(root, logFile);
        logFilePath = logFile;
    }

    /**
     * Escribe una línea mientras la JVM se está deteniendo.
     *
     * <p>En ese momento java.util.logging ya está cerrando sus destinos y
     * descarta lo que se le envía. Por eso esta línea va directa a la salida
     * estándar y al archivo, sin pasar por el log.</p>
     *
     * @param message texto de la línea, con nivel INFO
     */
    public static void logDuringShutdown(String message) {
        LogRecord record = new LogRecord(Level.INFO, message);
        CONSOLE.setEnabled(true);
        CONSOLE.publish(record);
        Path file = logFilePath;
        if (file == null) {
            return;
        }
        try {
            Files.writeString(file, new LogLineFormatter().format(record), StandardCharsets.UTF_8,
                    StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        } catch (IOException e) {
            // La línea ya salió por la salida estándar; no hay otro sitio donde avisar.
            CONSOLE.publish(new LogRecord(Level.WARNING, "No se pudo escribir en " + file + ": " + e.getMessage()));
        }
    }

    /**
     * Activa o silencia la salida estándar. La interfaz la silencia al abrirse
     * y la reactiva al cerrarse.
     *
     * @param enabled {@code true} para escribir las líneas en la salida estándar
     */
    public static void setConsoleEnabled(boolean enabled) {
        CONSOLE.setEnabled(enabled);
    }

    private static void addFileHandler(Logger root, Path logFile) {
        try {
            // Con un solo archivo y un límite, al llenarse se vacía y vuelve a empezar.
            FileHandler fileHandler = new FileHandler(logFile.toString(), LOG_FILE_LIMIT_BYTES, 1, true);
            fileHandler.setEncoding(StandardCharsets.UTF_8.name());
            fileHandler.setFormatter(new LogLineFormatter());
            root.addHandler(fileHandler);
        } catch (IOException | SecurityException e) {
            root.warning("No se pudo abrir el archivo de log " + logFile + ": " + e.getMessage()
                    + ". El log sigue solo en la salida estándar.");
        }
    }

    /** Escribe cada línea en la salida estándar, en UTF-8, mientras esté activo. */
    private static final class ConsoleLineHandler extends Handler {

        private final PrintStream out =
                new PrintStream(new FileOutputStream(FileDescriptor.out), true, StandardCharsets.UTF_8);
        private boolean enabled = true;

        ConsoleLineHandler() {
            setFormatter(new LogLineFormatter());
        }

        synchronized void setEnabled(boolean enabled) {
            this.enabled = enabled;
        }

        @Override
        public synchronized void publish(LogRecord record) {
            if (enabled && isLoggable(record)) {
                out.print(getFormatter().format(record));
                out.flush();
            }
        }

        @Override
        public synchronized void flush() {
            out.flush();
        }

        @Override
        public void close() {
            flush();
        }
    }
}
