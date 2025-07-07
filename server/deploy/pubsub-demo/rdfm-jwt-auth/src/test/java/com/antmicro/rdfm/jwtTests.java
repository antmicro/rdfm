package com.antmicro.rdfm;

import com.auth0.jwt.algorithms.Algorithm;
import com.auth0.jwt.JWT;
import com.auth0.jwt.JWTVerifier;
import com.auth0.jwt.exceptions.*;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

public class jwtTests {
    private static final Algorithm algorithm = Algorithm.HMAC256(System.getenv("RDFM_JWT_SECRET"));
    private static final long mockUnixTime = 1747982498;
    private static final String mockDeviceMAC = "00:00:00:00:00:00";

    private static String token;
    private static String malformedToken;

    @BeforeAll
    public static void setupJWTTest() {
        token = JWT.create()
            .withClaim("device_id", mockDeviceMAC)
            .withClaim("created_at", mockUnixTime)
            .withClaim("expires", 100)
            .sign(algorithm);

        malformedToken = JWT.create()
            .withClaim("device_id", mockDeviceMAC)
            .withClaim("created", mockUnixTime) /* This is wrong */
            .withClaim("expires", 100)
            .sign(algorithm);
    }

    /*
     * We're not making use of the `exp` claim so this won't raise
     * TokenExpiredException. We're checking our custom fields
     * manually with a lambda expression inside a `withClaim` method.
     */
    @Test
    public void shouldFaiExpiry() {
        long expiredTimestamp = mockUnixTime + 101;
        boolean verifyFailed = false;
        try {
            JWTVerifier verifier = JWT.require(algorithm)
                .withClaim("device_id", "00:00:00:00:00:00")
                .withClaimPresence("created_at")
                .withClaimPresence("expires")
                .withClaim("created_at", (claim, jwt) -> expiredTimestamp <= claim.asLong() + jwt.getClaim("expires").asLong())
                .build();
            verifier.verify(token);
        } catch (Exception e) {
            verifyFailed = true;
            assertInstanceOf(IncorrectClaimException.class, e);
        }
        assertTrue(verifyFailed);
    }

    /*
     * malformedToken does not have the `created_at` field.
     */
    @Test
    public void shouldFailMissing() {
        boolean verifyFailed = false;
        try {
            JWTVerifier verifier = JWT.require(algorithm)
                .withClaim("device_id", "00:00:00:00:00:00")
                .withClaimPresence("created_at") /* This should be missing */
                .withClaimPresence("expires")
                .withClaim("created_at", (claim, jwt) -> mockUnixTime + 1 <= claim.asLong() + jwt.getClaim("expires").asLong())
                .build();
            verifier.verify(malformedToken);
        } catch (Exception e) {
            verifyFailed = true;
            assertInstanceOf(MissingClaimException.class, e);
        }
        assertTrue(verifyFailed);
    }

    @Test
    public void shouldFailWrongMAC() {
        boolean verifyFailed = false;
        try {
            JWTVerifier verifier = JWT.require(algorithm)
                .withClaim("device_id", "00:00:00:00:00:01") /* principal different from the claimed one */
                .withClaimPresence("created_at")
                .withClaimPresence("expires")
                .withClaim("created_at", (claim, jwt) -> mockUnixTime + 1 <= claim.asLong() + jwt.getClaim("expires").asLong())
                .build();
                verifier.verify(token);
        } catch (Exception e) {
            verifyFailed = true;
            assertInstanceOf(IncorrectClaimException.class, e);
        }
        assertTrue(verifyFailed);
    }
}
