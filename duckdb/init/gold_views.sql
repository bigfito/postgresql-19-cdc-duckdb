-- =============================================================================
-- ElastiFlix: vistas de consumo de Gold en DuckDB (diseño, secciones 34 y 35)
-- =============================================================================
-- Una vista por producto de Gold, en la base en memoria de DuckDB, con el
-- mismo nombre que la tabla. Los datasets de Superset se definen sobre estas
-- vistas, que su interfaz muestra en el esquema memory.main (decisión 68).
-- La validación 7 vio que Superset no leía las columnas de una tabla Iceberg
-- adjunta. En la fase F10 sí las leyó, y las vistas se mantienen como el
-- camino comprobado.
--
-- Se ejecuta después de attach_lakehouse.sql, que adjunta el catálogo con el
-- nombre lake. Como la base vive en memoria, hay que repetirlo en cada
-- conexión.
--
-- Quién lo usa:
--   - Superset, en cada conexión. Su configuración ejecuta de este archivo
--     solo las vistas cuya tabla ya existe en Gold: una vista sobre una tabla
--     que todavía no existe haría fallar la conexión.
--   - El contenedor de línea de comandos, a mano y cuando Gold ya existe.
-- El Event Simulator no lo usa.
--
-- Reglas para quien edite este archivo:
--   - Una sentencia por producto y una vista por sentencia, siempre con la
--     forma CREATE OR REPLACE VIEW memory.main.<producto> AS SELECT * FROM
--     lake.gold.<producto>. Superset saca el nombre del producto de ahí.
--   - Ningún comentario puede llevar punto y coma. Quien lo ejecuta descarta
--     las líneas de comentario y parte el resto por ese carácter.
--   - Los comentarios van en líneas propias, nunca al final de una sentencia.

-- Ficha completa de cada película viva.
CREATE OR REPLACE VIEW memory.main.movie_current_overview AS SELECT * FROM lake.gold.movie_current_overview;

-- Géneros: volumen, dinero y valoración.
CREATE OR REPLACE VIEW memory.main.genre_performance AS SELECT * FROM lake.gold.genre_performance;

-- Colecciones o sagas.
CREATE OR REPLACE VIEW memory.main.collection_performance AS SELECT * FROM lake.gold.collection_performance;

-- Películas con presupuesto y recaudación.
CREATE OR REPLACE VIEW memory.main.financial_performance AS SELECT * FROM lake.gold.financial_performance;

-- Estrenos por mes.
CREATE OR REPLACE VIEW memory.main.release_trends AS SELECT * FROM lake.gold.release_trends;

-- Personas del reparto.
CREATE OR REPLACE VIEW memory.main.cast_analysis AS SELECT * FROM lake.gold.cast_analysis;

-- Cobertura de los datos.
CREATE OR REPLACE VIEW memory.main.data_quality_coverage AS SELECT * FROM lake.gold.data_quality_coverage;
