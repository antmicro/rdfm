package com.antmicro.update.rdfm;

import android.annotation.SuppressLint;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Build;
import android.os.Build.VERSION;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;

import java.io.IOException;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.security.InvalidAlgorithmParameterException;
import java.security.InvalidKeyException;
import java.security.KeyPairGenerator;
import java.security.KeyStore;
import java.security.KeyStoreException;
import java.security.NoSuchAlgorithmException;
import java.security.PublicKey;
import java.security.Signature;
import java.security.SignatureException;
import java.security.UnrecoverableEntryException;
import java.security.cert.CertificateException;
import java.util.Base64;
import java.util.Calendar;
import java.util.Objects;

import androidx.preference.PreferenceManager;

public class Utils {
    private final String TAG = "Utils";
    private final String keyStoreAlias = "keyStore1";
    Context mContext;

    public Utils(Context appContext) {
        mContext = appContext;
    }

    public String getServerAddress() {
        SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(mContext);
        String pref_key = mContext.getResources().getString(R.string.preference_ota_server_address_key);
        String default_value = mContext.getResources().getString(R.string.default_rdfm_server_address);
        return prefs.getString(pref_key, default_value);
    }

    public int getUpdateIntervalSeconds() {
        SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(mContext);
        String pref_key = mContext.getResources().getString(R.string.preference_update_check_interval_key);
        String default_value = mContext.getResources().getString(R.string.default_update_check_interval_seconds);
        return Integer.parseInt(prefs.getString(pref_key, default_value));
    }

    public int getMaxShellCount() {
        SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(mContext);
        String pref_key = mContext.getResources().getString(R.string.preference_max_shell_count);
        String default_value = mContext.getResources().getString(R.string.default_max_shell_count);
        return Integer.parseInt(prefs.getString(pref_key, default_value));
    }
}