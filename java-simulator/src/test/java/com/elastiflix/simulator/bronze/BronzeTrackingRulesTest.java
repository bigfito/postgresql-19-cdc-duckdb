package com.elastiflix.simulator.bronze;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.elastiflix.simulator.error.ErrorCode;
import com.elastiflix.simulator.error.SimulatorException;
import com.elastiflix.simulator.simulation.OperationType;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

/**
 * Reglas del seguimiento hasta Bronze (diseño, secciones 9.3 y 34): cuándo se
 * da un cambio por llegado y cómo se prepara el SQL de inicialización.
 */
class BronzeTrackingRulesTest {

    private static final long REFERENCE = 1_700_000_000_500L;

    // ------------------------------------------------------------------
    // Cuándo ha llegado un cambio
    // ------------------------------------------------------------------

    @Test
    void unaFilaAnteriorAlInstanteDeReferenciaNoCuenta() {
        assertFalse(BronzeMatcher.hasArrived(OperationType.INSERT, REFERENCE, "+I", REFERENCE - 1));
        assertFalse(BronzeMatcher.hasArrived(OperationType.UPDATE, REFERENCE, "+U", REFERENCE - 1));
        assertFalse(BronzeMatcher.hasArrived(OperationType.DELETE, REFERENCE, "-D", REFERENCE - 1));
    }

    /** El commit cae a menudo en el mismo milisegundo que el inicio de la transacción. */
    @Test
    void unaFilaEnElMismoMilisegundoCuenta() {
        assertTrue(BronzeMatcher.hasArrived(OperationType.INSERT, REFERENCE, "+I", REFERENCE));
        assertTrue(BronzeMatcher.hasArrived(OperationType.UPDATE, REFERENCE, "+U", REFERENCE));
    }

    @Test
    void unaFilaPosteriorCuenta() {
        assertTrue(BronzeMatcher.hasArrived(OperationType.INSERT, REFERENCE, "+I", REFERENCE + 40));
        assertTrue(BronzeMatcher.hasArrived(OperationType.UPDATE, REFERENCE, "+U", REFERENCE + 40));
    }

    @Test
    void unDeleteLlegaCuandoApareceElTombstone() {
        assertTrue(BronzeMatcher.hasArrived(OperationType.DELETE, REFERENCE, "-D", REFERENCE));
        assertTrue(BronzeMatcher.hasArrived(OperationType.DELETE, REFERENCE, "-D", REFERENCE + 12));
    }

    @Test
    void unDeleteNoSeConfundeConLaFilaPreviaDelMismoMilisegundo() {
        assertFalse(BronzeMatcher.hasArrived(OperationType.DELETE, REFERENCE, "+U", REFERENCE));
    }

    @Test
    void unDeleteSeguidoDeUnaReinsercionTambienHaLlegado() {
        assertTrue(BronzeMatcher.hasArrived(OperationType.DELETE, REFERENCE, "+I", REFERENCE + 300));
    }

    // ------------------------------------------------------------------
    // SQL de inicialización
    // ------------------------------------------------------------------

    private static final String SCRIPT = """
            -- Comentario de cabecera
            SET extension_directory = '/opt/duckdb_extensions';
            LOAD httpfs;

              -- Comentario con sangría
            CREATE OR REPLACE SECRET rustfs (
                TYPE s3,
                KEY_ID '${AWS_ACCESS_KEY_ID}',
                SECRET '${AWS_SECRET_ACCESS_KEY}'
            );
            """;

    @Test
    void parteElScriptEnSentenciasSinComentarios() {
        List<String> statements = InitSqlScript.statements(SCRIPT,
                Map.of("AWS_ACCESS_KEY_ID", "clave", "AWS_SECRET_ACCESS_KEY", "secreto"));

        assertEquals(3, statements.size());
        assertEquals("SET extension_directory = '/opt/duckdb_extensions'", statements.get(0));
        assertEquals("LOAD httpfs", statements.get(1));
        assertTrue(statements.get(2).startsWith("CREATE OR REPLACE SECRET rustfs"));
        assertTrue(statements.stream().noneMatch(statement -> statement.contains("--")));
    }

    @Test
    void sustituyeLosMarcadoresPorSusValores() {
        List<String> statements = InitSqlScript.statements(SCRIPT,
                Map.of("AWS_ACCESS_KEY_ID", "clave", "AWS_SECRET_ACCESS_KEY", "secreto"));

        assertTrue(statements.get(2).contains("KEY_ID 'clave'"));
        assertTrue(statements.get(2).contains("SECRET 'secreto'"));
    }

    @Test
    void unaComillaEnUnValorNoRompeLaSentencia() {
        List<String> statements = InitSqlScript.statements(SCRIPT,
                Map.of("AWS_ACCESS_KEY_ID", "cla've", "AWS_SECRET_ACCESS_KEY", "secreto"));

        assertTrue(statements.get(2).contains("KEY_ID 'cla''ve'"));
    }

    @Test
    void unMarcadorSinValorEsUnError() {
        SimulatorException error = assertThrows(SimulatorException.class,
                () -> InitSqlScript.statements(SCRIPT, Map.of("AWS_ACCESS_KEY_ID", "clave")));

        assertEquals(ErrorCode.BRONZE_INIT_SQL, error.errorCode());
    }
}
