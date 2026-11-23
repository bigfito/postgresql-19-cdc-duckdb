package com.elastiflix.simulator.ui;

import com.googlecode.lanterna.SGR;
import com.googlecode.lanterna.TerminalTextUtils;
import com.googlecode.lanterna.TextColor;
import com.googlecode.lanterna.graphics.TextGraphics;

import java.util.Locale;

/**
 * Utilidades de dibujo compartidas por la pantalla y los diálogos: cajas con
 * título, texto ajustado a un ancho y formato de números.
 */
final class Draw {

    static final TextColor NORMAL = TextColor.ANSI.DEFAULT;
    static final TextColor FRAME = TextColor.ANSI.CYAN;
    static final TextColor LABEL = TextColor.ANSI.WHITE;
    static final TextColor GOOD = TextColor.ANSI.GREEN;
    static final TextColor WARNING = TextColor.ANSI.YELLOW;
    static final TextColor BAD = TextColor.ANSI.RED;

    private Draw() {
    }

    /**
     * Dibuja una caja con su título en el borde superior.
     *
     * @param graphics lienzo de la pantalla
     * @param left     columna de la esquina superior izquierda
     * @param top      fila de la esquina superior izquierda
     * @param width    ancho total, bordes incluidos
     * @param height   alto total, bordes incluidos
     * @param title    título de la zona
     */
    static void box(TextGraphics graphics, int left, int top, int width, int height, String title) {
        graphics.setForegroundColor(FRAME);
        String horizontal = "─".repeat(Math.max(0, width - 2));
        graphics.putString(left, top, "┌" + horizontal + "┐");
        graphics.putString(left, top + height - 1, "└" + horizontal + "┘");
        for (int row = top + 1; row < top + height - 1; row++) {
            graphics.putString(left, row, "│");
            graphics.putString(left + width - 1, row, "│");
        }
        graphics.putString(left + 2, top, " " + fitWithoutPadding(title, width - 6) + " ", SGR.BOLD);
        graphics.setForegroundColor(NORMAL);
    }

    /** Borra el interior y el borde de un rectángulo, para dibujar un diálogo encima de la pantalla. */
    static void clear(TextGraphics graphics, int left, int top, int width, int height) {
        graphics.setForegroundColor(NORMAL);
        String blank = " ".repeat(width);
        for (int row = top; row < top + height; row++) {
            graphics.putString(left, row, blank);
        }
    }

    /**
     * Escribe un texto ocupando exactamente {@code width} columnas: lo recorta
     * con puntos suspensivos si no cabe y lo rellena con espacios si sobra.
     */
    static void text(TextGraphics graphics, int column, int row, int width, String text, TextColor color) {
        graphics.setForegroundColor(color);
        graphics.putString(column, row, fit(text, width));
        graphics.setForegroundColor(NORMAL);
    }

    /** Como {@link #text}, en negrita. */
    static void boldText(TextGraphics graphics, int column, int row, int width, String text, TextColor color) {
        graphics.setForegroundColor(color);
        graphics.putString(column, row, fit(text, width), SGR.BOLD);
        graphics.setForegroundColor(NORMAL);
    }

    /** Ajusta el texto a un ancho exacto en columnas de terminal. */
    static String fit(String text, int width) {
        String fitted = fitWithoutPadding(text, width);
        int missing = width - TerminalTextUtils.getColumnWidth(fitted);
        return missing > 0 ? fitted + " ".repeat(missing) : fitted;
    }

    /** Recorta el texto si pasa del ancho; un carácter ancho, como los CJK, cuenta por dos columnas. */
    static String fitWithoutPadding(String text, int width) {
        if (width <= 0) {
            return "";
        }
        String oneLine = text.replace('\n', ' ').replace('\r', ' ');
        if (TerminalTextUtils.getColumnWidth(oneLine) <= width) {
            return oneLine;
        }
        return TerminalTextUtils.fitString(oneLine, width - 1) + "…";
    }

    /** Alinea el texto a la derecha dentro del ancho. */
    static String right(String text, int width) {
        int missing = width - TerminalTextUtils.getColumnWidth(text);
        return missing > 0 ? " ".repeat(missing) + text : text;
    }

    /** @return el número con separador de miles, por ejemplo {@code 6,899} */
    static String number(long value) {
        return String.format(Locale.US, "%,d", value);
    }
}
