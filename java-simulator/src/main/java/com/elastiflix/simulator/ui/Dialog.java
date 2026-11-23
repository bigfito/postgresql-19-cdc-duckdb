package com.elastiflix.simulator.ui;

import com.googlecode.lanterna.TerminalPosition;
import com.googlecode.lanterna.TerminalSize;
import com.googlecode.lanterna.graphics.TextGraphics;
import com.googlecode.lanterna.input.KeyStroke;

/**
 * Un diálogo que se dibuja sobre la pantalla y recibe todas las teclas
 * mientras está abierto.
 */
interface Dialog {

    /**
     * @param key tecla pulsada
     * @return {@code true} si el diálogo sigue abierto; {@code false} si se cerró
     */
    boolean handleKey(KeyStroke key);

    /**
     * Dibuja el diálogo centrado.
     *
     * @param graphics lienzo de la pantalla
     * @param size     tamaño actual de la terminal
     */
    void paint(TextGraphics graphics, TerminalSize size);

    /** @return dónde debe parpadear el cursor, o {@code null} para ocultarlo */
    TerminalPosition cursor();
}
