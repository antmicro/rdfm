package com.antmicro.update.rdfm.mgmt;

import com.antmicro.update.rdfm.exceptions.DeviceInfoException;
import com.antmicro.update.rdfm.utilities.SysUtils;

import java.util.HashMap;
import java.util.Map;

import kotlin.contracts.Returns;

public class DeviceInfoProvider {
    private String mDeviceMAC;

    public DeviceInfoProvider() {
    }

    /**
     * Get the device MAC to be used as a unique device identifier.
     *
     * @return device MAC
     */
    public String getDeviceMAC() throws DeviceInfoException {
        if (mDeviceMAC == null) {
            try {
                mDeviceMAC = SysUtils.findDeviceMAC();
            } catch (RuntimeException e) {
                throw new DeviceInfoException(e.getMessage());
            }
        }
        return mDeviceMAC;
    }

    /**
     * Get the device type identifier
     *
     * @return device type string
     */
    public String getDeviceType() {
        return SysUtils.getDeviceType();
    }

    /**
     * Get the unique software version identifier
     *
     * @return software version identifier
     */
    public String getSoftwareVersion() {
        return SysUtils.getBuildVersion();
    }

    /**
     * Save the metadata of the device as a map of Strings to String values.
     *
     * @return device metadata in map form
     */
    public Map<String, String> toMap() throws DeviceInfoException {
        Map<String, String> devParams = new HashMap<>();
        devParams.put("rdfm.software.version", getSoftwareVersion());
        devParams.put("rdfm.hardware.macaddr", getDeviceMAC());
        devParams.put("rdfm.hardware.devtype", getDeviceType());
        return devParams;
    }

}
