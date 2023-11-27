package com.antmicro.update.rdfm.mgmt;

public interface IMessageHandler {
    void onAlert(String alert);

    void onShellAttach(String macAddress, String uuid);
}
