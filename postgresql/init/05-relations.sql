-- =============================================================================
-- ElastiFlix: las 6 tablas de relación y movie_enrichment (diseño, secciones
-- 12.6, 12.8, 12.10, 12.12, 12.14, 12.17 y 12.21)
-- =============================================================================
-- Regla común a las seis tablas de relación con lista ordenada:
--   - clave primaria (movie_id, <entidad>_id): dentro de una película no se
--     repite ninguna entidad;
--   - la posición es NOT NULL, empieza en 1 y es única junto con movie_id;
--     movie_cast la llama billing_order, las demás source_position.
--
-- Política de borrado (sección 13): borrar una película borra sus filas en
-- estas tablas (ON DELETE CASCADE), y cada fila borrada genera su propio
-- evento en el WAL. Las entidades compartidas no se borran nunca por cascada.

-- Géneros de una película.
CREATE TABLE catalog.movie_genre (
    movie_id        bigint  NOT NULL,
    genre_id        bigint  NOT NULL,
    source_position integer NOT NULL,

    CONSTRAINT pk_movie_genre PRIMARY KEY (movie_id, genre_id),
    CONSTRAINT uq_movie_genre_position UNIQUE (movie_id, source_position),
    CONSTRAINT fk_movie_genre_movie FOREIGN KEY (movie_id)
        REFERENCES catalog.movie (movie_id) ON DELETE CASCADE,
    CONSTRAINT fk_movie_genre_genre FOREIGN KEY (genre_id)
        REFERENCES catalog.genre (genre_id),
    CONSTRAINT ck_movie_genre_position CHECK (source_position >= 1)
);

COMMENT ON TABLE catalog.movie_genre IS
    'Géneros de cada película, en el orden de la fuente.';

-- Palabras clave de una película.
CREATE TABLE catalog.movie_keyword (
    movie_id        bigint  NOT NULL,
    keyword_id      bigint  NOT NULL,
    source_position integer NOT NULL,

    CONSTRAINT pk_movie_keyword PRIMARY KEY (movie_id, keyword_id),
    CONSTRAINT uq_movie_keyword_position UNIQUE (movie_id, source_position),
    CONSTRAINT fk_movie_keyword_movie FOREIGN KEY (movie_id)
        REFERENCES catalog.movie (movie_id) ON DELETE CASCADE,
    CONSTRAINT fk_movie_keyword_keyword FOREIGN KEY (keyword_id)
        REFERENCES catalog.keyword (keyword_id),
    CONSTRAINT ck_movie_keyword_position CHECK (source_position >= 1)
);

COMMENT ON TABLE catalog.movie_keyword IS
    'Palabras clave de cada película, en el orden de la fuente.';

-- Reparto de una película. billing_order conserva el orden de facturación.
CREATE TABLE catalog.movie_cast (
    movie_id      bigint  NOT NULL,
    person_id     bigint  NOT NULL,
    billing_order integer NOT NULL,

    CONSTRAINT pk_movie_cast PRIMARY KEY (movie_id, person_id),
    CONSTRAINT uq_movie_cast_billing_order UNIQUE (movie_id, billing_order),
    CONSTRAINT fk_movie_cast_movie FOREIGN KEY (movie_id)
        REFERENCES catalog.movie (movie_id) ON DELETE CASCADE,
    CONSTRAINT fk_movie_cast_person FOREIGN KEY (person_id)
        REFERENCES catalog.person (person_id),
    CONSTRAINT ck_movie_cast_billing_order CHECK (billing_order >= 1)
);

COMMENT ON TABLE catalog.movie_cast IS
    'Reparto de cada película, en orden de facturación.';

-- Compañías productoras de una película.
CREATE TABLE catalog.movie_production_company (
    movie_id        bigint  NOT NULL,
    company_id      bigint  NOT NULL,
    source_position integer NOT NULL,

    CONSTRAINT pk_movie_production_company PRIMARY KEY (movie_id, company_id),
    CONSTRAINT uq_movie_production_company_position UNIQUE (movie_id, source_position),
    CONSTRAINT fk_movie_production_company_movie FOREIGN KEY (movie_id)
        REFERENCES catalog.movie (movie_id) ON DELETE CASCADE,
    CONSTRAINT fk_movie_production_company_company FOREIGN KEY (company_id)
        REFERENCES catalog.production_company (company_id),
    CONSTRAINT ck_movie_production_company_position CHECK (source_position >= 1)
);

COMMENT ON TABLE catalog.movie_production_company IS
    'Compañías productoras de cada película, en el orden de la fuente.';

-- Países de producción de una película.
CREATE TABLE catalog.movie_production_country (
    movie_id        bigint  NOT NULL,
    country_id      bigint  NOT NULL,
    source_position integer NOT NULL,

    CONSTRAINT pk_movie_production_country PRIMARY KEY (movie_id, country_id),
    CONSTRAINT uq_movie_production_country_position UNIQUE (movie_id, source_position),
    CONSTRAINT fk_movie_production_country_movie FOREIGN KEY (movie_id)
        REFERENCES catalog.movie (movie_id) ON DELETE CASCADE,
    CONSTRAINT fk_movie_production_country_country FOREIGN KEY (country_id)
        REFERENCES catalog.production_country (country_id),
    CONSTRAINT ck_movie_production_country_position CHECK (source_position >= 1)
);

COMMENT ON TABLE catalog.movie_production_country IS
    'Países de producción de cada película, en el orden de la fuente.';

-- Idiomas hablados en una película.
CREATE TABLE catalog.movie_spoken_language (
    movie_id           bigint  NOT NULL,
    spoken_language_id bigint  NOT NULL,
    source_position    integer NOT NULL,

    CONSTRAINT pk_movie_spoken_language PRIMARY KEY (movie_id, spoken_language_id),
    CONSTRAINT uq_movie_spoken_language_position UNIQUE (movie_id, source_position),
    CONSTRAINT fk_movie_spoken_language_movie FOREIGN KEY (movie_id)
        REFERENCES catalog.movie (movie_id) ON DELETE CASCADE,
    CONSTRAINT fk_movie_spoken_language_language FOREIGN KEY (spoken_language_id)
        REFERENCES catalog.spoken_language (spoken_language_id),
    CONSTRAINT ck_movie_spoken_language_position CHECK (source_position >= 1)
);

COMMENT ON TABLE catalog.movie_spoken_language IS
    'Idiomas hablados en cada película, en el orden de la fuente.';

-- Procedencia de los campos de una película: de qué fuente salió cada uno. El
-- código queda abierto, sin catálogo, porque hay familias con parámetros, como
-- wikipedia_infobox_fx:<MONEDA>:<AÑO>; Silver lo descompone (sección 29).
CREATE TABLE catalog.movie_enrichment (
    movie_id   bigint NOT NULL,
    field_name text   NOT NULL,
    code       text   NOT NULL,

    CONSTRAINT pk_movie_enrichment PRIMARY KEY (movie_id, field_name),
    CONSTRAINT fk_movie_enrichment_movie FOREIGN KEY (movie_id)
        REFERENCES catalog.movie (movie_id) ON DELETE CASCADE,
    CONSTRAINT fk_movie_enrichment_field FOREIGN KEY (field_name)
        REFERENCES catalog.enrichment_field (field_name)
);

COMMENT ON TABLE catalog.movie_enrichment IS
    'Procedencia de cada campo de una película, con su código de fuente.';
