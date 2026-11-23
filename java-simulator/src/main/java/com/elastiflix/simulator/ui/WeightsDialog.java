package com.elastiflix.simulator.ui;

import com.elastiflix.simulator.config.Weights;
import com.elastiflix.simulator.error.SimulatorException;
import com.elastiflix.simulator.simulation.SimulationControl;

import com.googlecode.lanterna.TerminalPosition;
import com.googlecode.lanterna.TerminalSize;
import com.googlecode.lanterna.graphics.TextGraphics;
import com.googlecode.lanterna.input.KeyStroke;
import com.googlecode.lanterna.input.KeyType;

/**
 * Diálogo de pesos (tecla {@code P}; RF-07): tres campos numéricos para los
 * pesos de INSERT, UPDATE y DELETE. Enter los aplica sin reiniciar.
 */
final class WeightsDialog implements Dialog {

    private static final String[] LABELS = {"INSERT", "UPDATE", "DELETE"};
    private static final int WIDTH = 58;
    private static final int HEIGHT = 10;
    private static final int MAX_DIGITS = 4;
    private static final int FIELD_COLUMN = 12;

    private final SimulationControl control;
    private final StringBuilder[] fields = new StringBuilder[LABELS.length];
    private int focus;
    private String error = "";
    private TerminalPosition cursor;

    /**
     * @param control de dónde se leen los pesos vigentes y dónde se aplican los nuevos
     */
    WeightsDialog(SimulationControl control) {
        this.control = control;
        Weights current = control.weights();
        fields[0] = new StringBuilder(String.valueOf(current.insert()));
        fields[1] = new StringBuilder(String.valueOf(current.update()));
        fields[2] = new StringBuilder(String.valueOf(current.delete()));
    }

    @Override
    public boolean handleKey(KeyStroke key) {
        KeyType type = key.getKeyType();
        if (type == KeyType.Escape) {
            return false;
        }
        if (type == KeyType.Enter) {
            return !apply();
        }
        if (type == KeyType.Tab || type == KeyType.ArrowDown) {
            focus = (focus + 1) % fields.length;
        } else if (type == KeyType.ReverseTab || type == KeyType.ArrowUp) {
            focus = (focus + fields.length - 1) % fields.length;
        } else if (type == KeyType.Backspace && !fields[focus].isEmpty()) {
            fields[focus].setLength(fields[focus].length() - 1);
        } else if (type == KeyType.Character && Character.isDigit(key.getCharacter())
                && fields[focus].length() < MAX_DIGITS) {
            fields[focus].append(key.getCharacter());
        }
        return true;
    }

    /** @return {@code true} si los pesos eran válidos y quedaron aplicados */
    private boolean apply() {
        try {
            Weights weights = new Weights(valueOf(0), valueOf(1), valueOf(2));
            control.changeWeights(weights);
            return true;
        } catch (NumberFormatException e) {
            error = "Cada peso debe ser un número entero.";
        } catch (SimulatorException e) {
            error = "Al menos un peso debe ser mayor que cero.";
        }
        return false;
    }

    private int valueOf(int field) {
        return Integer.parseInt(fields[field].toString());
    }

    @Override
    public void paint(TextGraphics graphics, TerminalSize size) {
        int left = Math.max(0, (size.getColumns() - WIDTH) / 2);
        int top = Math.max(0, (size.getRows() - HEIGHT) / 2);
        Draw.clear(graphics, left, top, WIDTH, HEIGHT);
        Draw.box(graphics, left, top, WIDTH, HEIGHT, "Pesos de las operaciones");
        int inner = WIDTH - 4;
        for (int index = 0; index < fields.length; index++) {
            String mark = index == focus ? "▸ " : "  ";
            String line = mark + Draw.fit(LABELS[index], 8) + "[ " + Draw.fit(fields[index].toString(), MAX_DIGITS) + " ]";
            Draw.text(graphics, left + 2, top + 2 + index, inner, line, index == focus ? Draw.LABEL : Draw.NORMAL);
        }
        Draw.text(graphics, left + 2, top + 6, inner, error, Draw.BAD);
        Draw.text(graphics, left + 2, top + 7, inner, "Tab o ↑ ↓ cambia de campo · Enter aplica · Esc cancela",
                Draw.FRAME);
        cursor = new TerminalPosition(left + 2 + FIELD_COLUMN + fields[focus].length(), top + 2 + focus);
    }

    @Override
    public TerminalPosition cursor() {
        return cursor;
    }
}
