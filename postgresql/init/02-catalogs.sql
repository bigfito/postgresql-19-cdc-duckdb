-- =============================================================================
-- ElastiFlix: los 4 catálogos (diseño, secciones 12.15 y 12.18 a 12.20)
-- =============================================================================
-- Tablas de códigos a las que apuntan movie y movie_enrichment. Ninguna se
-- precarga: el simulador inserta cada fila la primera vez que una película la
-- necesita (sección 9.5).
--
-- Tipos según el contrato de la sección 11: text para los códigos. No se usan
-- ENUM ni dominios, para que el catálogo pueda crecer sin cambiar el esquema.
-- No llevan created_at ni updated_at (sección 12.9).

-- Estado de publicación de una película. Hoy el dataset solo trae 'Released'.
CREATE TABLE catalog.movie_status (
    status_code text NOT NULL,
    CONSTRAINT pk_movie_status PRIMARY KEY (status_code)
);

COMMENT ON TABLE catalog.movie_status IS
    'Catálogo de estados de publicación de una película.';

-- Clasificación por edades. Valores documentados: G, PG, PG-13, R, NC-17, NR y
-- TV-PG; el catálogo queda abierto a otros.
CREATE TABLE catalog.content_rating (
    rating_code text NOT NULL,
    CONSTRAINT pk_content_rating PRIMARY KEY (rating_code)
);

COMMENT ON TABLE catalog.content_rating IS
    'Catálogo de clasificaciones por edades.';

-- Idioma original de una película. Códigos de dos letras minúsculas, incluido
-- 'cn', que es una convención de TMDB. description llega NULL: el nombre del
-- idioma lo aporta Silver (sección 24).
CREATE TABLE catalog.original_language (
    language_code text NOT NULL,
    description   text NULL,
    CONSTRAINT pk_original_language PRIMARY KEY (language_code),
    CONSTRAINT ck_original_language_code CHECK (language_code ~ '^[a-z]{2}$')
);

COMMENT ON TABLE catalog.original_language IS
    'Catálogo de idiomas originales, por código de dos letras.';

-- Campos de una película cuya procedencia se registra en movie_enrichment. El
-- dataset documenta 21.
CREATE TABLE catalog.enrichment_field (
    field_name text NOT NULL,
    CONSTRAINT pk_enrichment_field PRIMARY KEY (field_name)
);

COMMENT ON TABLE catalog.enrichment_field IS
    'Catálogo de campos de película con procedencia registrada.';
