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

import com.antmicro.update.rdfm.intents.ConfigurationIntentReceiver;
import com.antmicro.update.rdfm.mgmt.AuthorizationProvider;
import com.antmicro.update.rdfm.mgmt.DeviceInfoProvider;
import com.antmicro.update.rdfm.mgmt.ManagementClient;
import com.antmicro.update.rdfm.utilities.SysUtils;

import java.util.concurrent.locks.ReentrantLock;

public class MainActivity extends Activity {

    private static final String TAG = "MainActivity";
    private static final String startUpdateIntent = "com.antmicro.update.rdfm.startUpdate";
    static final String otaPackagePath = "/data/ota_package";
    private Context mContext;
    private HttpClient mHttpClient;
    private final Utils utils = new Utils(this);
    private final UpdateManager mUpdateManager = new UpdateManager(
            new UpdateEngine(), otaPackagePath, this);
    private TextView mTextViewBuild;
    private TextView mTextViewAddress;
    private String serverAddress;
    private ReentrantLock updaterLock;
    private DeviceInfoProvider mDeviceInfo = new DeviceInfoProvider();
    private AuthorizationProvider mDeviceAuthorizationProvider;
    private ManagementClient mWsClient;
    private ConfigurationIntentReceiver mConfigReceiver;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        mContext = this;
        PreferenceManager.setDefaultValues(mContext, R.xml.shared_preference, false);
        setContentView(R.layout.main_layout);
        this.mTextViewBuild = findViewById(R.id.textViewBuild);
        this.mTextViewAddress = findViewById(R.id.textViewUrlAddress);
        Log.d(TAG, "Build version: " + mDeviceInfo.getSoftwareVersion());
        serverAddress = utils.getServerAddress();
        Log.d(TAG, "OTA server address: " + serverAddress);
        this.mTextViewBuild.setText(mDeviceInfo.getSoftwareVersion());
        this.mTextViewAddress.setText(serverAddress);
        updaterLock = new ReentrantLock();

        mDeviceAuthorizationProvider = new AuthorizationProvider(mDeviceInfo, serverAddress, this);
        mHttpClient = new HttpClient(otaPackagePath, mDeviceAuthorizationProvider);
        mWsClient = new ManagementClient(utils, mDeviceAuthorizationProvider);

        StrictMode.ThreadPolicy policy = new StrictMode.ThreadPolicy.Builder().permitAll().build();
        StrictMode.setThreadPolicy(policy);
    }

    @Override
    protected void onResume() {
        super.onResume();
        BroadcastReceiver startUpdateReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                // Handle update check in a separate thread
                new Thread(() -> onStartUpdateIntent()).start();
            }
        };
        registerReceiver(startUpdateReceiver, new IntentFilter(startUpdateIntent));
        mConfigReceiver = new ConfigurationIntentReceiver(this);
        this.setUpdateAlarm();
        this.mUpdateManager.bind();
    }

    @Override
    protected void onPause() {
        this.mUpdateManager.unbind();
        super.onPause();
    }

    private void onStartUpdateIntent() {
        if(!mUpdateManager.canSafelyCheckForUpdates()) {
            Log.i(TAG, "An update is already being installed - skipping update check");
            return;
        }
        if(!updaterLock.tryLock()) {
            Log.i(TAG, "An update check is already in progress - skipping update check");
            return;
        }

        Log.d(TAG, "Start system update");
        try {
            mHttpClient.checkUpdate(mDeviceInfo, serverAddress, utils, mUpdateManager);
        } catch (RuntimeException e) {
            Log.e(TAG, "Update failed with exception:", e);
        } finally {
            updaterLock.unlock();
        }
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