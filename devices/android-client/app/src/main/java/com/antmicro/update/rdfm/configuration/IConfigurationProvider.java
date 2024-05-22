package com.antmicro.update.rdfm.configuration;

public interface IConfigurationProvider {
    /**
     * Get the configured RDFM server address
     *
     * @return RDFM server address to connect to, or null if an error occurred
     *         while reading the configuration
     */
    String getServerAddress();

    /**
     * Get the configured update interval
     *
     * @return automatic update interval [seconds], or -1 if an error occurred
     *         while reading the configuration
     */
    int getUpdateIntervalSeconds();

    /**
     * Get the configured maximum reverse shell count
     *
     * @return max reverse shell count, or -1 if an error occurred
     *         while reading the configuration
     */
    int getMaxShellCount();
}
