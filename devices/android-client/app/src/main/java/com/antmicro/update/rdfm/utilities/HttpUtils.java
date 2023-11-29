package com.antmicro.update.rdfm.utilities;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.Objects;

public class HttpUtils {
    /**
     * Replace HTTP scheme in the given URL with `ws`.
     * This also handles HTTPS schemes, in which case the resulting
     * WS URL has the `wss` scheme.
     * If no scheme is present, `wss` is assumed.
     *
     * @param url HTTP/S URL
     * @return URL with WS scheme
     */
    public static String replaceHttpSchemeWithWs(String url) {
        URI uri = URI.create(url);
        String oldScheme = uri.getScheme();
        String newScheme;
        if (Objects.equals(oldScheme, "http")) {
            newScheme = "ws";
        } else if (Objects.equals(oldScheme, "https") || oldScheme == null) {
            newScheme = "wss";
        } else {
            throw new RuntimeException("Server URL has invalid scheme: " + oldScheme);
        }
        try {
            return new URI(newScheme, uri.getSchemeSpecificPart(), uri.getFragment()).toString();
        } catch (URISyntaxException e) {
            throw new RuntimeException("Malformed server URL", e);
        }
    }
}
