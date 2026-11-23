package com.elastiflix.simulator.simulation;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Random;

/**
 * Inventa los valores de un UPDATE de medidas a partir de los actuales.
 *
 * <p>Imita lo que le pasa a una película con el tiempo: la popularidad sube o
 * baja, llegan votos nuevos, las puntuaciones se mueven un poco y los importes
 * crecen. Respeta las restricciones de {@code catalog.movie}: puntuaciones
 * entre 0 y 10, y popularidad y votos no negativos. Un presupuesto o una
 * recaudación ausentes siguen ausentes: {@code NULL} no se sustituye por un
 * número (diseño, sección 12.2).</p>
 */
public final class MeasureChangeGenerator {

    private static final BigDecimal MAX_POPULARITY = new BigDecimal("9999999.999");
    private static final BigDecimal POPULARITY_STEP = new BigDecimal("0.001");
    private static final BigDecimal DEFAULT_SCORE = new BigDecimal("5");

    /**
     * @param current medidas que la película tiene ahora en PostgreSQL
     * @param random  generador de la simulación
     * @return las medidas nuevas
     */
    public MeasureValues next(MeasureValues current, Random random) {
        return new MeasureValues(
                nextPopularity(current.popularity(), random),
                nextVoteCount(current.voteCount(), random),
                nextScore(current.voteAverage(), 3, random),
                nextScore(current.userScore(), 1, random),
                grow(current.budgetUsd(), 0.05, random),
                grow(current.revenueUsd(), 0.10, random));
    }

    /** Varía la popularidad hasta un 15 % arriba o abajo, y siempre la cambia. */
    private BigDecimal nextPopularity(BigDecimal current, Random random) {
        double factor = 0.85 + random.nextDouble() * 0.30;
        BigDecimal next = current.multiply(BigDecimal.valueOf(factor)).setScale(3, RoundingMode.HALF_UP);
        if (next.compareTo(current) == 0) {
            next = next.add(POPULARITY_STEP);
        }
        return next.min(MAX_POPULARITY);
    }

    /** Suma entre 1 y 250 votos. */
    private Integer nextVoteCount(Integer current, Random random) {
        long base = current == null ? 0 : current;
        return (int) Math.min(Integer.MAX_VALUE, base + 1 + random.nextInt(250));
    }

    /** Mueve una puntuación como mucho 0.3 puntos, sin salir del rango de 0 a 10. */
    private BigDecimal nextScore(BigDecimal current, int scale, Random random) {
        BigDecimal base = current == null ? DEFAULT_SCORE : current;
        double step = (random.nextDouble() * 2 - 1) * 0.3;
        BigDecimal next = base.add(BigDecimal.valueOf(step)).setScale(scale, RoundingMode.HALF_UP);
        return next.max(BigDecimal.ZERO).min(BigDecimal.TEN).setScale(scale, RoundingMode.HALF_UP);
    }

    /** Hace crecer un importe hasta {@code maxGrowth}; un importe ausente sigue ausente. */
    private BigDecimal grow(BigDecimal current, double maxGrowth, Random random) {
        double factor = 1 + random.nextDouble() * maxGrowth;
        if (current == null) {
            return null;
        }
        return current.multiply(BigDecimal.valueOf(factor)).setScale(2, RoundingMode.HALF_UP);
    }
}
