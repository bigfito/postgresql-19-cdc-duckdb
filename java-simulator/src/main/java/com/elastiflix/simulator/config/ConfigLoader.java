package com.elastiflix.simulator.config;

import com.elastiflix.simulator.error.ErrorCode;
import com.elastiflix.simulator.error.SimulatorException;

import java.util.Map;
import java.util.regex.Pattern;

/**
 * Lee la configuración del simulador desde las variables de entorno (diseño,
 * sección 9.6). Una variable ausente o vacía toma su valor por defecto; un
 * valor que no se entiende detiene el arranque con un error claro.
 */
public final class ConfigLoader {

    private static final Pattern MEMORY_LIMIT = Pattern.compile("\\d+(\\.\\d+)?\\s?(KB|MB|GB|KiB|MiB|GiB)");

    private final Map<String, String> environment;

    /**
     * @param environment variables de entorno; en producción, {@link System#getenv()}
     */
    public ConfigLoader(Map<String, String> environment) {
        this.environment = environment;
    }

    /**
     * @return la configuración, ya validada
     * @throws SimulatorException con {@link ErrorCode#CONFIG_INVALID} si algo no es válido
     */
    public SimulatorConfig load() {
        boolean trackBronze = booleanValue("SIMULATOR_TRACK_BRONZE", true);
        return new SimulatorConfig(
                longValue("SIMULATOR_DELAY_MS", 250, 0),
                loadWeights(),
                longValue("SIMULATOR_RANDOM_SEED", 42, Long.MIN_VALUE),
                booleanValue("SIMULATOR_CONTINUOUS", true),
                booleanValue("SIMULATOR_AUTOSTART", true),
                trackBronze,
                longValue("SIMULATOR_TRACK_INTERVAL_MS", 5_000, 100),
                longValue("SIMULATOR_TRACK_LATE_MS", 120_000, 1_000),
                (int) longValue("SIMULATOR_DUCKDB_THREADS", 2, 1),
                memoryLimit(),
                loadCredentials(trackBronze));
    }

    private Weights loadWeights() {
        return new Weights(
                (int) longValue("SIMULATOR_INSERT_WEIGHT", 70, 0),
                (int) longValue("SIMULATOR_UPDATE_WEIGHT", 25, 0),
                (int) longValue("SIMULATOR_DELETE_WEIGHT", 5, 0));
    }

    private Credentials loadCredentials(boolean trackBronze) {
        String postgresPassword = required("ELASTIFLIX_APP_PASSWORD");
        if (!trackBronze) {
            return new Credentials(postgresPassword, "", "");
        }
        return new Credentials(postgresPassword, required("AWS_ACCESS_KEY_ID"), required("AWS_SECRET_ACCESS_KEY"));
    }

    private String memoryLimit() {
        String value = text("SIMULATOR_DUCKDB_MEMORY_LIMIT", "128MB");
        if (!MEMORY_LIMIT.matcher(value).matches()) {
            throw invalid("SIMULATOR_DUCKDB_MEMORY_LIMIT", value, "una cantidad con unidad, como 128MB");
        }
        return value;
    }

    private long longValue(String name, long defaultValue, long minimum) {
        String value = text(name, null);
        if (value == null) {
            return defaultValue;
        }
        try {
            long parsed = Long.parseLong(value);
            if (parsed < minimum) {
                throw invalid(name, value, "un entero mayor o igual que " + minimum);
            }
            return parsed;
        } catch (NumberFormatException e) {
            throw invalid(name, value, "un número entero");
        }
    }

    private boolean booleanValue(String name, boolean defaultValue) {
        String value = text(name, null);
        if (value == null) {
            return defaultValue;
        }
        if (value.equalsIgnoreCase("true")) {
            return true;
        }
        if (value.equalsIgnoreCase("false")) {
            return false;
        }
        throw invalid(name, value, "true o false");
    }

    private String required(String name) {
        String value = text(name, null);
        if (value == null) {
            throw new SimulatorException(ErrorCode.CONFIG_INVALID, "falta la variable " + name);
        }
        return value;
    }

    /** Una variable vacía cuenta como ausente. */
    private String text(String name, String defaultValue) {
        String value = environment.get(name);
        if (value == null || value.isBlank()) {
            return defaultValue;
        }
        return value.trim();
    }

    private static SimulatorException invalid(String name, String value, String expected) {
        return new SimulatorException(ErrorCode.CONFIG_INVALID,
                name + "=" + value + " no es válido; se esperaba " + expected);
    }
}
