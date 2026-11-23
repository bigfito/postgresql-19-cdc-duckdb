package com.elastiflix.simulator.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.elastiflix.simulator.error.ErrorCode;
import com.elastiflix.simulator.error.SimulatorException;

import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;

/**
 * Lectura de la configuración desde variables de entorno (diseño, sección 9.6).
 */
class ConfigLoaderTest {

    @Test
    void sinVariablesUsaLosValoresPorDefectoDelDiseno() {
        SimulatorConfig config = new ConfigLoader(required()).load();

        assertEquals(250, config.delayMillis());
        assertEquals(new Weights(70, 25, 5), config.weights());
        assertEquals(42, config.randomSeed());
        assertTrue(config.continuous());
        assertTrue(config.autostart());
        assertTrue(config.trackBronze());
        assertEquals(5_000, config.trackIntervalMillis());
        assertEquals(120_000, config.trackLateMillis());
        assertEquals(2, config.duckdbThreads());
        assertEquals("128MB", config.duckdbMemoryLimit());
    }

    @Test
    void leeCadaVariable() {
        Map<String, String> environment = required();
        environment.put("SIMULATOR_DELAY_MS", "1000");
        environment.put("SIMULATOR_INSERT_WEIGHT", "10");
        environment.put("SIMULATOR_UPDATE_WEIGHT", "20");
        environment.put("SIMULATOR_DELETE_WEIGHT", "30");
        environment.put("SIMULATOR_RANDOM_SEED", "-7");
        environment.put("SIMULATOR_CONTINUOUS", "false");
        environment.put("SIMULATOR_AUTOSTART", "FALSE");
        environment.put("SIMULATOR_TRACK_INTERVAL_MS", "2000");
        environment.put("SIMULATOR_TRACK_LATE_MS", "60000");
        environment.put("SIMULATOR_DUCKDB_THREADS", "4");
        environment.put("SIMULATOR_DUCKDB_MEMORY_LIMIT", "256MB");

        SimulatorConfig config = new ConfigLoader(environment).load();

        assertEquals(1_000, config.delayMillis());
        assertEquals(new Weights(10, 20, 30), config.weights());
        assertEquals(-7, config.randomSeed());
        assertFalse(config.continuous());
        assertFalse(config.autostart());
        assertEquals(2_000, config.trackIntervalMillis());
        assertEquals(60_000, config.trackLateMillis());
        assertEquals(4, config.duckdbThreads());
        assertEquals("256MB", config.duckdbMemoryLimit());
    }

    @Test
    void unaVariableVaciaCuentaComoAusente() {
        Map<String, String> environment = required();
        environment.put("SIMULATOR_DELAY_MS", "  ");

        assertEquals(250, new ConfigLoader(environment).load().delayMillis());
    }

    @Test
    void rechazaUnValorQueNoEsNumero() {
        assertInvalid("SIMULATOR_DELAY_MS", "rápido");
    }

    @Test
    void rechazaUnPesoNegativo() {
        assertInvalid("SIMULATOR_INSERT_WEIGHT", "-1");
    }

    @Test
    void rechazaUnBooleanoMalEscrito() {
        assertInvalid("SIMULATOR_CONTINUOUS", "sí");
    }

    @Test
    void rechazaUnLimiteDeMemoriaSinUnidad() {
        assertInvalid("SIMULATOR_DUCKDB_MEMORY_LIMIT", "128");
    }

    @Test
    void rechazaTodosLosPesosACero() {
        Map<String, String> environment = required();
        environment.put("SIMULATOR_INSERT_WEIGHT", "0");
        environment.put("SIMULATOR_UPDATE_WEIGHT", "0");
        environment.put("SIMULATOR_DELETE_WEIGHT", "0");

        SimulatorException error = assertThrows(SimulatorException.class, () -> new ConfigLoader(environment).load());

        assertEquals(ErrorCode.CONFIG_INVALID, error.errorCode());
    }

    @Test
    void exigeLaContrasenaDePostgres() {
        Map<String, String> environment = required();
        environment.remove("ELASTIFLIX_APP_PASSWORD");

        SimulatorException error = assertThrows(SimulatorException.class, () -> new ConfigLoader(environment).load());

        assertTrue(error.getMessage().contains("ELASTIFLIX_APP_PASSWORD"));
    }

    @Test
    void sinSeguimientoNoExigeLasClavesDeRustfs() {
        Map<String, String> environment = new HashMap<>();
        environment.put("ELASTIFLIX_APP_PASSWORD", "una-contraseña");
        environment.put("SIMULATOR_TRACK_BRONZE", "false");

        assertFalse(new ConfigLoader(environment).load().trackBronze());
    }

    @Test
    void lasCredencialesNoAparecenAlImprimirLaConfiguracion() {
        SimulatorConfig config = new ConfigLoader(required()).load();

        assertFalse(config.toString().contains("una-contraseña"));
        assertFalse(config.toString().contains("clave-secreta"));
    }

    private static void assertInvalid(String name, String value) {
        Map<String, String> environment = required();
        environment.put(name, value);

        SimulatorException error = assertThrows(SimulatorException.class, () -> new ConfigLoader(environment).load());

        assertEquals(ErrorCode.CONFIG_INVALID, error.errorCode());
        assertTrue(error.getMessage().contains(name), error.getMessage());
    }

    /** Las variables sin valor por defecto, con valores de prueba. */
    private static Map<String, String> required() {
        Map<String, String> environment = new HashMap<>();
        environment.put("ELASTIFLIX_APP_PASSWORD", "una-contraseña");
        environment.put("AWS_ACCESS_KEY_ID", "clave-de-acceso");
        environment.put("AWS_SECRET_ACCESS_KEY", "clave-secreta");
        return environment;
    }
}
