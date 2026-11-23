package com.elastiflix.simulator.config;

/**
 * Credenciales que el simulador recibe por variables de entorno (diseño,
 * sección 45.5). Nunca se escriben en el log: {@link #toString()} las oculta.
 *
 * @param postgresPassword   contraseña de la cuenta {@code elastiflix_app}
 * @param awsAccessKeyId     clave de acceso de RustFS; vacía si no hay seguimiento
 * @param awsSecretAccessKey clave secreta de RustFS; vacía si no hay seguimiento
 */
public record Credentials(String postgresPassword, String awsAccessKeyId, String awsSecretAccessKey) {

    @Override
    public String toString() {
        return "Credentials[ocultas]";
    }
}
