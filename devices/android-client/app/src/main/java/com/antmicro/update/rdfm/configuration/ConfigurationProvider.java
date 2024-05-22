package com.antmicro.update.rdfm.configuration;

import android.content.Context;
import android.content.SharedPreferences;
import android.content.res.Resources.NotFoundException;

import androidx.preference.PreferenceManager;
import android.util.Log;

import com.antmicro.update.rdfm.R;

public class ConfigurationProvider implements IConfigurationProvider {
    private final Context mContext;
    private static final String TAG = "ConfigurationProvider";

    public ConfigurationProvider(Context context) {
        mContext = context;
    }

    @Override
    public String getServerAddress() {
        SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(mContext);

        String pref_key;
        String default_value;
        try {
            pref_key = mContext.getResources().getString(R.string.preference_ota_server_address_key);
            default_value = mContext.getResources().getString(R.string.default_rdfm_server_address);
        } catch (NotFoundException e) {
            Log.e(TAG, "Failed to get preference key or default value: " + e.getMessage() + ", aborting");
            return null;
        }

        try {
            return prefs.getString(pref_key, default_value);
        } catch (ClassCastException e) {
            Log.e(TAG, "Failed to get preference value: " + e.getMessage() + ", aborting");
            return null;
        }
    }

    @Override
    public int getUpdateIntervalSeconds() {
        SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(mContext);

        String pref_key;
        String default_value;
        String pref_value;
        try {
            pref_key = mContext.getResources().getString(R.string.preference_update_check_interval_key);
            default_value = mContext.getResources().getString(R.string.default_update_check_interval_seconds);
        } catch (NotFoundException e) {
            Log.e(TAG, "Failed to get preference key or default value: " + e.getMessage() + ", aborting");
            return -1;
        }

        try {
            pref_value = prefs.getString(pref_key, default_value);
        } catch (ClassCastException e) {
            Log.e(TAG, "Failed to get preference value: " + e.getMessage() + ", aborting");
            return -1;
        }

        try {
            return Integer.parseInt(pref_value);
        } catch (NumberFormatException e) {
            Log.e(TAG, "Failed to parse update interval seconds: " + e.getMessage() + ", aborting");
            return -1;
        }
    }

    @Override
    public int getMaxShellCount() {
        SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(mContext);

        String pref_key;
        String default_value;

        try {
            pref_key = mContext.getResources().getString(R.string.preference_max_shell_count);
            default_value = mContext.getResources().getString(R.string.default_max_shell_count);
        } catch (NotFoundException e) {
            Log.e(TAG, "Failed to get preference key or default value: " + e.getMessage() + ", aborting");
            return -1;
        }

        try {
            return Integer.parseInt(prefs.getString(pref_key, default_value));
        } catch (NumberFormatException e) {
            Log.e(TAG, "Failed to parse max shell count: " + e.getMessage() + ", aborting");
            return -1;
        }
    }
}
