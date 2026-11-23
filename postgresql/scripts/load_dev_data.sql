-- =============================================================================
-- ElastiFlix: carga de desarrollo del dataset completo (diseño, sección 39,
-- «Datos de desarrollo»)
-- =============================================================================
-- Carga de una vez los 20 CSV de raw_data/ en el esquema catalog, para
-- desarrollar las fases que no pueden esperar al simulador con el volumen real.
--
-- SOLO PARA DESARROLLAR. El laboratorio terminado arranca con las tablas vacías
-- y es el Event Simulator quien las llena. Ningún servicio ni job del Compose
-- ejecuta este archivo: se lanza a mano, con el servicio postgresql en marcha,
-- desde la raíz del repositorio:
--
--   docker compose run --rm --no-deps -v ./raw_data:/raw_data:ro -v ./postgresql/scripts:/scripts:ro postgresql bash -c 'PGPASSWORD="$ELASTIFLIX_APP_PASSWORD" psql -h postgresql -U elastiflix_app -d elastiflix -v ON_ERROR_STOP=1 -f /scripts/load_dev_data.sql'
--
-- Ese comando crea un contenedor temporal de la imagen de PostgreSQL, que monta
-- raw_data/ y postgresql/scripts/ en solo lectura y se conecta por la red del
-- proyecto con la cuenta elastiflix_app, la misma que usará el simulador.
--
-- Cómo funciona:
--   - \copy lee cada archivo en el contenedor temporal y lo envía al servidor,
--     así que al servidor le basta el permiso INSERT de elastiflix_app.
--   - Los archivos van en el orden de las claves foráneas: catálogos,
--     entidades compartidas, movie y, al final, sus relaciones.
--   - Las columnas se nombran en el orden de cada CSV (sección 8.2). Las que
--     no vienen en los archivos, created_at y updated_at, las pone PostgreSQL.
--   - Cada archivo es una transacción aparte. No se carga todo en una sola
--     porque PostgreSQL decodifica cada transacción entera antes de entregarla
--     al CDC y, cuando pasa de 64 MB, la vuelca a disco cambio a cambio. Con
--     los datos en un directorio compartido desde Windows, ese volcado tarda
--     muchos minutos y Bronze no recibe nada mientras tanto.
--   - Si un archivo falla, lo ya cargado se queda: hay que volver a cero
--     (sección 39, «Vuelta a cero») y repetir la carga.
--   - Solo carga sobre una base vacía. Si catalog ya tiene datos, se detiene
--     sin tocar nada; para repetir la carga hay que volver antes a cero
--     (sección 39, «Vuelta a cero»).
--
-- Flink CDC lleva estas filas a Bronze como cualquier otro cambio: en el
-- snapshot inicial si se cargan antes de enviar el pipeline, o como cambios en
-- streaming si el pipeline ya corre.

\set ON_ERROR_STOP on

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM catalog.movie_status)
       OR EXISTS (SELECT 1 FROM catalog.movie)
       OR EXISTS (SELECT 1 FROM catalog.genre) THEN
        RAISE EXCEPTION 'El esquema catalog ya tiene datos. Esta carga solo se hace sobre una base vacía.'
              USING HINT = 'Vuelve el laboratorio a cero (diseño, sección 39) y repite la carga.';
    END IF;
END
$$;

-- Catálogos.
\copy catalog.movie_status (status_code) FROM '/raw_data/movie_status.csv' WITH (FORMAT csv, HEADER true)
\copy catalog.content_rating (rating_code) FROM '/raw_data/content_rating.csv' WITH (FORMAT csv, HEADER true)
\copy catalog.original_language (language_code, description) FROM '/raw_data/original_language.csv' WITH (FORMAT csv, HEADER true)
\copy catalog.enrichment_field (field_name) FROM '/raw_data/enrichment_field.csv' WITH (FORMAT csv, HEADER true)

-- Entidades compartidas.
\copy catalog.collection (collection_id, name) FROM '/raw_data/collection.csv' WITH (FORMAT csv, HEADER true)
\copy catalog.genre (genre_id, name) FROM '/raw_data/genre.csv' WITH (FORMAT csv, HEADER true)
\copy catalog.keyword (keyword_id, name) FROM '/raw_data/keyword.csv' WITH (FORMAT csv, HEADER true)
\copy catalog.person (person_id, name) FROM '/raw_data/person.csv' WITH (FORMAT csv, HEADER true)
\copy catalog.production_company (company_id, name) FROM '/raw_data/production_company.csv' WITH (FORMAT csv, HEADER true)
\copy catalog.production_country (country_id, name) FROM '/raw_data/production_country.csv' WITH (FORMAT csv, HEADER true)
\copy catalog.spoken_language (spoken_language_id, name) FROM '/raw_data/spoken_language.csv' WITH (FORMAT csv, HEADER true)

-- Películas.
\copy catalog.movie (movie_id, imdb_id, title, original_title, original_language_code, overview, plot, tagline, status_code, rating_code, release_date, runtime_minutes, budget_usd, revenue_usd, popularity, user_score, vote_average, vote_count, adult, video, homepage, poster_path, backdrop_path) FROM '/raw_data/movie.csv' WITH (FORMAT csv, HEADER true)

-- Relaciones de cada película.
\copy catalog.movie_collection (movie_id, collection_id, observed_poster_path, observed_backdrop_path) FROM '/raw_data/movie_collection.csv' WITH (FORMAT csv, HEADER true)
\copy catalog.movie_genre (movie_id, genre_id, source_position) FROM '/raw_data/movie_genre.csv' WITH (FORMAT csv, HEADER true)
\copy catalog.movie_keyword (movie_id, keyword_id, source_position) FROM '/raw_data/movie_keyword.csv' WITH (FORMAT csv, HEADER true)
\copy catalog.movie_cast (movie_id, person_id, billing_order) FROM '/raw_data/movie_cast.csv' WITH (FORMAT csv, HEADER true)
\copy catalog.movie_production_company (movie_id, company_id, source_position) FROM '/raw_data/movie_production_company.csv' WITH (FORMAT csv, HEADER true)
\copy catalog.movie_production_country (movie_id, country_id, source_position) FROM '/raw_data/movie_production_country.csv' WITH (FORMAT csv, HEADER true)
\copy catalog.movie_spoken_language (movie_id, spoken_language_id, source_position) FROM '/raw_data/movie_spoken_language.csv' WITH (FORMAT csv, HEADER true)
\copy catalog.movie_enrichment (movie_id, field_name, code) FROM '/raw_data/movie_enrichment.csv' WITH (FORMAT csv, HEADER true)

-- Resumen: filas por tabla y total. El dataset definitivo suma 438,925 filas y
-- 6,899 películas (sección 8.5).
SELECT tabla, filas
  FROM (
        SELECT 1 AS orden, 'movie_status' AS tabla, count(*) AS filas FROM catalog.movie_status
        UNION ALL SELECT 2, 'content_rating', count(*) FROM catalog.content_rating
        UNION ALL SELECT 3, 'original_language', count(*) FROM catalog.original_language
        UNION ALL SELECT 4, 'enrichment_field', count(*) FROM catalog.enrichment_field
        UNION ALL SELECT 5, 'collection', count(*) FROM catalog.collection
        UNION ALL SELECT 6, 'genre', count(*) FROM catalog.genre
        UNION ALL SELECT 7, 'keyword', count(*) FROM catalog.keyword
        UNION ALL SELECT 8, 'person', count(*) FROM catalog.person
        UNION ALL SELECT 9, 'production_company', count(*) FROM catalog.production_company
        UNION ALL SELECT 10, 'production_country', count(*) FROM catalog.production_country
        UNION ALL SELECT 11, 'spoken_language', count(*) FROM catalog.spoken_language
        UNION ALL SELECT 12, 'movie', count(*) FROM catalog.movie
        UNION ALL SELECT 13, 'movie_collection', count(*) FROM catalog.movie_collection
        UNION ALL SELECT 14, 'movie_genre', count(*) FROM catalog.movie_genre
        UNION ALL SELECT 15, 'movie_keyword', count(*) FROM catalog.movie_keyword
        UNION ALL SELECT 16, 'movie_cast', count(*) FROM catalog.movie_cast
        UNION ALL SELECT 17, 'movie_production_company', count(*) FROM catalog.movie_production_company
        UNION ALL SELECT 18, 'movie_production_country', count(*) FROM catalog.movie_production_country
        UNION ALL SELECT 19, 'movie_spoken_language', count(*) FROM catalog.movie_spoken_language
        UNION ALL SELECT 20, 'movie_enrichment', count(*) FROM catalog.movie_enrichment
       ) t
 ORDER BY orden;

SELECT (SELECT count(*) FROM catalog.movie_status) + (SELECT count(*) FROM catalog.content_rating)
     + (SELECT count(*) FROM catalog.original_language) + (SELECT count(*) FROM catalog.enrichment_field)
     + (SELECT count(*) FROM catalog.collection) + (SELECT count(*) FROM catalog.genre)
     + (SELECT count(*) FROM catalog.keyword) + (SELECT count(*) FROM catalog.person)
     + (SELECT count(*) FROM catalog.production_company) + (SELECT count(*) FROM catalog.production_country)
     + (SELECT count(*) FROM catalog.spoken_language) + (SELECT count(*) FROM catalog.movie)
     + (SELECT count(*) FROM catalog.movie_collection) + (SELECT count(*) FROM catalog.movie_genre)
     + (SELECT count(*) FROM catalog.movie_keyword) + (SELECT count(*) FROM catalog.movie_cast)
     + (SELECT count(*) FROM catalog.movie_production_company) + (SELECT count(*) FROM catalog.movie_production_country)
     + (SELECT count(*) FROM catalog.movie_spoken_language) + (SELECT count(*) FROM catalog.movie_enrichment)
       AS filas_totales;
