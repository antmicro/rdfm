package com.antmicro.rdfm;

import org.apache.kafka.common.security.auth.AuthenticateCallbackHandler;
import org.apache.kafka.common.security.plain.PlainAuthenticateCallback;
import com.auth0.jwt.algorithms.Algorithm;
import com.auth0.jwt.exceptions.*;
import com.auth0.jwt.JWT;
import com.auth0.jwt.JWTVerifier;
import java.time.Instant;
import java.util.List;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.Map;
import javax.security.auth.callback.*;
import javax.security.auth.login.AppConfigurationEntry;

public class DeviceAuthenticateCallbackHandler implements AuthenticateCallbackHandler {
	private static final Logger LOG = Logger.getLogger(DeviceAuthenticateCallbackHandler.class.getName());
	private Algorithm algorithm;
	private boolean configured = false;

	@Override
	public void configure(Map<String, ?> configs, String mechanism, List<AppConfigurationEntry> jaasConfigEntries) {
		try {
			algorithm = Algorithm.HMAC256(System.getenv("RDFM_JWT_SECRET"));
		} catch (Exception e) {
			LOG.log(Level.SEVERE, "Failed to configure callback: ", e);
			return;
		}

		configured = true;
	}

	@Override
	public void handle(Callback[] callbacks) throws UnsupportedCallbackException {
		if (!configured) {
			throw new IllegalStateException("callback is not configured");
		}

		String deviceId = null;
		String token = null;

		for (Callback cb : callbacks) {
			if (cb instanceof NameCallback) {
				deviceId = ((NameCallback) cb).getDefaultName();
			} else if (cb instanceof PlainAuthenticateCallback) {
				PlainAuthenticateCallback pc = (PlainAuthenticateCallback) cb;
				token = new String(pc.password());
			} else {
				throw new UnsupportedCallbackException(cb);
			}
		}

		boolean isValid = isValidToken(deviceId, token);

		for (Callback cb : callbacks) {
			if (cb instanceof PlainAuthenticateCallback) {
				((PlainAuthenticateCallback) cb).authenticated(isValid);
			}
		}
	}

	@Override
	public void close() {
		return;
	}

	private boolean isValidToken(String deviceId, String token) {
		try {
			long currentUnixUTC = Instant.now().getEpochSecond();

			JWTVerifier verifier = JWT.require(algorithm)
					.withClaim("device_id", deviceId)
					.withClaimPresence("created_at")
					.withClaimPresence("expires")
					.withClaim("created_at",
							(claim, jwt) -> currentUnixUTC <= claim.asLong() + jwt.getClaim("expires").asLong())
					.build();
			verifier.verify(token);
		} catch (AlgorithmMismatchException e) {
			LOG.log(Level.INFO, "Failed to validate device " + deviceId + " due to algorithm mismatch: " + e.getMessage());
			return false;
		} catch (SignatureVerificationException e) {
			LOG.log(Level.INFO, "Failed to validate device " + deviceId + " due to signature verification failure: " + e.getMessage());
			return false;
		} catch (TokenExpiredException e) {
			LOG.log(Level.INFO, "Failed to validate device " + deviceId + " due to token expiry: " + e.getMessage());
			return false;
		} catch (MissingClaimException e) {
			LOG.log(Level.INFO, "Failed to validate device " + deviceId + " due to one or more token claims missing: " + e.getMessage());
			return false;
		} catch (IncorrectClaimException e) {
			// We expect this since `IncorrectClaimException` is triggered in the case of an expired token, hence a lower log level
			LOG.log(Level.FINE,
					"Failed to validate device " + deviceId + " due to one or more token claims being incorrect: " + e.getMessage());
			return false;
		} catch (Exception e) {
			LOG.log(Level.WARNING, "Failed to validate device " + deviceId, e);
			return false;
		}
		LOG.log(Level.INFO, ": Validated device: " + deviceId + ".");
		return true;
	}

	public boolean isConfigred() {
		return configured;
	}
}
