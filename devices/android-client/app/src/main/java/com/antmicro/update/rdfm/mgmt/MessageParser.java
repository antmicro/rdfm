package com.antmicro.update.rdfm.mgmt;

import androidx.annotation.NonNull;

import org.json.JSONException;
import org.json.JSONObject;

public class MessageParser {
    private final IMessageHandler mMessageHandler;

    public MessageParser(@NonNull IMessageHandler messageHandler) {
        mMessageHandler = messageHandler;
    }

    public void parse(String jsonMessage) {
        try {
            JSONObject message = new JSONObject(jsonMessage);
            String method = message.getString("method");
            switch (method) {
                case "alert": {
                    String alert = message.getJSONObject("alert").getString("message");
                    mMessageHandler.onAlert(alert);
                    break;
                }
                case "shell_attach": {
                    String macAddress = message.getString("mac_addr");
                    String shellUuid = message.getString("uuid");
                    mMessageHandler.onShellAttach(macAddress, shellUuid);
                    break;
                }
            }
        } catch (JSONException exception) {
            throw new RuntimeException("Could not deserialize JSON message", exception);
        }
    }
}
