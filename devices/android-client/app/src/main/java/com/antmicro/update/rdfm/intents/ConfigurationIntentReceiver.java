package com.antmicro.update.rdfm.intents;

import android.annotation.SuppressLint;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.util.Log;

import androidx.preference.PreferenceManager;

import java.util.Map;
import java.util.Set;

public class ConfigurationIntentReceiver extends BroadcastReceiver {
    private static final String TAG = "ConfigurationIntentReceiver";
    private static final String SET_CONFIGURATION = "com.antmicro.update.rdfm.configurationSet";
    private static final String GET_CONFIGURATION = "com.antmicro.update.rdfm.configurationGet";
    private static final String CONFIGURATION_RESPONSE = "com.antmicro.update.rdfm.configurationResponse";
    // This must match the one specified in the manifest
    private static final String CONFIGURATION_PERMISSION = "com.antmicro.update.rdfm.permission.CONFIGURATION";

    @SuppressLint("UnspecifiedRegisterReceiverFlag")
    public ConfigurationIntentReceiver(Context context) {
        IntentFilter filter = new IntentFilter();
        filter.addAction(SET_CONFIGURATION);
        filter.addAction(GET_CONFIGURATION);
        context.registerReceiver(this, filter, CONFIGURATION_PERMISSION, null);
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        try {
            if (intent.getAction() == SET_CONFIGURATION) {
                setConfiguration(context, intent);
            } else if (intent.getAction() == GET_CONFIGURATION) {
                getConfiguration(context, intent);
            }
        } catch (Exception e) {
            Log.w(TAG, "Exception during handling of config intent", e);
        }
    }

    private void setConfiguration(Context context, Intent intent) {
        Bundle bundle = intent.getExtras();
        SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(context);

        Map<String, ?> allPreferences = prefs.getAll();
        for (Map.Entry<String, ?> entry : allPreferences.entrySet()) {
            // Only modify preferences that already exist
            String key = entry.getKey();

            if (bundle.containsKey(key)) {
                Object value = bundle.get(key);
                SharedPreferences.Editor edit = prefs.edit();
                Log.d(TAG, "Configuration bundle: " + key + " : " + (value != null ? value.toString() : "NULL"));
                if (value instanceof String) {
                    edit.putString(key, (String) value);
                } else if (value instanceof Boolean) {
                    edit.putBoolean(key, (Boolean) value);
                } else if (value instanceof Float) {
                    edit.putFloat(key, (float) value);
                } else if (value instanceof Integer) {
                    edit.putInt(key, (Integer) value);
                } else if (value instanceof Long) {
                    edit.putLong(key, (Long) value);
                } else if (value instanceof Set) {
                    Log.w(TAG, "SharedPreference values of Set<String> unsupported for config via intents");
                }
                edit.apply();
            }
        }
    }

    private void getConfiguration(Context context, Intent intent) {
        Intent response = new Intent(CONFIGURATION_RESPONSE);
        SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(context);

        Map<String, ?> allPreferences = prefs.getAll();
        for (Map.Entry<String, ?> entry : allPreferences.entrySet()) {
            String key = entry.getKey();
            Object value = entry.getValue();
            if (value instanceof String) {
                response.putExtra(key, (String) value);
            } else if (value instanceof Boolean) {
                response.putExtra(key, (Boolean) value);
            } else if (value instanceof Float) {
                response.putExtra(key, (float) value);
            } else if (value instanceof Integer) {
                response.putExtra(key, (Integer) value);
            } else if (value instanceof Long) {
                response.putExtra(key, (Long) value);
            } else if (value instanceof Set) {
                Log.w(TAG, "SharedPreference values of Set<String> unsupported for config via intents");
            }
        }
        context.sendBroadcast(response);
    }
}
