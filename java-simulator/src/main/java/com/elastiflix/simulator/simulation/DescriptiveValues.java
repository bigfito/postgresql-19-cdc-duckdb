package com.elastiflix.simulator.simulation;

/**
 * Los cuatro textos descriptivos de una película. Salvo el título, pueden ser
 * {@code null}.
 *
 * @param title    título
 * @param tagline  lema
 * @param overview sinopsis
 * @param homepage página web
 */
public record DescriptiveValues(String title, String tagline, String overview, String homepage) {

    /**
     * @param field uno de los cuatro campos
     * @return su valor; puede ser {@code null}
     */
    public String get(DescriptiveField field) {
        return switch (field) {
            case TITLE -> title;
            case TAGLINE -> tagline;
            case OVERVIEW -> overview;
            case HOMEPAGE -> homepage;
        };
    }
}
