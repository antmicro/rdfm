package com.antmicro.update.rdfm;

import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.os.UpdateEngine;
import android.os.UpdateEngineCallback;
import android.util.Log;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.nio.file.Paths;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

public class UpdateManager {

    private static final String TAG = "UpdateManager";
    private final UpdateEngine mUpdateEngine;
    private final Context mContext;
    private String otaPackagePath;
    private String otaPackageName;

    public UpdateManager(UpdateEngine updateEngine, String otaPackagesPath, Context context) {
        this.mUpdateEngine = updateEngine;
        this.mContext = context;
        this.otaPackagePath = otaPackagesPath;
    }

    private final UpdateData mUpdateData = new UpdateData();
    private final UpdateManager.UpdateEngineCallbackImpl
            mUpdateEngineCallback = new UpdateManager.UpdateEngineCallbackImpl();
    private final AtomicInteger mCurrentEngineState = new AtomicInteger();
    private final AtomicBoolean mGotStateUpdateOnce = new AtomicBoolean(false);

    class UpdateEngineCallbackImpl extends UpdateEngineCallback {
        @Override
        public void onStatusUpdate(int status, float percent) {
            UpdateManager.this.onStatusUpdate(status, percent);
        }

        @Override
        public void onPayloadApplicationComplete(int errorCode) {
            UpdateManager.this.onPayloadApplicationComplete(errorCode);
        }
    }

    private void onPayloadApplicationComplete(int errorCode) {
        Log.d(TAG, "Complete applying payload, errorCode: "
                + UpdateEngineErrors.getCodeName(errorCode));

        String otaPackageFullPah = otaPackagePath + "/" + otaPackageName;
        try {
            Files.deleteIfExists(Paths.get(otaPackageFullPah));
            Log.d(TAG, "Removed file: " + otaPackageFullPah);
        } catch (NoSuchFileException e) {
            Log.d(TAG, "No such OTA package: " + otaPackagePath);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }

        if (errorCode == UpdateEngine.ErrorCodeConstants.SUCCESS) {
            this.rebootAfterUpdate();
        }
    }

    private void rebootAfterUpdate() {
        Log.d(TAG, "Rebooting device...");
        Intent rebootIntent = new Intent("android.intent.action.REBOOT");
        Bundle bundle = rebootIntent.getExtras();
        if (bundle != null) {
            for (String key : bundle.keySet()) {
                Log.d(TAG, key + " : " + (bundle.get(key) != null ? bundle.get(key) : "NULL"));
            }
        }
        rebootIntent.putExtra("nowait", 1);
        rebootIntent.putExtra("interval", 1);
        rebootIntent.putExtra("window", 0);
        this.mContext.sendBroadcast(rebootIntent);
    }

    private void onStatusUpdate(int status, float percent) {
        Log.d(TAG, String.format("Update status: %s, progress: %.2f%%",
                UpdateEngineStatuses.getStatusText(status), percent * 100.0f));

        mCurrentEngineState.set(status);
        // This is the first status update received from the UpdateEngine
        if(!mGotStateUpdateOnce.get()) {
            handleUpdateEngineInitialState(status);
        }
        mGotStateUpdateOnce.set(true);
    }

    private void handleUpdateEngineInitialState(int status) {
        Log.d(TAG, "Initial state received from UpdateEngine: " +  UpdateEngineStatuses.getStatusText(status));
        if(status == UpdateEngine.UpdateStatusConstants.UPDATED_NEED_REBOOT) {
            Log.w(TAG, "UpdateEngine is reporting that a reboot is required.");
            Log.w(TAG, "Either an update was performed outside RDFM, or the application crashed during a previous update.");
            Log.w(TAG, "Forcing a reboot.");
            rebootAfterUpdate();
        }
    }

    public void bind() {
        this.mUpdateEngine.bind(mUpdateEngineCallback);
    }

    public void unbind() {
        this.mUpdateEngine.unbind();
    }

    public boolean canSafelyCheckForUpdates() {
        return mCurrentEngineState.get() == UpdateEngine.UpdateStatusConstants.IDLE;
    }

    public void applyUpdate(String otaName) {
        otaPackageName = otaName;
        try {
            mUpdateData.mPayload.update(otaPackagePath, otaName);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        this.updateEngineApplyPayload(mUpdateData);
    }

    private void updateEngineApplyPayload(UpdateData update) {
        try {
            this.mUpdateEngine.applyPayload(
                    update.getPayload().getUrl(),
                    update.getPayload().getOffset(),
                    update.getPayload().getSize(),
                    update.getPayload().getProperties().toArray(new String[0]));
        } catch (Exception e) {
            Log.e(TAG, "UpdateEngine failed to apply the update", e);
        }
    }
}