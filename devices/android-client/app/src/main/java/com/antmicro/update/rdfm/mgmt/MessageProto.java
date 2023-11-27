package com.antmicro.update.rdfm.mgmt;

import org.json.JSONException;
import org.json.JSONObject;

import java.util.Map;

public class MessageProto {
    public static String createCapabilityReport(Map<String, Boolean> capabilities) {
        JSONObject message = new JSONObject();
        try {
            message.put("method", "capability_report");

            JSONObject capabilitiesObject = new JSONObject();
            for (Map.Entry<String, Boolean> capability : capabilities.entrySet()) {
                capabilitiesObject.put(capability.getKey(), capability.getValue());
            }
            message.putOpt("capabilities", capabilitiesObject);

            return message.toString();
        } catch (JSONException e) {
            throw new RuntimeException(e);
        }
    }
}
