package com.elastiflix.simulator.simulation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.Random;

/**
 * Contenido de los UPDATE: nombre con revisión, textos descriptivos y medidas
 * (diseño, sección 9.5).
 */
class UpdateContentTest {

    // ------------------------------------------------------------------
    // UPDATE de catálogo: sufijo (rev N)
    // ------------------------------------------------------------------

    @Test
    void elPrimerRenombradoAnadeRevUno() {
        assertEquals("Refuge Collection (rev 1)", RevisionName.next("Refuge Collection"));
    }

    @Test
    void elSufijoSeSustituyeYNoSeAcumula() {
        assertEquals("Refuge Collection (rev 2)", RevisionName.next("Refuge Collection (rev 1)"));
        assertEquals("rogue tart (rev 10)", RevisionName.next("rogue tart (rev 9)"));

        String name = "bacteria";
        for (int revision = 0; revision < 25; revision++) {
            name = RevisionName.next(name);
        }
        assertEquals("bacteria (rev 25)", name);
    }

    @Test
    void soloCuentaElSufijoDelFinalDelNombre() {
        assertEquals("Saga (rev 3) especial (rev 1)", RevisionName.next("Saga (rev 3) especial"));
        assertEquals("(rev x) (rev 1)", RevisionName.next("(rev x)"));
    }

    // ------------------------------------------------------------------
    // UPDATE descriptivo
    // ------------------------------------------------------------------

    @Test
    void elCambioDescriptivoSiempreEsDistintoDelValorActual() {
        DescriptiveChangeGenerator generator = new DescriptiveChangeGenerator();
        DescriptiveValues original = new DescriptiveValues("Sun 2", "Un lema", "Una sinopsis.", "https://sun.example");
        DescriptiveValues current = original;
        Random random = new Random(42);

        for (int step = 0; step < 500; step++) {
            DescriptiveChange change = generator.next(11, original, current, random);
            assertNotEquals(current.get(change.field()), change.newValue(), "paso " + step);
            current = apply(current, change);
        }
    }

    @Test
    void lasVariantesPartenDelValorOriginalYNoCrecenSinLimite() {
        DescriptiveChangeGenerator generator = new DescriptiveChangeGenerator();
        DescriptiveValues original = new DescriptiveValues("Sun 2", null, null, null);
        DescriptiveValues current = original;
        Random random = new Random(7);

        for (int step = 0; step < 500; step++) {
            current = apply(current, generator.next(11, original, current, random));
        }

        assertTrue(current.title().startsWith("Sun 2"));
        assertTrue(current.title().length() <= "Sun 2: Anniversary Edition".length(), current.title());
        assertTrue(current.homepage().startsWith("https://"), "la columna solo admite http o https");
        assertTrue(current.overview().length() < 80, current.overview());
    }

    private static DescriptiveValues apply(DescriptiveValues current, DescriptiveChange change) {
        String value = change.newValue();
        return switch (change.field()) {
            case TITLE -> new DescriptiveValues(value, current.tagline(), current.overview(), current.homepage());
            case TAGLINE -> new DescriptiveValues(current.title(), value, current.overview(), current.homepage());
            case OVERVIEW -> new DescriptiveValues(current.title(), current.tagline(), value, current.homepage());
            case HOMEPAGE -> new DescriptiveValues(current.title(), current.tagline(), current.overview(), value);
        };
    }

    // ------------------------------------------------------------------
    // UPDATE de medidas
    // ------------------------------------------------------------------

    @Test
    void lasMedidasNuevasRespetanLasRestriccionesDeLaTabla() {
        MeasureChangeGenerator generator = new MeasureChangeGenerator();
        MeasureValues current = new MeasureValues(new BigDecimal("12.345"), 100, new BigDecimal("9.900"),
                new BigDecimal("0.1"), new BigDecimal("1000000.00"), new BigDecimal("2500000.50"));
        Random random = new Random(42);
        BigDecimal ten = BigDecimal.TEN;

        for (int step = 0; step < 2_000; step++) {
            MeasureValues next = generator.next(current, random);
            assertNotEquals(0, next.popularity().compareTo(current.popularity()), "la popularidad siempre cambia");
            assertTrue(next.popularity().signum() >= 0);
            assertEquals(3, next.popularity().scale());
            assertTrue(next.voteCount() > current.voteCount());
            assertTrue(next.voteAverage().signum() >= 0 && next.voteAverage().compareTo(ten) <= 0);
            assertEquals(3, next.voteAverage().scale());
            assertTrue(next.userScore().signum() >= 0 && next.userScore().compareTo(ten) <= 0);
            assertEquals(1, next.userScore().scale());
            assertTrue(next.budgetUsd().compareTo(current.budgetUsd()) >= 0);
            assertEquals(2, next.revenueUsd().scale());
            current = next;
        }
    }

    @Test
    void unImporteAusenteSigueAusente() {
        MeasureChangeGenerator generator = new MeasureChangeGenerator();
        MeasureValues current = new MeasureValues(new BigDecimal("0.000"), null, null, null, null, null);

        MeasureValues next = generator.next(current, new Random(42));

        assertNull(next.budgetUsd());
        assertNull(next.revenueUsd());
        assertEquals(new BigDecimal("0.001"), next.popularity(), "una popularidad de cero también cambia");
        assertTrue(next.voteCount() >= 1);
        assertTrue(next.voteAverage().compareTo(BigDecimal.ZERO) > 0);
    }

    @Test
    void laMismaSemillaDaLasMismasMedidas() {
        MeasureChangeGenerator generator = new MeasureChangeGenerator();
        MeasureValues current = new MeasureValues(new BigDecimal("12.345"), 100, new BigDecimal("6.500"),
                new BigDecimal("6.5"), null, new BigDecimal("2500000.50"));

        assertEquals(generator.next(current, new Random(42)), generator.next(current, new Random(42)));
    }
}
