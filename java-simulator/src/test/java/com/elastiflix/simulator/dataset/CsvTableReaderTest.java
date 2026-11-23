package com.elastiflix.simulator.dataset;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.elastiflix.simulator.error.ErrorCode;
import com.elastiflix.simulator.error.SimulatorException;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.List;

/**
 * Lectura de un CSV con el formato del dataset (diseño, sección 8.3).
 */
class CsvTableReaderTest {

    private static final String MOVIE_HEADER = "movie_id,imdb_id,title,original_title,original_language_code,"
            + "overview,plot,tagline,status_code,rating_code,release_date,runtime_minutes,budget_usd,revenue_usd,"
            + "popularity,user_score,vote_average,vote_count,adult,video,homepage,poster_path,backdrop_path\n";

    @TempDir
    Path directory;

    private final CsvTableReader reader = new CsvTableReader();

    @Test
    void convierteCadaValorASuTipo() throws IOException {
        Path file = write("movie.csv", MOVIE_HEADER
                + "11,tt9780691,Sun 2,Sun 2,en,Resumen,Trama,Lema,Released,PG-13,1999-12-31,120,"
                + "1000000.00,2500000.50,12.345,7.5,7.512,1500,false,true,https://sun.example,/p.jpg,/b.jpg\n");

        Object[] movie = reader.read(CatalogTable.MOVIE, file).get(0);

        assertEquals(11L, movie[0]);
        assertEquals("Sun 2", movie[2]);
        assertEquals(LocalDate.of(1999, 12, 31), movie[10]);
        assertEquals(120, movie[11]);
        assertEquals(new BigDecimal("1000000.00"), movie[12]);
        assertEquals(new BigDecimal("12.345"), movie[14]);
        assertEquals(1500, movie[17]);
        assertEquals(Boolean.FALSE, movie[18]);
        assertEquals(Boolean.TRUE, movie[19]);
    }

    @Test
    void unCampoVacioEsNull() throws IOException {
        Path file = write("movie.csv", MOVIE_HEADER
                + "23,,Título,Título,es,,Trama,,Released,,2001-01-01,,,,0.600,,,,false,false,,,\n");

        Object[] movie = reader.read(CatalogTable.MOVIE, file).get(0);

        assertNull(movie[1], "imdb_id");
        assertNull(movie[5], "overview");
        assertNull(movie[9], "rating_code");
        assertNull(movie[11], "runtime_minutes");
        assertNull(movie[12], "budget_usd");
        assertNull(movie[22], "backdrop_path");
        assertEquals(new BigDecimal("0.600"), movie[14]);
    }

    @Test
    void respetaComasComillasYSaltosDeLineaDentroDeUnaCelda() throws IOException {
        Path file = write("movie.csv", MOVIE_HEADER
                + "46,,\"Uno, dos\",Uno,es,\"Dijo \"\"hola\"\", y se fue\",\"Primera línea\nSegunda línea\","
                + ",Released,,2001-01-01,,,,1.000,,,,false,false,,,\n"
                + "47,,Otra,Otra,es,,Trama,,Released,,2002-02-02,,,,2.000,,,,false,false,,,\n");

        List<Object[]> movies = reader.read(CatalogTable.MOVIE, file);

        assertEquals(2, movies.size(), "el salto de línea dentro de la celda no parte el registro");
        assertEquals("Uno, dos", movies.get(0)[2]);
        assertEquals("Dijo \"hola\", y se fue", movies.get(0)[5]);
        assertEquals("Primera línea\nSegunda línea", movies.get(0)[6]);
        assertEquals(47L, movies.get(1)[0]);
    }

    @Test
    void leeTextoUtf8() throws IOException {
        Path file = write("spoken_language.csv", "spoken_language_id,name\n2,Español\n3,日本語\n");

        List<Object[]> languages = reader.read(CatalogTable.SPOKEN_LANGUAGE, file);

        assertArrayEquals(new Object[] {2L, "Español"}, languages.get(0));
        assertArrayEquals(new Object[] {3L, "日本語"}, languages.get(1));
    }

    @Test
    void conservaElOrdenDelArchivo() throws IOException {
        Path file = write("movie_genre.csv", "movie_id,genre_id,source_position\n11,5,1\n11,2,2\n23,2,1\n");

        List<Object[]> rows = reader.read(CatalogTable.MOVIE_GENRE, file);

        assertEquals(3, rows.size());
        assertArrayEquals(new Object[] {11L, 5L, 1}, rows.get(0));
        assertArrayEquals(new Object[] {11L, 2L, 2}, rows.get(1));
        assertArrayEquals(new Object[] {23L, 2L, 1}, rows.get(2));
    }

    @Test
    void unArchivoSoloConCabeceraNoTieneFilas() throws IOException {
        Path file = write("genre.csv", "genre_id,name\n");

        assertTrue(reader.read(CatalogTable.GENRE, file).isEmpty());
    }

    @Test
    void rechazaUnaCabeceraQueNoEsLaDeLaTabla() throws IOException {
        Path file = write("genre.csv", "name,genre_id\nDrama,1\n");

        SimulatorException error = assertThrows(SimulatorException.class,
                () -> reader.read(CatalogTable.GENRE, file));

        assertEquals(ErrorCode.DATASET_FORMAT, error.errorCode());
        assertTrue(error.getMessage().contains("genre.csv"));
    }

    @Test
    void rechazaUnValorQueNoEsDeSuTipo() throws IOException {
        Path file = write("genre.csv", "genre_id,name\nuno,Drama\n");

        SimulatorException error = assertThrows(SimulatorException.class,
                () -> reader.read(CatalogTable.GENRE, file));

        assertEquals(ErrorCode.DATASET_FORMAT, error.errorCode());
        assertTrue(error.getMessage().contains("genre_id"), error.getMessage());
    }

    @Test
    void rechazaUnRegistroConCamposDeMenos() throws IOException {
        Path file = write("genre.csv", "genre_id,name\n1\n");

        SimulatorException error = assertThrows(SimulatorException.class,
                () -> reader.read(CatalogTable.GENRE, file));

        assertEquals(ErrorCode.DATASET_FORMAT, error.errorCode());
    }

    @Test
    void avisaSiFaltaElArchivo() {
        SimulatorException error = assertThrows(SimulatorException.class,
                () -> reader.read(CatalogTable.GENRE, directory.resolve("genre.csv")));

        assertEquals(ErrorCode.DATASET_FILE_MISSING, error.errorCode());
    }

    private Path write(String fileName, String content) throws IOException {
        Path file = directory.resolve(fileName);
        Files.writeString(file, content, StandardCharsets.UTF_8);
        return file;
    }
}
