package com.elastiflix.simulator.simulation;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.Random;

/**
 * Inventa el cambio de un UPDATE descriptivo.
 *
 * <p>Elige uno de los cuatro campos y le da una variante construida sobre el
 * valor original del dataset, no sobre el valor actual: así los sufijos no se
 * acumulan por muchas veces que se actualice la misma película. La variante
 * elegida siempre es distinta del valor que hay ahora en PostgreSQL.</p>
 */
public final class DescriptiveChangeGenerator {

    private static final List<String> TITLE_SUFFIXES = List.of(
            ": Director's Cut", ": Extended Edition", ": Remastered", ": Anniversary Edition");

    private static final List<String> TAGLINES = List.of(
            "Every story has a second act.",
            "Some stories refuse to end.",
            "See it again for the first time.",
            "Now streaming on ElastiFlix.");

    private static final List<String> OVERVIEW_NOTES = List.of(
            "Newly restored for this release.",
            "This edition includes previously unseen footage.",
            "Presented with a remastered soundtrack.");

    private static final List<String> HOMEPAGE_PATHS = List.of("", "/special-edition", "/extras", "/watch");

    /**
     * @param movieId  película que se actualiza
     * @param original sus textos en el dataset
     * @param current  sus textos ahora en PostgreSQL
     * @param random   generador de la simulación
     * @return el campo elegido y su valor nuevo
     */
    public DescriptiveChange next(long movieId, DescriptiveValues original, DescriptiveValues current, Random random) {
        DescriptiveField[] fields = DescriptiveField.values();
        DescriptiveField field = fields[random.nextInt(fields.length)];
        List<String> variants = variantsOf(field, movieId, original);
        int choice = random.nextInt(variants.size());
        if (Objects.equals(variants.get(choice), current.get(field))) {
            choice = (choice + 1) % variants.size();
        }
        return new DescriptiveChange(field, variants.get(choice));
    }

    private List<String> variantsOf(DescriptiveField field, long movieId, DescriptiveValues original) {
        return switch (field) {
            case TITLE -> titleVariants(original.title());
            case TAGLINE -> withOriginal(original.tagline(), TAGLINES);
            case OVERVIEW -> overviewVariants(original.overview());
            case HOMEPAGE -> homepageVariants(original.homepage(), movieId);
        };
    }

    private List<String> titleVariants(String originalTitle) {
        List<String> variants = new ArrayList<>();
        variants.add(originalTitle);
        for (String suffix : TITLE_SUFFIXES) {
            variants.add(originalTitle + suffix);
        }
        return variants;
    }

    private List<String> overviewVariants(String originalOverview) {
        List<String> variants = new ArrayList<>();
        if (originalOverview != null) {
            variants.add(originalOverview);
        }
        for (String note : OVERVIEW_NOTES) {
            variants.add(originalOverview == null ? note : originalOverview + " " + note);
        }
        return variants;
    }

    /** Las direcciones cumplen la restricción de la columna: empiezan por http o https. */
    private List<String> homepageVariants(String originalHomepage, long movieId) {
        List<String> generated = new ArrayList<>();
        for (String path : HOMEPAGE_PATHS) {
            generated.add("https://www.elastiflix.example/movies/" + movieId + path);
        }
        return withOriginal(originalHomepage, generated);
    }

    private List<String> withOriginal(String original, List<String> others) {
        List<String> variants = new ArrayList<>();
        if (original != null) {
            variants.add(original);
        }
        variants.addAll(others);
        return variants;
    }
}
