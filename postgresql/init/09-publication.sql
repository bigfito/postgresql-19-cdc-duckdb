-- =============================================================================
-- ElastiFlix: publicación para Flink CDC (diseño, secciones 10 y 14)
-- =============================================================================
-- Flink CDC lee el WAL con el plugin pgoutput, que solo entrega los cambios de
-- las tablas incluidas en una publicación.
--
-- Se crea aquí, con el superusuario, y no la crea el conector: la cuenta
-- elastiflix_cdc no puede crear publicaciones, y el pipeline lleva
-- publication.autocreate.mode en 'disabled' (sección 14).
--
-- FOR TABLES IN SCHEMA incluye las 20 tablas de catalog y cualquier tabla que
-- se añada después al esquema. Publica INSERT, UPDATE, DELETE y TRUNCATE, que
-- es el comportamiento por defecto.
--
-- El slot de replicación elastiflix_cdc no se crea aquí: lo crea el conector la
-- primera vez que arranca el pipeline.

CREATE PUBLICATION elastiflix_pub FOR TABLES IN SCHEMA catalog;

COMMENT ON PUBLICATION elastiflix_pub IS
    'Cambios de las tablas del esquema catalog, para Flink CDC.';
