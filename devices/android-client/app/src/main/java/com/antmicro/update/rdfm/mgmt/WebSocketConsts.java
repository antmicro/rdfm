package com.antmicro.update.rdfm.mgmt;

/**
 * WebSocket status codes
 * <a href="https://www.rfc-editor.org/rfc/rfc6455.html#section-7.4.1">RFC</a>
 */
public class WebSocketConsts {
    /**
     * No error (normal close)
     */
    public static final int WS_CLOSE_NORMAL_CLOSURE = 1000;

    /**
     * Invalid encoding
     */
    public static final int WS_CLOSE_INVALID_ENCODING = 1003;

}
