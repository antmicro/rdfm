package com.antmicro.update.rdfm.mgmt;

import android.util.Log;

import androidx.annotation.NonNull;

import com.antmicro.update.rdfm.Utils;
import com.antmicro.update.rdfm.exceptions.DeviceUnauthorizedException;
import com.antmicro.update.rdfm.exceptions.ServerConnectionException;
import com.antmicro.update.rdfm.utilities.SysUtils;

import java.util.HashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;
import okhttp3.Response;
import okio.ByteString;

public final class ManagementClient extends WebSocketListener {
    private static final String TAG = "ManagementWS";
    private static final int MAX_SHELL_COUNT = 1;
    private final String mServerAddress;
    private final IDeviceTokenProvider mTokenProvider;
    private final Object mClosed = new Object();
    private final AtomicInteger mShellCount = new AtomicInteger(0);
    private final OkHttpClient mWsClient;

    public ManagementClient(Utils utils, IDeviceTokenProvider tokenProvider) {
        // Strip the protocol from the server URL
        mServerAddress = utils.getServerAddress()
                .replaceAll("http(s?)(\\:\\/\\/)", "");
        mTokenProvider = tokenProvider;
        mWsClient = new OkHttpClient.Builder()
                .connectTimeout(5, TimeUnit.SECONDS)
                .readTimeout(5, TimeUnit.SECONDS)
                .writeTimeout(5, TimeUnit.SECONDS)
                .pingInterval(2, TimeUnit.SECONDS)
                .build();
        new Thread(this::reconnectThread).start();
    }

    private void connectToWs() {
        String token;
        try {
            token = mTokenProvider.fetchDeviceToken();
        } catch (DeviceUnauthorizedException | ServerConnectionException e) {
            Log.w(TAG, "Cannot connect to management WebSocket - device unauthorized");
            return;
        }

        Request request = new Request.Builder()
                .url("ws://" + mServerAddress + "/api/v1/devices/ws")
                .header("Authorization", "Bearer token=" + token)
                .build();
        mWsClient.newWebSocket(request, this);
    }

    @Override
    public void onOpen(WebSocket webSocket, @NonNull Response response) {
        Log.d(TAG, "Connected to: " + mServerAddress + ", sending CapabilityReport message");

        HashMap<String, Boolean> map = new HashMap<>();
        map.put("shell", true);
        webSocket.send(MessageProto.createCapabilityReport(map));
    }

    @Override
    public void onMessage(@NonNull WebSocket webSocket, @NonNull String json) {
        Log.d(TAG, "Received message: '" + json + "'");

        new MessageParser(new IMessageHandler() {
            @Override
            public void onAlert(String alert) {
                Log.d(TAG, "Server message: " + alert);
            }

            @Override
            public void onShellAttach(String macAddress, String uuid) {
            }
        }).parse(json);
    }

    @Override
    public void onMessage(WebSocket webSocket, @NonNull ByteString bytes) {
        // The protocol only utilizes text-mode messages at this point
        webSocket.close(WebSocketConsts.WS_CLOSE_INVALID_ENCODING, "RDFM protocol expects text-mode messages");
    }

    @Override
    public void onClosing(WebSocket webSocket, int code, @NonNull String reason) {
        Log.d(TAG, "Connection is being closed, reason: " + reason + " with status code: " + code);
        webSocket.close(WebSocketConsts.WS_CLOSE_NORMAL_CLOSURE, null);
        synchronized (mClosed) {
            mClosed.notifyAll();
        }
    }

    @Override
    public void onFailure(WebSocket webSocket, Throwable t, Response response) {
        Log.e(TAG, "Exception during WS processing", t);
        synchronized (mClosed) {
            mClosed.notifyAll();
        }
    }

    private void reconnectThread() {
        while (true) {
            // Delay until reconnection
            while (true) {
                try {
                    Thread.sleep(5000);
                    break;
                } catch (InterruptedException e) {
                    // empty
                }
            }

            // Connect to the WS
            try {
                connectToWs();
            } catch (Exception e) {
                Log.e(TAG, "Exception when connecting to the management WebSocket", e);
                continue;
            }

            // Wait until the connection dies
            while (true) {
                try {
                    synchronized (mClosed) {
                        mClosed.wait();
                    }
                    break;
                } catch (InterruptedException e) {
                    // empty
                }
            }
        }
    }
}
