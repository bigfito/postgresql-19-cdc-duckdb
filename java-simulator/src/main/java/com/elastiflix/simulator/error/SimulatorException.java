package com.elastiflix.simulator.error;

/**
 * Excepción propia del simulador. Siempre lleva un {@link ErrorCode}, de modo
 * que su mensaje explica qué pasó y qué hacer.
 */
public class SimulatorException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    private final ErrorCode errorCode;

    /**
     * @param errorCode código que clasifica el error
     * @param detail    lo concreto de este caso
     */
    public SimulatorException(ErrorCode errorCode, String detail) {
        super(errorCode.message(detail));
        this.errorCode = errorCode;
    }

    /**
     * @param errorCode código que clasifica el error
     * @param detail    lo concreto de este caso
     * @param cause     excepción original
     */
    public SimulatorException(ErrorCode errorCode, String detail, Throwable cause) {
        super(errorCode.message(detail), cause);
        this.errorCode = errorCode;
    }

    /** @return el código que clasifica el error */
    public ErrorCode errorCode() {
        return errorCode;
    }
}
