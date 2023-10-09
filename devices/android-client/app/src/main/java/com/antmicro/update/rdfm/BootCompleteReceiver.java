package com.antmicro.update.rdfm;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

public class BootCompleteReceiver extends BroadcastReceiver {

    private static final String TAG = "BootCompleteReceiver";

    @Override
    public void onReceive(Context context, Intent intent) {
        String action = intent.getAction();
        try {
            if (Intent.ACTION_BOOT_COMPLETED.equals(action)) {
                Intent updateIntent = new Intent(context, StartAppService.class);
                updateIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                context.startForegroundService(updateIntent);
                Log.d(TAG, "Boot complete");
            }
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}