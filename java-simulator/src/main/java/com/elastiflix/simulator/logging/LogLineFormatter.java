package com.elastiflix.simulator.logging;

import java.io.PrintWriter;
import java.io.StringWriter;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.logging.Formatter;
import java.util.logging.Level;
import java.util.logging.LogRecord;

/**
 * Da a cada línea del log la forma {@code marca-de-tiempo NIVEL mensaje}
 * (RF-11). La marca de tiempo va en UTC, con milisegundos.
 */
public final class LogLineFormatter extends Formatter {

    private static final DateTimeFormatter TIMESTAMP =
            DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'").withZone(ZoneOffset.UTC);

    @Override
    public String format(LogRecord record) {
        StringBuilder line = new StringBuilder(160);
        line.append(TIMESTAMP.format(Instant.ofEpochMilli(record.getMillis())));
        line.append(' ').append(levelName(record.getLevel()));
        line.append(' ').append(formatMessage(record));
        line.append('\n');
        if (record.getThrown() != null) {
            line.append(stackTrace(record.getThrown()));
        }
        return line.toString();
    }

    /** Traduce los niveles de java.util.logging a los nombres habituales, a cinco caracteres. */
    static String levelName(Level level) {
        int value = level.intValue();
        if (value >= Level.SEVERE.intValue()) {
            return "ERROR";
        }
        if (value >= Level.WARNING.intValue()) {
            return "WARN ";
        }
        if (value >= Level.INFO.intValue()) {
            return "INFO ";
        }
        if (value >= Level.FINE.intValue()) {
            return "DEBUG";
        }
        return "TRACE";
    }

    private static String stackTrace(Throwable thrown) {
        StringWriter text = new StringWriter();
        thrown.printStackTrace(new PrintWriter(text));
        return text.toString();
    }
}
