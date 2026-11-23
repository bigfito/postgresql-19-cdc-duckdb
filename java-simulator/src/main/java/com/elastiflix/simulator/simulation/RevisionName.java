package com.elastiflix.simulator.simulation;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Calcula el nombre que deja un UPDATE de catálogo (diseño, sección 9.5).
 */
public final class RevisionName {

    /** Un nombre que ya termina en « (rev N)». */
    private static final Pattern REVISED = Pattern.compile("(.*) \\(rev (\\d{1,9})\\)", Pattern.DOTALL);

    private RevisionName() {
    }

    /**
     * Añade el sufijo {@code  (rev 1)} al nombre. Si ya termina en
     * {@code  (rev N)}, lo sustituye por {@code  (rev N+1)}: el sufijo no se
     * acumula.
     *
     * @param currentName nombre que la colección o la keyword tiene en PostgreSQL
     * @return el nombre con la revisión siguiente
     */
    public static String next(String currentName) {
        Matcher matcher = REVISED.matcher(currentName);
        if (matcher.matches()) {
            int revision = Integer.parseInt(matcher.group(2));
            return matcher.group(1) + " (rev " + (revision + 1) + ")";
        }
        return currentName + " (rev 1)";
    }
}
