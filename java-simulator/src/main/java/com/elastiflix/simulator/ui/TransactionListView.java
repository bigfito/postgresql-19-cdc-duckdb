package com.elastiflix.simulator.ui;

import com.elastiflix.simulator.simulation.TransactionRecord;

import java.util.List;

/**
 * Qué transacción de la lista está seleccionada y qué tramo de la lista se ve.
 *
 * <p>Por defecto la selección sigue a la transacción más reciente. Al bajar
 * con la flecha, se queda en una transacción concreta aunque lleguen otras
 * nuevas, hasta que se vuelve a subir al principio.</p>
 */
final class TransactionListView {

    /** Número de orden de la transacción seleccionada; {@code null} para seguir a la más reciente. */
    private Long selectedSequence;
    private int firstVisible;

    /** Vuelve a seguir a la transacción más reciente. */
    void followNewest() {
        selectedSequence = null;
        firstVisible = 0;
    }

    /** Sube una fila; en la primera, la selección vuelve a seguir a la más reciente. */
    void moveUp(List<TransactionRecord> recent) {
        int target = selectedIndex(recent) - 1;
        if (target <= 0) {
            followNewest();
        } else {
            selectedSequence = recent.get(target).sequence();
        }
    }

    /** Baja una fila, sin pasar de la última. */
    void moveDown(List<TransactionRecord> recent) {
        if (recent.isEmpty()) {
            return;
        }
        int target = Math.min(selectedIndex(recent) + 1, recent.size() - 1);
        selectedSequence = recent.get(target).sequence();
    }

    /**
     * @param recent transacciones, de la más reciente a la más antigua
     * @return la posición de la seleccionada; 0 si se sigue a la más reciente
     *         o si la seleccionada ya salió de la lista
     */
    int selectedIndex(List<TransactionRecord> recent) {
        if (selectedSequence == null) {
            return 0;
        }
        for (int index = 0; index < recent.size(); index++) {
            if (recent.get(index).sequence() == selectedSequence) {
                return index;
            }
        }
        followNewest();
        return 0;
    }

    /**
     * Ajusta el tramo visible para que la fila seleccionada quede dentro.
     *
     * @param recent      transacciones, de la más reciente a la más antigua
     * @param visibleRows cuántas filas caben en la zona
     * @return la posición de la primera fila que se dibuja
     */
    int firstVisible(List<TransactionRecord> recent, int visibleRows) {
        int selected = selectedIndex(recent);
        if (selectedSequence == null || selected < firstVisible) {
            firstVisible = selected;
        } else if (selected >= firstVisible + visibleRows) {
            firstVisible = selected - visibleRows + 1;
        }
        return firstVisible;
    }
}
