-- =============================================================================
-- ElastiFlix: REPLICA IDENTITY FULL en las 20 tablas (diseño, sección 10)
-- =============================================================================
-- Con la identidad por defecto, el WAL de un UPDATE o de un DELETE solo lleva
-- la clave primaria de la fila anterior. El pipeline de Flink CDC convierte
-- cada DELETE en un tombstone con la fila completa (sección 14), así que
-- necesita todas las columnas en el evento de borrado. No es opcional.
--
-- El coste es un WAL algo mayor en cada UPDATE y DELETE, asumible con el
-- volumen de este laboratorio.

-- Catálogos.
ALTER TABLE catalog.movie_status             REPLICA IDENTITY FULL;
ALTER TABLE catalog.content_rating           REPLICA IDENTITY FULL;
ALTER TABLE catalog.original_language        REPLICA IDENTITY FULL;
ALTER TABLE catalog.enrichment_field         REPLICA IDENTITY FULL;

-- Entidades compartidas.
ALTER TABLE catalog.collection               REPLICA IDENTITY FULL;
ALTER TABLE catalog.genre                    REPLICA IDENTITY FULL;
ALTER TABLE catalog.keyword                  REPLICA IDENTITY FULL;
ALTER TABLE catalog.person                   REPLICA IDENTITY FULL;
ALTER TABLE catalog.production_company       REPLICA IDENTITY FULL;
ALTER TABLE catalog.production_country       REPLICA IDENTITY FULL;
ALTER TABLE catalog.spoken_language          REPLICA IDENTITY FULL;

-- Película y relaciones.
ALTER TABLE catalog.movie                    REPLICA IDENTITY FULL;
ALTER TABLE catalog.movie_collection         REPLICA IDENTITY FULL;
ALTER TABLE catalog.movie_genre              REPLICA IDENTITY FULL;
ALTER TABLE catalog.movie_keyword            REPLICA IDENTITY FULL;
ALTER TABLE catalog.movie_cast               REPLICA IDENTITY FULL;
ALTER TABLE catalog.movie_production_company REPLICA IDENTITY FULL;
ALTER TABLE catalog.movie_production_country REPLICA IDENTITY FULL;
ALTER TABLE catalog.movie_spoken_language    REPLICA IDENTITY FULL;
ALTER TABLE catalog.movie_enrichment         REPLICA IDENTITY FULL;

-- Comprobación: ninguna tabla de catalog puede quedarse sin la identidad
-- completa. Si alguien añade una tabla y olvida su línea aquí, la
-- inicialización se detiene en lugar de dejar un DELETE sin fila completa.
DO $$
DECLARE
    missing text;
BEGIN
    SELECT string_agg(c.relname, ', ' ORDER BY c.relname)
      INTO missing
      FROM pg_class c
     WHERE c.relnamespace = 'catalog'::regnamespace
       AND c.relkind = 'r'
       AND c.relreplident <> 'f';
    IF missing IS NOT NULL THEN
        RAISE EXCEPTION 'Tablas de catalog sin REPLICA IDENTITY FULL: %', missing;
    END IF;
END
$$;
