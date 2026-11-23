package com.elastiflix.simulator.simulation;

import java.math.BigDecimal;

/**
 * Las seis medidas de una película que cambia un UPDATE de medidas (diseño,
 * sección 9.5). Todas salvo la popularidad pueden ser {@code null}.
 *
 * @param popularity  popularidad, con tres decimales
 * @param voteCount   número de votos
 * @param voteAverage media de votos, entre 0 y 10, con tres decimales
 * @param userScore   puntuación de usuarios, entre 0 y 10, con un decimal
 * @param budgetUsd   presupuesto; {@code null} significa dato ausente
 * @param revenueUsd  recaudación; {@code null} significa dato ausente
 */
public record MeasureValues(
        BigDecimal popularity,
        Integer voteCount,
        BigDecimal voteAverage,
        BigDecimal userScore,
        BigDecimal budgetUsd,
        BigDecimal revenueUsd) {
}
