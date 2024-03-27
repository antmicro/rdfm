package com.antmicro.update.rdfm.mgmt;

import android.util.Log;

import androidx.annotation.NonNull;

import com.antmicro.update.rdfm.configuration.IConfigurationProvider;
import com.antmicro.update.rdfm.exceptions.DeviceUnauthorizedException;
import com.antmicro.update.rdfm.exceptions.ServerConnectionException;
import com.antmicro.update.rdfm.utilities.BackoffCounter;
import com.antmicro.update.rdfm.utilities.HttpUtils;

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
    private static final long MIN_RECONNECT_INTERVAL_MILLIS = 1_000;
    private static final long MAX_RECONNECT_INTERVAL_MILLIS = 120_000;
    private final IDeviceTokenProvider mTokenProvider;
    private final IConfigurationProvider mConfig;
    private final Object mClosed = new Object();
    private final AtomicInteger mShellCount = new AtomicInteger(0);
    private final OkHttpClient mWsClient;
    private String mServerAddress;
    private int mMaxShellCount;

    public ManagementClient(IConfigurationProvider config, IDeviceTokenProvider tokenProvider) {
        mConfig = config;
        mTokenProvider = tokenProvider;
        mWsClient = new OkHttpClient.Builder()
                .connectTimeout(5, TimeUnit.SECONDS)
                .readTimeout(5, TimeUnit.SECONDS)
                .writeTimeout(5, TimeUnit.SECONDS)
                .pingInterval(120, TimeUnit.SECONDS)
                .build();
        new Thread(this::reconnectThread).start();
    }

    private void connectToWs() throws DeviceUnauthorizedException, ServerConnectionException {
        mServerAddress = HttpUtils.replaceHttpSchemeWithWs(mConfig.getServerAddress());
        mMaxShellCount = mConfig.getMaxShellCount();
        String token = mTokenProvider.fetchDeviceToken();
        Request request = new Request.Builder()
                .url(mServerAddress + "/api/v1/devices/ws")
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
                String token;
                try {
                    token = mTokenProvider.fetchDeviceToken();
                } catch (DeviceUnauthorizedException | ServerConnectionException e) {
                    Log.w(TAG, "Cannot connect reverse shell WebSocket - device unauthorized");
                    return;
                }

                if (mShellCount.incrementAndGet() > mMaxShellCount) {
                    Log.w(TAG, "Ignoring shell attach request - maximum shell count reached");
                    mShellCount.decrementAndGet();
                    return;
                }

                new Thread(() -> {
                    try {
                        ReverseShell shell = new ReverseShell(mServerAddress, token, uuid, macAddress);
                        shell.run();
                    } finally {
                        mShellCount.decrementAndGet();
                    }
                }).start();
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
        BackoffCounter counter = new BackoffCounter(MIN_RECONNECT_INTERVAL_MILLIS, MAX_RECONNECT_INTERVAL_MILLIS);
        while (true) {
            long sleepDurationMillis = counter.next();
            Log.i(TAG, "Reconnecting in " + sleepDurationMillis + "ms..");

            // Delay until reconnection
            while (true) {
                try {
                    Thread.sleep(sleepDurationMillis);
                    break;
                } catch (InterruptedException e) {
                    // empty
                }
            }

            // Connect to the WS
            try {
                connectToWs();
            } catch (ServerConnectionException e) {
                Log.e(TAG, "Cannot connect to the management WebSocket - server connection failed");
                continue;
            } catch (DeviceUnauthorizedException e) {
                Log.e(TAG, "Cannot connect to the management WebSocket - device unauthorized");
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
