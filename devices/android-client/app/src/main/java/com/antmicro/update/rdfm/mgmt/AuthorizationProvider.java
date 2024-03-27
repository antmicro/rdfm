package com.antmicro.update.rdfm.mgmt;

import android.content.Context;
import android.util.Log;

import com.antmicro.update.rdfm.configuration.IConfigurationProvider;
import com.antmicro.update.rdfm.exceptions.DeviceInfoException;
import com.antmicro.update.rdfm.exceptions.DeviceUnauthorizedException;
import com.antmicro.update.rdfm.exceptions.ServerConnectionException;
import com.antmicro.update.rdfm.utilities.KeyUtils;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.sql.Timestamp;
import java.util.Iterator;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.TimeUnit;

import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import okhttp3.logging.HttpLoggingInterceptor;

public class AuthorizationProvider implements IDeviceTokenProvider {
    private static final String TAG = "AuthorizationProvider";
    private static final MediaType JSON = MediaType.get("application/json; charset=utf-8");
    private static final int READ_TIMEOUT_MS = 500;
    private static final long TOKEN_EXPIRATION_GRACE_PERIOD_MS = 5000;
    private final IConfigurationProvider mConfig;
    private final Context mContext;
    private final OkHttpClient mClient;
    private final DeviceInfoProvider mDeviceInfo;
    private String mDeviceToken;
    private long mTokenExpiresAt;

    public AuthorizationProvider(DeviceInfoProvider deviceInfo, IConfigurationProvider config, Context context) {
        mDeviceInfo = deviceInfo;
        mConfig = config;
        mContext = context;
        mDeviceToken = "";
        mTokenExpiresAt = 0;

        HttpLoggingInterceptor loggingInterceptor = new HttpLoggingInterceptor();
        loggingInterceptor.setLevel(HttpLoggingInterceptor.Level.BODY);
        mClient = new OkHttpClient.Builder()
                .addInterceptor(loggingInterceptor)
                .readTimeout(READ_TIMEOUT_MS, TimeUnit.MILLISECONDS)
                .build();
    }

    private String registerRequest() throws ServerConnectionException, DeviceUnauthorizedException {
        Timestamp timestamp = new Timestamp(System.currentTimeMillis());
        String key = KeyUtils.getPublicKey(mContext);
        Log.d(TAG, "Public key: " + key);

        try {
            JSONObject devParamsJSON = new JSONObject(mDeviceInfo.toMap());
            String reqJSON = new JSONObject()
                    .put("metadata", devParamsJSON)
                    .put("public_key", key)
                    .put("timestamp", timestamp.getTime())
                    .toString();
            byte[] requestBytes = reqJSON.getBytes(StandardCharsets.UTF_8);
            String signature = KeyUtils.signData(mContext, reqJSON);

            RequestBody reqBody = RequestBody.create(requestBytes, JSON);
            try {
                Request request = new Request.Builder()
                        .url(mConfig.getServerAddress() + "/api/v1/auth/device")
                        .addHeader("X-RDFM-Device-Signature", signature)
                        .post(reqBody)
                        .build();
                try (Response response = mClient.newCall(request).execute()) {
                    switch (response.code()) {
                        case 200:
                            Log.d(TAG, "Device authorized");
                            String body = response.body().string();
                            String token = getResponseParam(body, "token");
                            String expires = getResponseParam(body, "expires");

                            Log.d(TAG, "Token expires in " + expires + " seconds");
                            mDeviceToken = token;
                            long expiryMillis = Long.parseLong(expires) * 1000;
                            // Intentionally shorten the time this token is in use.
                            // This is to reduce the probability that we use a token that was just
                            // about to expire and we receive a 401 response.
                            long nextAuthMillis = (expiryMillis > TOKEN_EXPIRATION_GRACE_PERIOD_MS)
                                    ? expiryMillis - TOKEN_EXPIRATION_GRACE_PERIOD_MS
                                    : expiryMillis;
                            mTokenExpiresAt = timestamp.getTime() + nextAuthMillis;
                            return mDeviceToken;
                        case 401:
                            Log.d(TAG, "Wait until the server administration accepts your request.");
                            throw new DeviceUnauthorizedException("Device unauthorized");
                        default:
                            Log.d(TAG, "Unexpected status code in register response: " + response.code());
                            throw new ServerConnectionException("Failed to make authorization request");
                    }
                } catch (IOException e) {
                    Log.e(TAG, "Authorization request failed", e);
                    throw new ServerConnectionException("Failed to make authorization request");
                }
            } catch (RuntimeException e) {
                Log.e(TAG, "Authorization request failed", e);
                throw new ServerConnectionException("Failed to make authorization request");
            }
        } catch (JSONException | DeviceInfoException e) {
            Log.e(TAG, "Authorization request failed", e);
            throw new ServerConnectionException("Failed to make authorization request");
        }
    }

    private String getResponseParam(String responseBody, String param) {
        try {
            JSONObject jsonData = new JSONObject(responseBody);
            Iterator<String> keys = jsonData.keys();
            while (keys.hasNext()) {
                String key = keys.next();
                if (key.equals(param)) {
                    return jsonData.get(key).toString();
                }
            }
        } catch (JSONException e) {
            throw new RuntimeException(e);
        }
        return null;
    }

    private boolean isTokenExpired() {
        Timestamp timestamp = new Timestamp(System.currentTimeMillis());
        return timestamp.getTime() >= mTokenExpiresAt;
    }

    @Override
    public String fetchDeviceToken() throws ServerConnectionException, DeviceUnauthorizedException {
        synchronized (this) {
            if (isTokenExpired()) {
                Log.d(TAG, "Token expired, resending device authorization");
                return registerRequest();
            }
            return mDeviceToken;
        }
    }
}
