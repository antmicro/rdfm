package com.antmicro.update.rdfm;

import android.app.Activity;
import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Bundle;
import android.os.StrictMode;
import android.os.SystemClock;
import android.os.UpdateEngine;
import android.util.Log;
import android.widget.TextView;

import androidx.preference.PreferenceManager;

import com.antmicro.update.rdfm.utilities.SysUtils;

import java.util.Calendar;

public class MainActivity extends Activity {

    private static final String TAG = "MainActivity";
    private static final String startUpdateIntent = "com.antmicro.update.rdfm.startUpdate";
    static final String otaPackagePath = "/data/ota_package";
    private Context mContext;
    private final HttpClient httpClient = new HttpClient(otaPackagePath);
    private final Utils utils = new Utils(this);
    private final UpdateManager mUpdateManager = new UpdateManager(
            new UpdateEngine(), otaPackagePath, this);
    private TextView mTextViewBuild;
    private TextView mTextViewAddress;
    private String serverAddress;
    private String buildVersion;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        mContext = this;
        PreferenceManager.setDefaultValues(mContext, R.xml.shared_preference, false);
        setContentView(R.layout.main_layout);
        this.mTextViewBuild = findViewById(R.id.textViewBuild);
        this.mTextViewAddress = findViewById(R.id.textViewUrlAddress);
        buildVersion = SysUtils.getBuildVersion();
        Log.d(TAG, "Build version: " + buildVersion);
        serverAddress = utils.getServerAddress(mContext);
        Log.d(TAG, "OTA server address: " + serverAddress);
        this.mTextViewBuild.setText(buildVersion);
        this.mTextViewAddress.setText(serverAddress);

        StrictMode.ThreadPolicy policy = new StrictMode.ThreadPolicy.Builder().permitAll().build();
        StrictMode.setThreadPolicy(policy);
    }

    @Override
    protected void onResume() {
        super.onResume();
        BroadcastReceiver startUpdateReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                Log.d(TAG, "Start system update");
                mUpdateManager.bind();
                httpClient.checkUpdate(buildVersion, serverAddress, utils, mUpdateManager);
            }
        };
        registerReceiver(startUpdateReceiver, new IntentFilter(startUpdateIntent));
        this.setUpdateAlarm();
    }

    @Override
    protected void onPause() {
       this.mUpdateManager.unbind();
       super.onPause();
    }

    private void setUpdateAlarm() {
        AlarmManager startAlarm = (AlarmManager) this.getSystemService(Context.ALARM_SERVICE);
        PendingIntent pendingIntent = PendingIntent.getBroadcast(
                mContext,
                0,
                new Intent(startUpdateIntent),
                PendingIntent.FLAG_IMMUTABLE);

        startAlarm.setRepeating(
                AlarmManager.ELAPSED_REALTIME_WAKEUP,
                SystemClock.elapsedRealtime(),
                utils.getUpdateIntervalSeconds() * 1000L,
                pendingIntent);
    }
}