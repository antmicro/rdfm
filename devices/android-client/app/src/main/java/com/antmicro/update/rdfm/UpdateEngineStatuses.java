package com.antmicro.update.rdfm;

import android.util.SparseArray;

public class UpdateEngineStatuses {

    private UpdateEngineStatuses() {}
    private static final SparseArray<String> STATUS_MAP = new SparseArray<>();
    static {
        STATUS_MAP.put(0, "IDLE");
        STATUS_MAP.put(1, "CHECKING_FOR_UPDATE");
        STATUS_MAP.put(2, "UPDATE_AVAILABLE");
        STATUS_MAP.put(3, "DOWNLOADING");
        STATUS_MAP.put(4, "VERIFYING");
        STATUS_MAP.put(5, "FINALIZING");
        STATUS_MAP.put(6, "UPDATED_NEED_REBOOT");
        STATUS_MAP.put(7, "REPORTING_ERROR_EVENT");
        STATUS_MAP.put(8, "ATTEMPTING_ROLLBACK");
        STATUS_MAP.put(9, "DISABLED");
        STATUS_MAP.put(10, "NEED_PERMISSION_TO_UPDATE");
    }

    /**
     * converts status code to status name
     */
    public static String getStatusText(int status) {
        return STATUS_MAP.get(status);
    }
}
