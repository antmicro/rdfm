package com.antmicro.update.rdfm.utilities;

import android.annotation.SuppressLint;
import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.util.Log;

import com.antmicro.update.rdfm.MainActivity;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.net.SocketException;
import java.util.Collections;
import java.util.List;
import java.util.stream.Collectors;

public class SysUtils {
    public static final int APP_RESTART_INTENT_MAGIC = 492738126;
    private static final String TAG = "SysUtils";

    public static String findDeviceMAC() {
        try {
            List<NetworkInterface> interfaces = Collections.list(NetworkInterface.getNetworkInterfaces());
            // Find the first network interface that contains a non-local IP address.
            // The MAC of this interface is used as the device identifier.
            for (NetworkInterface nif : interfaces) {
                byte[] macBytes = nif.getHardwareAddress();
                if (macBytes == null) {
                    continue;
                }

                List<InetAddress> nonLocalAddresses = Collections.list(nif.getInetAddresses())
                        .stream()
                        .filter(inetAddress -> !inetAddress.isAnyLocalAddress())
                        .filter(inetAddress -> !inetAddress.isLoopbackAddress())
                        .filter(inetAddress -> !inetAddress.isLinkLocalAddress())
                        .collect(Collectors.toList());
                if(nonLocalAddresses.isEmpty()) {
                    continue;
                }

                String macAddress = StringUtils.bytesToHexString(macBytes, ":");
                Log.d(TAG, "Using MAC address: " + macAddress + " from network interface: " + nif.getName() + " as device identifier");
                return macAddress;
            }
        } catch (SocketException e) {
            throw new RuntimeException("Error while discovering primary network interface MAC", e);
        }
        throw new RuntimeException("Failed to determine MAC of the primary network interface!");
    }

    @SuppressLint("PrivateApi")
    public static String getSystemProperties(String properties) {
        Class<?> c;
        try {
            c = Class.forName("android.os.SystemProperties");
        } catch (ClassNotFoundException e) {
            throw new RuntimeException(e);
        }
        Method get;
        try {
            get = c.getMethod("get", String.class);
        } catch (NoSuchMethodException e) {
            throw new RuntimeException(e);
        }
        try {
            return (String) get.invoke(c, new Object[]{properties});
        } catch (IllegalAccessException | InvocationTargetException e) {
            throw new RuntimeException(e);
        }
    }

    public static String getBuildVersion() {
        return Build.VERSION.INCREMENTAL;
    }

    public static String getDeviceType() {
        return Build.PRODUCT;
    }

    public static void restartApp(Context c) {
        try {
            Intent intent = new Intent(c, MainActivity.class);
            PendingIntent pendingIntent = PendingIntent.getActivity(c, APP_RESTART_INTENT_MAGIC, intent, PendingIntent.FLAG_CANCEL_CURRENT | PendingIntent.FLAG_IMMUTABLE);
            AlarmManager mgr = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
            mgr.set(AlarmManager.RTC, System.currentTimeMillis() + 100, pendingIntent);
            System.exit(0);
        } catch (Exception ex) {
            Log.e(TAG, "Unable to restart application!");
        }
    }
}
