package com.antmicro.update.rdfm.utilities;

public class StringUtils {
    public static String bytesToHexString(byte[] bytes, String separator) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) {
            sb.append(separator);
            sb.append(String.format("%02X", b));
        }
        // Skip over first separator
        return sb.substring(1);
    }
}
