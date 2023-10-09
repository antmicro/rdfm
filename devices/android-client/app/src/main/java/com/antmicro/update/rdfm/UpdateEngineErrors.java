package com.antmicro.update.rdfm;

import android.util.SparseArray;

public class UpdateEngineErrors {

    private UpdateEngineErrors() {}
    private static final SparseArray<String> CODE_NAME = new SparseArray<>();
    static {
        CODE_NAME.put(0, "SUCCESS");
        CODE_NAME.put(1, "ERROR");
        CODE_NAME.put(4, "FILESYSTEM_COPIER_ERROR");
        CODE_NAME.put(5, "POST_INSTALL_RUNNER_ERROR");
        CODE_NAME.put(6, "PAYLOAD_MISMATCHED_TYPE_ERROR");
        CODE_NAME.put(7, "INSTALL_DEVICE_OPEN_ERROR");
        CODE_NAME.put(8, "KERNEL_DEVICE_OPEN_ERROR");
        CODE_NAME.put(9, "DOWNLOAD_TRANSFER_ERROR");
        CODE_NAME.put(10, "PAYLOAD_HASH_MISMATCH_ERROR");
        CODE_NAME.put(11, "PAYLOAD_SIZE_MISMATCH_ERROR");
        CODE_NAME.put(12, "DOWNLOAD_PAYLOAD_VERIFICATION_ERROR");
        CODE_NAME.put(15, "NEW_ROOTFS_VERIFICATION_ERROR");
        CODE_NAME.put(20, "DOWNLOAD_STATE_INITIALIZATION_ERROR");
        CODE_NAME.put(26, "DOWNLOAD_METADATA_SIGNATURE_MISMATCH");
        CODE_NAME.put(51, "PAYLOAD_TIMESTAMP_ERROR");
        CODE_NAME.put(52, "UPDATED_BUT_NOT_ACTIVE");
    }
    public static String getCodeName(int errorCode) {
        return CODE_NAME.get(errorCode);
    }
}
