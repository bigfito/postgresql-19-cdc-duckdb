-- =============================================================================
-- ElastiFlix: esquema operacional (diseño, sección 10)
-- =============================================================================
-- La imagen oficial de PostgreSQL ejecuta los archivos de este directorio una
-- sola vez, en orden alfabético, cuando postgresql/data/ está vacío, sobre la
-- base indicada en POSTGRES_DB (elastiflix) y deteniéndose en el primer error.
--
-- Todas las tablas del modelo relacional viven en el esquema catalog y se
-- nombran siempre con el esquema por delante.

CREATE SCHEMA catalog;

COMMENT ON SCHEMA catalog IS
    'Modelo operacional normalizado de ElastiFlix: 20 tablas capturadas por CDC.';
