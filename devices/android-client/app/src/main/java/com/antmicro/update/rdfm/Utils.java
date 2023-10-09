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

    public String getServerAddress(Context mContext) {
        PreferenceManager.setDefaultValues(mContext, R.xml.shared_preference, false);
        SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(mContext);
        String pref_key = mContext.getResources().getString(R.string.ota_server_address);
        return prefs.getString(pref_key, null);
    }

    public int getUpdateIntervalSeconds() {
        PreferenceManager.setDefaultValues(mContext, R.xml.shared_preference, false);
        SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(mContext);
        String pref_key = mContext.getResources().getString(R.string.update_check_interval_in_seconds);
        // The actual default is set in shared_preference.xml, but pass some sane values in here as well
        // if the configuration is missing this value.
        return Integer.parseInt(prefs.getString(pref_key, "600"));
    }
}