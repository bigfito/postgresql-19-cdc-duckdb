package com.elastiflix.simulator.dataset;

import static com.elastiflix.simulator.dataset.Column.bigint;
import static com.elastiflix.simulator.dataset.Column.bool;
import static com.elastiflix.simulator.dataset.Column.date;
import static com.elastiflix.simulator.dataset.Column.integer;
import static com.elastiflix.simulator.dataset.Column.numeric;
import static com.elastiflix.simulator.dataset.Column.text;

import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Las 20 tablas del esquema {@code catalog}, con sus columnas en el orden del
 * CSV (diseño, sección 8.2).
 *
 * <p>El orden de las constantes es el orden en que se insertan dentro de la
 * transacción de una película (diseño, sección 9.7): primero catálogos y
 * entidades compartidas, después {@code movie} y por último sus relaciones.</p>
 *
 * <p>Hay tres clases de tabla:</p>
 * <ul>
 *   <li><b>compartida</b>: catálogo o entidad que usan varias películas; su
 *       clave es la primera columna;</li>
 *   <li><b>película</b>: {@code movie};</li>
 *   <li><b>relación</b>: cuelga de una película; su primera columna es
 *       {@code movie_id} y la segunda apunta a una tabla compartida.</li>
 * </ul>
 */
public enum CatalogTable {

    MOVIE_STATUS("movie_status", Kind.SHARED, null, text("status_code")),
    CONTENT_RATING("content_rating", Kind.SHARED, null, text("rating_code")),
    ORIGINAL_LANGUAGE("original_language", Kind.SHARED, null, text("language_code"), text("description")),
    ENRICHMENT_FIELD("enrichment_field", Kind.SHARED, null, text("field_name")),
    GENRE("genre", Kind.SHARED, null, bigint("genre_id"), text("name")),
    KEYWORD("keyword", Kind.SHARED, null, bigint("keyword_id"), text("name")),
    PERSON("person", Kind.SHARED, null, bigint("person_id"), text("name")),
    PRODUCTION_COMPANY("production_company", Kind.SHARED, null, bigint("company_id"), text("name")),
    PRODUCTION_COUNTRY("production_country", Kind.SHARED, null, bigint("country_id"), text("name")),
    SPOKEN_LANGUAGE("spoken_language", Kind.SHARED, null, bigint("spoken_language_id"), text("name")),
    COLLECTION("collection", Kind.SHARED, null, bigint("collection_id"), text("name")),

    MOVIE("movie", Kind.MOVIE, null,
            bigint("movie_id"), text("imdb_id"), text("title"), text("original_title"),
            text("original_language_code"), text("overview"), text("plot"), text("tagline"),
            text("status_code"), text("rating_code"), date("release_date"), integer("runtime_minutes"),
            numeric("budget_usd"), numeric("revenue_usd"), numeric("popularity"), numeric("user_score"),
            numeric("vote_average"), integer("vote_count"), bool("adult"), bool("video"),
            text("homepage"), text("poster_path"), text("backdrop_path")),

    MOVIE_COLLECTION("movie_collection", Kind.RELATION, COLLECTION,
            bigint("movie_id"), bigint("collection_id"),
            text("observed_poster_path"), text("observed_backdrop_path")),
    MOVIE_GENRE("movie_genre", Kind.RELATION, GENRE,
            bigint("movie_id"), bigint("genre_id"), integer("source_position")),
    MOVIE_KEYWORD("movie_keyword", Kind.RELATION, KEYWORD,
            bigint("movie_id"), bigint("keyword_id"), integer("source_position")),
    MOVIE_CAST("movie_cast", Kind.RELATION, PERSON,
            bigint("movie_id"), bigint("person_id"), integer("billing_order")),
    MOVIE_PRODUCTION_COMPANY("movie_production_company", Kind.RELATION, PRODUCTION_COMPANY,
            bigint("movie_id"), bigint("company_id"), integer("source_position")),
    MOVIE_PRODUCTION_COUNTRY("movie_production_country", Kind.RELATION, PRODUCTION_COUNTRY,
            bigint("movie_id"), bigint("country_id"), integer("source_position")),
    MOVIE_SPOKEN_LANGUAGE("movie_spoken_language", Kind.RELATION, SPOKEN_LANGUAGE,
            bigint("movie_id"), bigint("spoken_language_id"), integer("source_position")),
    MOVIE_ENRICHMENT("movie_enrichment", Kind.RELATION, ENRICHMENT_FIELD,
            bigint("movie_id"), text("field_name"), text("code"));

    /** Posición de la columna que apunta a la tabla compartida, en una tabla de relación. */
    public static final int RELATION_REFERENCE_INDEX = 1;

    private enum Kind { SHARED, MOVIE, RELATION }

    private final String tableName;
    private final Kind kind;
    private final CatalogTable referencedTable;
    private final List<Column> columns;
    private final String insertSql;

    CatalogTable(String tableName, Kind kind, CatalogTable referencedTable, Column... columns) {
        this.tableName = tableName;
        this.kind = kind;
        this.referencedTable = referencedTable;
        this.columns = List.of(columns);
        this.insertSql = buildInsertSql();
    }

    private String buildInsertSql() {
        String names = columns.stream().map(Column::name).collect(Collectors.joining(", "));
        String marks = columns.stream().map(column -> "?").collect(Collectors.joining(", "));
        return "INSERT INTO " + qualifiedName() + " (" + names + ") VALUES (" + marks + ")";
    }

    /** @return el nombre de la tabla sin esquema, por ejemplo {@code movie_genre} */
    public String tableName() {
        return tableName;
    }

    /** @return el nombre con esquema, por ejemplo {@code catalog.movie_genre} */
    public String qualifiedName() {
        return "catalog." + tableName;
    }

    /** @return el nombre de su archivo en {@code raw_data/} */
    public String fileName() {
        return tableName + ".csv";
    }

    /** @return las columnas, en el orden del CSV */
    public List<Column> columns() {
        return columns;
    }

    /** @return la columna clave de una tabla compartida, o {@code movie_id} en las demás */
    public Column keyColumn() {
        return columns.get(0);
    }

    /** @return {@code true} si es un catálogo o una entidad compartida */
    public boolean isShared() {
        return kind == Kind.SHARED;
    }

    /** @return {@code true} si es una tabla de relación de una película */
    public boolean isRelation() {
        return kind == Kind.RELATION;
    }

    /** @return la tabla compartida a la que apunta una tabla de relación; {@code null} en las demás */
    public CatalogTable referencedTable() {
        return referencedTable;
    }

    /** @return la sentencia INSERT con todas las columnas del CSV */
    public String insertSql() {
        return insertSql;
    }

    /**
     * @param columnName nombre de una columna de esta tabla
     * @return su posición, empezando en cero
     * @throws IllegalArgumentException si la tabla no tiene esa columna
     */
    public int columnIndex(String columnName) {
        for (int index = 0; index < columns.size(); index++) {
            if (columns.get(index).name().equals(columnName)) {
                return index;
            }
        }
        throw new IllegalArgumentException(tableName + " no tiene la columna " + columnName);
    }

    /** @return los 11 catálogos y entidades compartidas, en orden de inserción */
    public static List<CatalogTable> sharedTables() {
        return Arrays.stream(values()).filter(CatalogTable::isShared).toList();
    }

    /** @return las 8 tablas de relación, en orden de inserción */
    public static List<CatalogTable> relationTables() {
        return Arrays.stream(values()).filter(CatalogTable::isRelation).toList();
    }
}
