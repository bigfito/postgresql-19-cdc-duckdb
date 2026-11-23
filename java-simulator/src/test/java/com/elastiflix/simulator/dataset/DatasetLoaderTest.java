package com.elastiflix.simulator.dataset;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

import com.elastiflix.simulator.error.ErrorCode;
import com.elastiflix.simulator.error.SimulatorException;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

/**
 * Carga de los 20 archivos en memoria (RF-01), con un dataset mínimo escrito
 * para la prueba y, si está disponible, con el dataset real del repositorio.
 */
class DatasetLoaderTest {

    @TempDir
    Path directory;

    @BeforeEach
    void writeSmallDataset() throws IOException {
        write("movie_status.csv", "status_code\nReleased\n");
        write("content_rating.csv", "rating_code\nPG\nR\n");
        write("original_language.csv", "language_code,description\nen,\nes,\n");
        write("enrichment_field.csv", "field_name\nplot\n");
        write("genre.csv", "genre_id,name\n1,Mystery\n2,Drama\n");
        write("keyword.csv", "keyword_id,name\n30,rogue tart\n62,bacteria\n");
        write("person.csv", "person_id,name\n1,Sipho Fischer\n2,Hannah Ashford\n");
        write("production_company.csv", "company_id,name\n1,Haunted Song Media\n");
        write("production_country.csv", "country_id,name\n1,United States of America\n");
        write("spoken_language.csv", "spoken_language_id,name\n1,English\n");
        write("collection.csv", "collection_id,name\n10,Refuge Collection\n");
        write("movie.csv", "movie_id,imdb_id,title,original_title,original_language_code,overview,plot,tagline,"
                + "status_code,rating_code,release_date,runtime_minutes,budget_usd,revenue_usd,popularity,"
                + "user_score,vote_average,vote_count,adult,video,homepage,poster_path,backdrop_path\n"
                + "23,,Segunda,Segunda,es,,Trama,,Released,R,2001-01-01,,,,2.000,,,,false,false,,,\n"
                + "11,,Primera,Primera,en,,Trama,,Released,PG,2000-01-01,,,,1.000,,,,false,false,,,\n");
        write("movie_collection.csv", "movie_id,collection_id,observed_poster_path,observed_backdrop_path\n"
                + "23,10,/p.jpg,\n");
        write("movie_genre.csv", "movie_id,genre_id,source_position\n23,2,1\n23,1,2\n11,1,1\n");
        write("movie_keyword.csv", "movie_id,keyword_id,source_position\n11,30,1\n11,62,2\n");
        write("movie_cast.csv", "movie_id,person_id,billing_order\n11,1,1\n11,2,2\n23,2,1\n");
        write("movie_production_company.csv", "movie_id,company_id,source_position\n11,1,1\n");
        write("movie_production_country.csv", "movie_id,country_id,source_position\n11,1,1\n");
        write("movie_spoken_language.csv", "movie_id,spoken_language_id,source_position\n11,1,1\n");
        write("movie_enrichment.csv", "movie_id,field_name,code\n11,plot,wikipedia_plot\n");
    }

    @Test
    void cargaLosVeinteArchivos() {
        Dataset dataset = new DatasetLoader().load(directory);

        assertEquals(2, dataset.movieCount());
        assertEquals(2, dataset.rowCount(CatalogTable.GENRE));
        assertEquals(3, dataset.rowCount(CatalogTable.MOVIE_CAST));
        assertEquals(31, dataset.totalRowCount());
    }

    @Test
    void lasPeliculasConservanElOrdenDelArchivo() {
        Dataset dataset = new DatasetLoader().load(directory);

        assertEquals(List.of(23L, 11L), dataset.movieIds(), "el orden de alta es el de movie.csv, no el del id");
        assertEquals("Segunda", dataset.title(23));
        assertEquals("R", dataset.movieValue(23, "rating_code"));
        assertTrue(dataset.hasMovie(11));
        assertFalse(dataset.hasMovie(99));
    }

    @Test
    void lasRelacionesQuedanIndexadasPorPelicula() {
        Dataset dataset = new DatasetLoader().load(directory);

        List<Object[]> genres = dataset.relationRows(CatalogTable.MOVIE_GENRE, 23);
        assertEquals(2, genres.size());
        assertEquals(2L, genres.get(0)[1], "se conserva el orden de source_position del archivo");
        assertEquals(1L, genres.get(1)[1]);
        assertEquals(2, dataset.relationRows(CatalogTable.MOVIE_CAST, 11).size());
        assertTrue(dataset.relationRows(CatalogTable.MOVIE_KEYWORD, 23).isEmpty(), "una película sin keywords");
        assertEquals(1, dataset.relationRows(CatalogTable.MOVIE_COLLECTION, 23).size());
    }

    @Test
    void losCatalogosYEntidadesSeBuscanPorSuClave() {
        Dataset dataset = new DatasetLoader().load(directory);

        assertEquals("Drama", dataset.sharedRow(CatalogTable.GENRE, 2L)[1]);
        assertEquals("rogue tart", dataset.sharedRow(CatalogTable.KEYWORD, 30L)[1]);
        assertNotNull(dataset.sharedRow(CatalogTable.MOVIE_STATUS, "Released"));
        assertNull(dataset.sharedRow(CatalogTable.ORIGINAL_LANGUAGE, "en")[1], "description llega NULL");
        assertNull(dataset.sharedRow(CatalogTable.GENRE, 99L), "una clave que el dataset no trae");
    }

    @Test
    void fallaSiFaltaUnArchivo() throws IOException {
        Files.delete(directory.resolve("movie_cast.csv"));

        SimulatorException error = assertThrows(SimulatorException.class, () -> new DatasetLoader().load(directory));

        assertEquals(ErrorCode.DATASET_FILE_MISSING, error.errorCode());
    }

    /**
     * Carga el dataset real si la prueba corre dentro del repositorio. Durante
     * el build de la imagen no está disponible y la prueba se omite.
     */
    @Test
    void cargaElDatasetRealDelRepositorio() {
        Path rawData = Path.of("..", "raw_data");
        assumeTrue(Files.isRegularFile(rawData.resolve("movie.csv")), "raw_data/ no está disponible");

        Dataset dataset = new DatasetLoader().load(rawData);

        assertEquals(6_899, dataset.movieCount());
        assertEquals(11L, dataset.movieIds().get(0), "movie.csv va ordenado por movie_id");
        assertEquals(19, dataset.rowCount(CatalogTable.GENRE));
        assertEquals(438_925, dataset.totalRowCount(), "las 20 tablas suman 438,925 filas (diseño, sección 39)");
        for (long movieId : dataset.movieIds()) {
            assertNotNull(dataset.movieValue(movieId, "plot"), "plot es NOT NULL");
        }
    }

    private void write(String fileName, String content) throws IOException {
        Files.writeString(directory.resolve(fileName), content, StandardCharsets.UTF_8);
    }
}
