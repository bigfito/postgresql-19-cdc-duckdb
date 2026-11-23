-- =============================================================================
-- ElastiFlix: las 7 entidades compartidas (diseño, secciones 12.3, 12.5, 12.7,
-- 12.9, 12.11, 12.13 y 12.16)
-- =============================================================================
-- Entidades que varias películas comparten. Borrar una película no las borra
-- (sección 13). Ninguna se precarga: el simulador inserta cada fila la primera
-- vez que una película la necesita (sección 9.5).
--
-- Claves: bigint, siempre con el valor que trae el dataset. PostgreSQL no
-- genera ninguna, por eso no hay secuencias ni columnas de identidad
-- (sección 8.4).
--
-- Fechas: solo las tablas que el simulador modifica, collection y keyword,
-- llevan created_at y updated_at; person lleva únicamente created_at. Las
-- asigna PostgreSQL con now(), y el simulador actualiza updated_at en cada
-- UPDATE: no hay trigger (secciones 9.5 y 12.9).

-- Colección o saga. El nombre no es único: hay identificadores distintos con
-- el mismo nombre. El simulador la renombra en el UPDATE de catálogo.
CREATE TABLE catalog.collection (
    collection_id bigint NOT NULL,
    name          text   NOT NULL,
    created_at    timestamp(6) with time zone NOT NULL DEFAULT now(),
    updated_at    timestamp(6) with time zone NOT NULL DEFAULT now(),
    CONSTRAINT pk_collection PRIMARY KEY (collection_id)
);

COMMENT ON TABLE catalog.collection IS
    'Colecciones o sagas. Clave natural de TMDB; el nombre puede repetirse.';

-- Género. Clave sustituta asignada por el dataset.
CREATE TABLE catalog.genre (
    genre_id bigint NOT NULL,
    name     text   NOT NULL,
    CONSTRAINT pk_genre PRIMARY KEY (genre_id),
    CONSTRAINT uq_genre_name UNIQUE (name)
);

COMMENT ON TABLE catalog.genre IS
    'Géneros. Clave sustituta asignada por el dataset.';

-- Palabra clave. El nombre no es único: el dataset trae nombres compartidos
-- por dos identificadores (sección 8.6). El simulador la renombra en el UPDATE
-- de catálogo.
CREATE TABLE catalog.keyword (
    keyword_id bigint NOT NULL,
    name       text   NOT NULL,
    created_at timestamp(6) with time zone NOT NULL DEFAULT now(),
    updated_at timestamp(6) with time zone NOT NULL DEFAULT now(),
    CONSTRAINT pk_keyword PRIMARY KEY (keyword_id)
);

COMMENT ON TABLE catalog.keyword IS
    'Palabras clave. Clave natural de TMDB; el nombre puede repetirse.';

-- Persona del reparto. La unicidad del nombre es técnica, por nombre exacto
-- del dataset; no resuelve homónimos reales.
CREATE TABLE catalog.person (
    person_id  bigint NOT NULL,
    name       text   NOT NULL,
    created_at timestamp(6) with time zone NOT NULL DEFAULT now(),
    CONSTRAINT pk_person PRIMARY KEY (person_id),
    CONSTRAINT uq_person_name UNIQUE (name)
);

COMMENT ON TABLE catalog.person IS
    'Personas del reparto. Clave sustituta asignada por el dataset.';

-- Compañía productora. Las variantes del nombre de un mismo estudio no se
-- fusionan.
CREATE TABLE catalog.production_company (
    company_id bigint NOT NULL,
    name       text   NOT NULL,
    CONSTRAINT pk_production_company PRIMARY KEY (company_id),
    CONSTRAINT uq_production_company_name UNIQUE (name)
);

COMMENT ON TABLE catalog.production_company IS
    'Compañías productoras. Clave sustituta asignada por el dataset.';

-- País de producción. Se conserva el valor fuente aunque tenga defectos de
-- calidad, como 'Guadaloupe'; estandarizarlo es tarea de Silver.
CREATE TABLE catalog.production_country (
    country_id bigint NOT NULL,
    name       text   NOT NULL,
    CONSTRAINT pk_production_country PRIMARY KEY (country_id),
    CONSTRAINT uq_production_country_name UNIQUE (name)
);

COMMENT ON TABLE catalog.production_country IS
    'Países de producción, con el nombre tal como llega de la fuente.';

-- Idioma hablado. 'No Language' es un valor válido, no una ausencia.
CREATE TABLE catalog.spoken_language (
    spoken_language_id bigint NOT NULL,
    name               text   NOT NULL,
    CONSTRAINT pk_spoken_language PRIMARY KEY (spoken_language_id),
    CONSTRAINT uq_spoken_language_name UNIQUE (name)
);

COMMENT ON TABLE catalog.spoken_language IS
    'Idiomas hablados, por nombre. Clave sustituta asignada por el dataset.';
