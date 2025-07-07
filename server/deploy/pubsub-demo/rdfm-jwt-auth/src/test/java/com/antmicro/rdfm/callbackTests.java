package com.antmicro.rdfm;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import com.auth0.jwt.algorithms.Algorithm;
import com.auth0.jwt.JWT;

import java.time.Instant;

import javax.security.auth.callback.Callback;
import javax.security.auth.callback.NameCallback;
import org.apache.kafka.common.security.plain.PlainAuthenticateCallback;

public class callbackTests {
    private static final Algorithm algorithm = Algorithm.HMAC256(System.getenv("RDFM_JWT_SECRET"));
    private static final String mockDeviceMAC = "00:00:00:00:00:00";

    private static String token;
    private static String expiredToken;

    private NameCallback nameCallback;
    private PlainAuthenticateCallback plainCallback;
    private DeviceAuthenticateCallbackHandler handler;

    @BeforeAll
    public static void setupCallbackTestsTokens() {
        long currentUnixUTC = Instant.now().getEpochSecond();

        token = JWT.create()
            .withClaim("device_id", mockDeviceMAC)
            .withClaim("created_at", currentUnixUTC)
            .withClaim("expires", 100)
            .sign(algorithm);

        expiredToken = JWT.create()
            .withClaim("device_id", mockDeviceMAC)
            .withClaim("created_at", currentUnixUTC - 101)
            .withClaim("expires", 100)
            .sign(algorithm);
    }

    @BeforeEach
    public void setupCallbackTestsCallbacks() {
        nameCallback = new NameCallback("dummy", mockDeviceMAC);
        plainCallback = new PlainAuthenticateCallback(token.toCharArray());
        handler = new DeviceAuthenticateCallbackHandler();
    }

    @Test
    public void shouldFailNoConfigure() {
        boolean handleFailed = false;
        Callback[] array = {plainCallback, nameCallback};

        try {
            handler.handle(array);
        } catch(Exception e) {
            handleFailed = true;
            assertInstanceOf(IllegalStateException.class, e);
        }
        assertTrue(handleFailed);
    }

    @Test
    public void shouldSucceedValidToken() {
        boolean handleFailed = false;
        Callback[] array = {plainCallback, nameCallback};

        try {
            handler.configure(null, "PLAIN", null);
            handler.handle(array);
        } catch(Exception e) {
            handleFailed = true;
        }
        assertFalse(handleFailed);
        assertTrue(plainCallback.authenticated());
    }

    @Test
    public void shouldFailExpiredToken() {
        boolean handleFailed = false;
        PlainAuthenticateCallback expiredPlainCallback = new PlainAuthenticateCallback(expiredToken.toCharArray());
        Callback[] array = {expiredPlainCallback, nameCallback};
        try {
            handler.configure(null, "PLAIN", null);
            handler.handle(array);
        } catch (Exception e) {
            handleFailed = true;
        }
        assertFalse(handleFailed);
        assertFalse(plainCallback.authenticated());
    }
}
