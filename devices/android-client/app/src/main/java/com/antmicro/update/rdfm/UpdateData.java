package com.antmicro.update.rdfm;

import android.util.Log;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

public class UpdateData {
    private static final String TAG = "UpdateData";
    public static final String PAYLOAD_BINARY_FILE_NAME = "payload.bin";
    public static final String PAYLOAD_PROPERTIES_FILE_NAME = "payload_properties.txt";
    public final PayloadSpec mPayload = new PayloadSpec();
    public UpdateData() {}

    public PayloadSpec getPayload() {
            return mPayload;
    }

    public static class PayloadSpec {
        private String mUrl;
        private long mOffset;
        private long mSize;
        private List<String> mProperties;

        public String getUrl() {
            return mUrl;
        }
        public long getOffset() {
            return mOffset;
        }

        public long getSize() {
            return mSize;
        }

        public List<String> getProperties() {
            return mProperties;
        }

        public void update(String otaPackagePath, String otaPackageName) throws IOException {
            File root = new File(otaPackagePath);
            if (!root.exists()) {
               throw new IOException("No root path: "+ root.getAbsolutePath());
            }

            for (final File f : root.listFiles()) {
                if(f.getName().equals(otaPackageName)) {
                   unzipPackage(f);
                }
            }
        }

        private void unzipPackage(File otaPkgPath) throws IOException {
            boolean payloadFound = false;
            boolean payloadPropertiesFound = false;

            List<String> properties = new ArrayList<>();
            try (ZipFile zip = new ZipFile(otaPkgPath)) {
                Enumeration<? extends ZipEntry> entries = zip.entries();
                long offset = 0;
                while (entries.hasMoreElements()) {
                    ZipEntry entry = entries.nextElement();
                    String name = entry.getName();
                    Log.d(TAG, "Found file: " + name);

                    // Zip local file header has 30 bytes + filename + sizeof extra field.
                    // https://en.wikipedia.org/wiki/Zip_(file_format)
                    long extraSize = entry.getExtra() == null ? 0 : entry.getExtra().length;
                    offset += 30 + name.length() + extraSize;

                    if (entry.isDirectory()) {
                        continue;
                    }

                    long length = entry.getCompressedSize();
                    if (PAYLOAD_BINARY_FILE_NAME.equals(name)) {
                        payloadFound = true;
                        mOffset = offset;
                        mSize = entry.getCompressedSize();
                    } else if (PAYLOAD_PROPERTIES_FILE_NAME.equals(name)) {
                        payloadPropertiesFound = true;
                        InputStream inputStream = zip.getInputStream(entry);
                        if (inputStream != null) {
                            BufferedReader br = new BufferedReader(new InputStreamReader(inputStream));
                            String line;
                            while ((line = br.readLine()) != null) {
                                properties.add(line);
                            }
                        }
                    }
                    offset += length;
                }
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
            if (!payloadFound) {
                throw new IOException("Payload in the OTA package not found.");
            } else {
                mUrl = "file://" + otaPkgPath.getAbsolutePath();
                if (!payloadPropertiesFound) {
                    properties.add("SWITCH_SLOT_ON_REBOOT=1");
                }
                mProperties = properties;
            }
        }
    }
}