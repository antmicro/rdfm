package com.antmicro.update.rdfm.mgmt;

import android.util.Log;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import com.antmicro.update.rdfm.utilities.StringUtils;
import com.antmicro.update.rdfm.utilities.SysUtils;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Arrays;
import java.util.HashMap;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;
import okio.ByteString;

public class ReverseShell {
    private static final String TAG = "ReverseShell";
    private final String mDeviceToken;
    private final String mShellUuid;
    private final String mServerAddress;
    private Process mShellProcess = null;
    private WebSocket mWebSocket = null;
    private Request mRequest;
    private Semaphore mSemaphore;

    public ReverseShell(String serverAddress, String deviceToken, String shellUuid, String macAddress) {
        mServerAddress = serverAddress;
        mDeviceToken = deviceToken;
        mShellUuid = shellUuid;
        mRequest = new Request.Builder()
                .url("ws://" + mServerAddress + "/api/v1/devices/" + macAddress + "/shell/attach/" + shellUuid)
                .header("Authorization", "Bearer token=" + mDeviceToken)
                .build();
        mSemaphore = new Semaphore(0);
    }

    /**
     * Run the RDFM reverse shell session.
     * This function blocks until the shell session has finished execution.
     */
    public void run() {
        try {
            mShellProcess = new ProcessBuilder("/bin/sh", "-i")
                    .redirectErrorStream(true)
                    .start();
        } catch (IOException e) {
            throw new RuntimeException("Failed to start /bin/sh", e);
        }

        OkHttpClient client = new OkHttpClient.Builder()
                .connectTimeout(5, TimeUnit.SECONDS)
                .readTimeout(5, TimeUnit.SECONDS)
                .writeTimeout(5, TimeUnit.SECONDS)
                .pingInterval(2, TimeUnit.SECONDS)
                .build();

        Object webSocketIsReady = new Object();

        mWebSocket = client.newWebSocket(mRequest, new WebSocketListener() {
            @Override
            public void onOpen(@NonNull WebSocket webSocket, @NonNull Response response) {
                Log.d(TAG, "Connected to shell WS!");
                synchronized (webSocketIsReady) {
                    webSocketIsReady.notifyAll();
                }
            }

            @Override
            public void onMessage(@NonNull WebSocket webSocket, @NonNull ByteString bytes) {
                try {
                    sendToShell(bytes.toByteArray());
                } catch (IOException e) {
                    throw new RuntimeException("Failed to send data to shell", e);
                }
            }

            @Override
            public void onClosed(@NonNull WebSocket webSocket, int code, @NonNull String reason) {
                Log.d(TAG, "Connection to shell WS closed, reason: " + reason + " with status code: " + code);
                closeShell();
            }

            @Override
            public void onFailure(@NonNull WebSocket webSocket, @NonNull Throwable t, @Nullable Response response) {
                Log.d(TAG, "Closing shell WS: " + t.getMessage());
                closeShell();
            }
        });

        // Wait until the WS is ready to accept data
        while (true) {
            try {
                synchronized (webSocketIsReady) {
                    webSocketIsReady.wait();
                }
                break;
            } catch (InterruptedException e) {
                // intentionally empty
            }
        }

        new Thread(() -> {
            try {
                outputToWebSocket();
            } catch (IOException e) {
                Log.d(TAG, "Closing stdout reader: " + e.getMessage());
            } finally {
                closeShell();
            }
        }).start();

        new Thread(() -> {
            try {
                checkShellExitStatus();
            } finally {
                closeShell();
            }
        }).start();

        Log.d(TAG, "Waiting until shell exit..");
        mSemaphore.acquireUninterruptibly(3);
        Log.d(TAG, "Shell is finished!");
    }

    /**
     * Read data from stdout to the connected WebSocket.
     *
     * @throws IOException Reading stdout of the shell failed
     */
    private void outputToWebSocket() throws IOException {
        byte[] buffer = new byte[4096];
        InputStream stdout = mShellProcess.getInputStream();
        while (true) {
            int count = stdout.read(buffer);
            if (count < 0) {
                return;
            }

            byte[] data = Arrays.copyOfRange(buffer, 0, count);
            // Uncomment the line below to log all shell output data
            // WARNING: Will produce lots of logs
            //Log.v(TAG, " SHELL --> WS " + StringUtils.bytesToHexString(data, ""));
            mWebSocket.send(new ByteString(data));
        }
    }

    /**
     * Wait for the shell to close.
     * This should be spawned in a separate thread.
     */
    private void checkShellExitStatus() {
        while (true) {
            try {
                int exitCode = mShellProcess.waitFor();
                Log.d(TAG, "Closing shell status waiter: shell process exited with status code " + exitCode);
                return;
            } catch (InterruptedException e) {
                // intentionally empty
            }
        }
    }

    /**
     * Send data to the currently running shell
     *
     * @param input Bytes to send to stdin of the shell
     * @throws IOException Writing to stdin failed
     */
    private void sendToShell(byte[] input) throws IOException {
        // Uncomment the line below to log all shell input data
        // WARNING: Will produce lots of logs
        //Log.v(TAG, " WS --> SHELL " + StringUtils.bytesToHexString(input, ""));
        OutputStream stdin = mShellProcess.getOutputStream();
        stdin.write(input);
        stdin.flush();
    }

    /**
     * Signal the shell to close
     * This must be called exactly once by each participating thread:
     * - WebSocketListener thread
     * - Shell STDOUT reader
     * - Shell exit status reader
     */
    private void closeShell() {
        mShellProcess.destroyForcibly();
        mWebSocket.close(WebSocketConsts.WS_CLOSE_NORMAL_CLOSURE, "shell connection closed");
        mSemaphore.release(1);
    }
}
