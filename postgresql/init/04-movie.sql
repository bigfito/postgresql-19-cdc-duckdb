-- =============================================================================
-- ElastiFlix: movie y movie_collection (diseño, secciones 12.2 y 12.4)
-- =============================================================================
-- movie es el centro del modelo: apunta a tres catálogos y de ella cuelgan las
-- ocho tablas de relación. Su alta, con todas sus relaciones, es una sola
-- transacción del simulador (sección 9.7).
--
-- Tipos según el contrato de la sección 11. Los decimales declaran siempre
-- precisión y escala; no se usa money.
--
-- Las claves foráneas hacia los catálogos no llevan cascada: un catálogo no se
-- borra mientras alguna película lo use.

CREATE TABLE catalog.movie (
    movie_id               bigint        NOT NULL,
    imdb_id                text          NULL,
    title                  text          NOT NULL,
    original_title         text          NOT NULL,
    original_language_code text          NOT NULL,
    overview               text          NULL,
    plot                   text          NOT NULL,
    tagline                text          NULL,
    status_code            text          NOT NULL,
    rating_code            text          NULL,
    release_date           date          NOT NULL,
    runtime_minutes        integer       NULL,
    -- NULL significa «dato ausente»; no se sustituye por cero.
    budget_usd             numeric(18,2) NULL,
    revenue_usd            numeric(18,2) NULL,
    popularity             numeric(10,3) NOT NULL,
    user_score             numeric(3,1)  NULL,
    vote_average           numeric(5,3)  NULL,
    vote_count             integer       NULL,
    adult                  boolean       NOT NULL,
    video                  boolean       NOT NULL,
    homepage               text          NULL,
    poster_path            text          NULL,
    backdrop_path          text          NULL,
    -- Las asigna PostgreSQL. El simulador actualiza updated_at en cada UPDATE,
    -- también en los de relaciones y de catálogo (sección 9.5); no hay trigger.
    created_at             timestamp(6) with time zone NOT NULL DEFAULT now(),
    updated_at             timestamp(6) with time zone NOT NULL DEFAULT now(),

    CONSTRAINT pk_movie PRIMARY KEY (movie_id),
    CONSTRAINT fk_movie_original_language FOREIGN KEY (original_language_code)
        REFERENCES catalog.original_language (language_code),
    CONSTRAINT fk_movie_status FOREIGN KEY (status_code)
        REFERENCES catalog.movie_status (status_code),
    CONSTRAINT fk_movie_rating FOREIGN KEY (rating_code)
        REFERENCES catalog.content_rating (rating_code),

    CONSTRAINT ck_movie_id_positive CHECK (movie_id > 0),
    -- Patrón documentado de IMDb: 'tt' y 7 u 8 dígitos.
    CONSTRAINT ck_movie_imdb_id CHECK (imdb_id ~ '^tt[0-9]{7,8}$'),
    CONSTRAINT ck_movie_runtime_positive CHECK (runtime_minutes > 0),
    CONSTRAINT ck_movie_popularity_not_negative CHECK (popularity >= 0),
    CONSTRAINT ck_movie_user_score_range CHECK (user_score BETWEEN 0 AND 10),
    CONSTRAINT ck_movie_vote_average_range CHECK (vote_average BETWEEN 0 AND 10),
    -- Una película sin votos es un dato válido.
    CONSTRAINT ck_movie_vote_count_not_negative CHECK (vote_count >= 0),
    CONSTRAINT ck_movie_homepage_http CHECK (homepage ~ '^https?://'),
    -- Rutas relativas de TMDB: empiezan por '/' y no llevan servidor.
    CONSTRAINT ck_movie_poster_path_relative CHECK (poster_path ~ '^/'),
    CONSTRAINT ck_movie_backdrop_path_relative CHECK (backdrop_path ~ '^/')
);

COMMENT ON TABLE catalog.movie IS
    'Películas. Clave natural de TMDB; centro del modelo operacional.';

-- imdb_id es único cuando existe; varias películas pueden no tenerlo.
-- poster_path no es único: dos películas pueden compartir imagen.
CREATE UNIQUE INDEX uq_movie_imdb_id
    ON catalog.movie (imdb_id)
    WHERE imdb_id IS NOT NULL;

-- Relación película 0..1 colección: movie_id es a la vez clave primaria y
-- foránea. No lleva source_position porque no hay orden que conservar. Guarda
-- las imágenes de la colección tal como se observaron en esa película.
CREATE TABLE catalog.movie_collection (
    movie_id               bigint NOT NULL,
    collection_id          bigint NOT NULL,
    observed_poster_path   text   NULL,
    observed_backdrop_path text   NULL,

    CONSTRAINT pk_movie_collection PRIMARY KEY (movie_id),
    -- Borrar la película borra su pertenencia a la colección (sección 13).
    CONSTRAINT fk_movie_collection_movie FOREIGN KEY (movie_id)
        REFERENCES catalog.movie (movie_id) ON DELETE CASCADE,
    -- La colección no se borra con la película.
    CONSTRAINT fk_movie_collection_collection FOREIGN KEY (collection_id)
        REFERENCES catalog.collection (collection_id)
);

COMMENT ON TABLE catalog.movie_collection IS
    'Colección a la que pertenece una película, como máximo una.';
