package com.antmicro.update.rdfm.configuration;

public interface IConfigurationProvider {
    /**
     * Get the configured RDFM server address
     *
     * @return RDFM server address to connect to
     */
    String getServerAddress();

    /**
     * Get the configured update interval
     *
     * @return automatic update interval [seconds]
     */
    int getUpdateIntervalSeconds();

    /**
     * Get the configured maximum reverse shell count
     *
     * @return max reverse shell count
     */
    int getMaxShellCount();
}
