-- =============================================================================
-- ElastiFlix: cuentas técnicas del PostgreSQL operacional (diseño, secciones 10
-- y 45.3)
-- =============================================================================
-- Cada servicio usa una cuenta propia con el mínimo privilegio que necesita.
-- Ninguna es superusuario ni dueña de las tablas, que pertenecen a postgres.
--
-- Las cuentas se crean aquí sin contraseña. Mientras no la tengan no pueden
-- entrar desde la red, porque la imagen exige scram-sha-256 a toda conexión
-- que no nace dentro del propio contenedor. La contraseña la pone el script
-- siguiente, leyéndola de variables de entorno: así no queda escrita en ningún
-- archivo versionado (sección 45.5).
--
-- Este archivo va después de los que crean las tablas, porque los permisos se
-- conceden sobre las tablas que ya existen.

-- -----------------------------------------------------------------------------
-- elastiflix_app: la aplicación transaccional, es decir, el Event Simulator
-- -----------------------------------------------------------------------------
-- Lee y modifica datos en catalog. No puede crear, alterar ni vaciar tablas.
CREATE ROLE elastiflix_app LOGIN;

COMMENT ON ROLE elastiflix_app IS
    'Event Simulator: SELECT, INSERT, UPDATE y DELETE sobre el esquema catalog.';

GRANT USAGE ON SCHEMA catalog TO elastiflix_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA catalog TO elastiflix_app;

-- -----------------------------------------------------------------------------
-- elastiflix_cdc: Flink CDC
-- -----------------------------------------------------------------------------
-- REPLICATION le permite crear su slot y leer el WAL; SELECT, tomar el snapshot
-- inicial. No modifica datos. La validación 1 comprobó que con esto basta, sin
-- superusuario, siempre que la publicación ya exista.
CREATE ROLE elastiflix_cdc LOGIN REPLICATION;

COMMENT ON ROLE elastiflix_cdc IS
    'Flink CDC: REPLICATION y SELECT sobre el esquema catalog.';

GRANT USAGE ON SCHEMA catalog TO elastiflix_cdc;
GRANT SELECT ON ALL TABLES IN SCHEMA catalog TO elastiflix_cdc;
