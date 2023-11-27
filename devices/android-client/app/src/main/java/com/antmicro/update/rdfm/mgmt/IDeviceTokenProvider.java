package com.antmicro.update.rdfm.mgmt;

import com.antmicro.update.rdfm.exceptions.DeviceUnauthorizedException;
import com.antmicro.update.rdfm.exceptions.ServerConnectionException;

public interface IDeviceTokenProvider {
    /**
     * Fetches a device token that can be used for authorizing with the server.
     * This function fetches a valid device token for interacting with the RDFM API.
     *
     * @return Valid device token
     */
    String fetchDeviceToken() throws ServerConnectionException, DeviceUnauthorizedException;
}
