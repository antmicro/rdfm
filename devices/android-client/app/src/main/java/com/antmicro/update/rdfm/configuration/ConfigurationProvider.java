package com.antmicro.update.rdfm.configuration;

import android.content.Context;
import android.content.SharedPreferences;

import androidx.preference.PreferenceManager;

import com.antmicro.update.rdfm.R;

public class ConfigurationProvider implements IConfigurationProvider {
    private final Context mContext;

    public ConfigurationProvider(Context context) {
        mContext = context;
    }

    @Override
    public String getServerAddress() {
        SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(mContext);
        String pref_key = mContext.getResources().getString(R.string.preference_ota_server_address_key);
        String default_value = mContext.getResources().getString(R.string.default_rdfm_server_address);
        return prefs.getString(pref_key, default_value);
    }

    @Override
    public int getUpdateIntervalSeconds() {
        SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(mContext);
        String pref_key = mContext.getResources().getString(R.string.preference_update_check_interval_key);
        String default_value = mContext.getResources().getString(R.string.default_update_check_interval_seconds);
        return Integer.parseInt(prefs.getString(pref_key, default_value));
    }

    @Override
    public int getMaxShellCount() {
        SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(mContext);
        String pref_key = mContext.getResources().getString(R.string.preference_max_shell_count);
        String default_value = mContext.getResources().getString(R.string.default_max_shell_count);
        return Integer.parseInt(prefs.getString(pref_key, default_value));
    }
}
