package com.antmicro.update.rdfm;

import android.annotation.SuppressLint;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.app.TaskStackBuilder;
import android.content.Context;
import android.content.Intent;
import android.os.IBinder;
import android.util.Log;

import androidx.core.app.NotificationCompat;
import androidx.core.app.NotificationManagerCompat;

public class StartAppService extends Service {
    private static final String TAG = "StartAppService";
    private static final String CHANNEL_ID = "systemUpdate";
    private static final int SERVICE_ID = 1;

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onCreate() {
        super.onCreate();
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Intent mainIntent = new Intent(this, MainActivity.class);
        mainIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        Log.d(TAG, "Start activity by service");
        this.startActivity(mainIntent);
        this.startServiceForeground(mainIntent);
        return super.onStartCommand(intent, flags, startId);
    }

    private void startServiceForeground(Intent activityIntent) {
        this.createNotifyChannel(activityIntent);
        Log.d(TAG, "Started foreground service");
    }

    @SuppressLint("MissingPermission")
    private void createNotifyChannel (Intent contentIntent) {
        TaskStackBuilder stackBuilder = TaskStackBuilder.create(this);
        stackBuilder.addNextIntentWithParentStack(contentIntent);
        PendingIntent resultIntent = stackBuilder.getPendingIntent(0, PendingIntent.FLAG_UPDATE_CURRENT);

        NotificationManager manager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        manager.createNotificationChannel(
                new NotificationChannel(
                        CHANNEL_ID,
                        "UpdateChannel",
                        NotificationManager.IMPORTANCE_DEFAULT)
        );

        NotificationCompat.Builder notificationBuilder = new NotificationCompat.Builder(this, CHANNEL_ID);
        Notification notification = notificationBuilder.setOngoing(true)
                .setCategory(Notification.CATEGORY_SERVICE)
                .setChannelId(CHANNEL_ID)
                .setContentIntent(resultIntent)
                .setContentTitle("Update app is running in background")
                .setPriority(NotificationManager.IMPORTANCE_DEFAULT)
                .setSmallIcon(R.mipmap.ic_launcher)
                .build();

        NotificationManagerCompat notificationManager = NotificationManagerCompat.from(this);
        notificationManager.notify(1, notificationBuilder.build());
        startForeground(SERVICE_ID, notification);
    }
}