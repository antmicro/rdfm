package com.antmicro.update.rdfm;

import android.util.Log;

import com.antmicro.update.rdfm.exceptions.DeviceUnauthorizedException;
import com.antmicro.update.rdfm.exceptions.ServerConnectionException;
import com.antmicro.update.rdfm.mgmt.IDeviceTokenProvider;
import com.antmicro.update.rdfm.mgmt.ManagementClient;
import com.antmicro.update.rdfm.utilities.KeyUtils;
import com.antmicro.update.rdfm.utilities.SysUtils;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.URISyntaxException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.DigestInputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.sql.Timestamp;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.concurrent.TimeUnit;

import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import okhttp3.ResponseBody;
import okhttp3.logging.HttpLoggingInterceptor;
import okio.BufferedSink;
import okio.Okio;

public class HttpClient {
    private static final String TAG = "HttpClient";
    private static final MediaType JSON = MediaType.get("application/json; charset=utf-8");
    private final OkHttpClient client;
    private final String otaPackagePath;
    private IDeviceTokenProvider mTokenProvider;

    public HttpClient(String otaPackagesPath, IDeviceTokenProvider tokenProvider) {
        final int timeout = 500;
        otaPackagePath = otaPackagesPath;
        HttpLoggingInterceptor loggingInterceptor = new HttpLoggingInterceptor();
        loggingInterceptor.setLevel(HttpLoggingInterceptor.Level.BODY);
        client = new OkHttpClient.Builder()
                .addInterceptor(loggingInterceptor)
                .readTimeout(timeout, TimeUnit.MILLISECONDS)
                .build();
        mTokenProvider = tokenProvider;
    }

    public void checkUpdate(String bspVersion, String serverAddress, Utils utils,
                            UpdateManager mUpdateManager) {
        String macAddress = SysUtils.findDeviceMAC();
        String devType = SysUtils.getDeviceType();
        String serialNumber = SysUtils.getSerialNumber();
        Log.d(TAG, "Device serial number: " + serialNumber);

        Map<String, String> devParams = new HashMap<>();
        devParams.put("rdfm.software.version", bspVersion);
        devParams.put("rdfm.hardware.macaddr", macAddress);
        devParams.put("rdfm.hardware.devtype", devType);
        String reqData = new JSONObject(devParams).toString();
        RequestBody reqBody = RequestBody.create(reqData, JSON);

        String token;
        try {
            token = mTokenProvider.fetchDeviceToken();
        } catch (DeviceUnauthorizedException | ServerConnectionException e) {
            Log.w(TAG, "Cannot check for updates, device unauthorized");
            return;
        }

        try {
            Request request = new Request.Builder()
                    .url(serverAddress + "/api/v1/update/check")
                    .addHeader("Authorization", "Bearer token=" + token)
                    .post(reqBody)
                    .build();

            try (Response response = client.newCall(request).execute()) {
                try (ResponseBody responseBody = response.body()) {
                    switch (response.code()) {
                        case 200:
                            Log.d(TAG, "Update is available");
                            String body = responseBody.string();
                            String packageUri = getResponseParam(body, "uri");
                            String checksum =  getResponseParam(body, "sha256");
                            String otaPackageName = Paths.get(
                                    new URI(packageUri).getPath()).getFileName().toString();
                            boolean readyToUpdate = downloadPackage(packageUri, checksum, otaPackageName);
                            if (readyToUpdate) {
                                mUpdateManager.applyUpdate(otaPackageName);
                            } else {
                                Log.d(TAG, "TODO: Retry to download package");
                            }
                            break;
                        case 204:
                            Log.d(TAG, "No updates are available");
                            break;
                        case 400:
                            Log.d(TAG, "Missing device metadata");
                            break;
                        case 401:
                            Log.d(TAG, "Device not authorized - the token has expired");
                            break;
                        default:
                            Log.d(TAG, "Unexpected code " + response);

                    }
                } catch (URISyntaxException e) {
                    throw new RuntimeException("Could not construct package URI", e);
                }
            }
        } catch (RuntimeException | IOException e) {
            throw new RuntimeException("Failed to check for updates", e);
        }
    }

    private boolean downloadPackage(String packageUri, String checksum, String packageName) {
        final int packageTimeout = 10000;
        Request packageRequest = new Request.Builder().url(packageUri).build();
        HttpLoggingInterceptor loggingInterceptor = new HttpLoggingInterceptor();
        loggingInterceptor.setLevel(HttpLoggingInterceptor.Level.BASIC);
        OkHttpClient pkgClient = new OkHttpClient.Builder()
                .addInterceptor(loggingInterceptor)
                .readTimeout(packageTimeout, TimeUnit.MILLISECONDS)
                .build();
        try (Response response = pkgClient.newCall(packageRequest).execute()) {
            if (response.isSuccessful()) {
                File otaPackageFile = new File(otaPackagePath, packageName);
                BufferedSink bufferedSink = Okio.buffer(Okio.sink(otaPackageFile));
                bufferedSink.writeAll(response.body().source());
                bufferedSink.close();
                Log.d(TAG, "Finished downloading OTA package from server");
                String packageFullPath = otaPackagePath + "/" + packageName;
                return verifyChecksum(packageFullPath, checksum);
            }
            return false;
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    private boolean verifyChecksum(String fileName, String checksum) {
        try {
            MessageDigest sha256 = MessageDigest.getInstance("SHA-256");
            try (InputStream input = Files.newInputStream(Paths.get(fileName))) {
                DigestInputStream digestInputStream = new DigestInputStream(input, sha256);
                byte[] buffer = new byte[4096];
                while (digestInputStream.read(buffer) != -1){}
                byte[] calcChecksum = digestInputStream.getMessageDigest().digest();
                String stringChecksum = byteArrayToHex(calcChecksum);
                Log.d(TAG, "Checksum of downloaded OTA package: " + stringChecksum);
                if (!checksum.equals(stringChecksum)) {
                    Log.e(TAG, "Invalid OTA package checksum!");
                    return false;
                }
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException(e);
        }
        return true;
    }

    public static String byteArrayToHex(byte[] byteArray) {
        StringBuilder builder = new StringBuilder(byteArray.length * 2);
        for(byte b: byteArray)
            builder.append(String.format("%02x", b));
        return builder.toString();
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
}