-- =============================================================================
-- ElastiFlix: inicialización de una conexión de DuckDB (diseño, sección 34)
-- =============================================================================
-- DuckDB corre embebido y en memoria, así que cada conexión nueva empieza de
-- cero y debe ejecutar este archivo: carga las extensiones, declara el acceso
-- a RustFS y adjunta el catálogo Iceberg con el nombre lake.
--
-- Lo usan Superset, el contenedor de línea de comandos y el Event Simulator,
-- que lo montan en solo lectura. Las vistas de consumo de Gold no están aquí:
-- van en gold_views.sql, que el simulador no usa.
--
-- Reglas para quien edite este archivo:
--   - Ningún comentario puede llevar punto y coma. Quien lo ejecuta descarta
--     las líneas de comentario y parte el resto por ese carácter.
--   - Los comentarios van en líneas propias, nunca al final de una sentencia.
--   - No se escriben claves. Los marcadores ${AWS_ACCESS_KEY_ID} y
--     ${AWS_SECRET_ACCESS_KEY} se sustituyen por las variables de entorno del
--     contenedor justo antes de ejecutar.

-- Las extensiones httpfs, iceberg y avro se instalan durante el build de cada
-- imagen en este directorio. Aquí solo se cargan. Con la instalación
-- automática desactivada, una extensión ausente es un error visible y no una
-- descarga silenciosa. iceberg carga avro por su cuenta desde el mismo
-- directorio.
SET extension_directory = '/opt/duckdb_extensions';
SET autoinstall_known_extensions = false;
LOAD httpfs;
LOAD iceberg;

-- Acceso a RustFS con la clave única del laboratorio, por el endpoint interno
-- de la red del Compose, con direcciones path-style y sin TLS.
CREATE OR REPLACE SECRET rustfs (
    TYPE s3,
    KEY_ID '${AWS_ACCESS_KEY_ID}',
    SECRET '${AWS_SECRET_ACCESS_KEY}',
    ENDPOINT 'rustfs:9000',
    URL_STYLE 'path',
    USE_SSL false
);

-- Catálogo REST de Iceberg. No pide credenciales. Sus tablas quedan como
-- lake.bronze.<tabla>, lake.silver.<tabla> y lake.gold.<tabla>.
ATTACH 'warehouse' AS lake (
    TYPE iceberg,
    ENDPOINT 'http://iceberg-rest:8181',
    AUTHORIZATION_TYPE 'none'
);
