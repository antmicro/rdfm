# System Architecture

The reference architecture of an RDFM system consists of:

- `RDFM Management Server` - handles device connections, packages, deployment, remote device management
- `Devices` - devices connect to a central management server and utilize the exposed `REST API` and device-server RDFM protocol for providing remote management functionality
- `Users` - individual users that are authenticated and allowed read-only/read-write access to resources exposed by the server

The system architecture can be visualized as follows:

:::{figure-md} summary
![Architecture summary](images/summary.png)

Summary of the system architecture
:::

## HTTP REST API

For functionality not requiring a persistent connection, the server exposes an HTTP API. A complete list of available endpoints can be found
in the [RDFM Server API Reference](api.rst) chapter. The clients use this API to perform update checks.

## Device-server RDFM Protocol

The devices also maintain a persistent connection to the RDFM Management Server by utilizing JSON-based messages sent over a WebSocket route.
This is used to securely expose additional management functionality without directly exposing device ports to the Internet.

Each message sent using the RDFM protocol is structured as follows:

```text
0                            h
+----------------------------+
| utf-8 encoded JSON message |
+----------------------------+
```

The message is a UTF-8 encoded JSON object, where each message is distinguished by the mandatory ``'method'`` field.

An example request sent to the server may look like:

``{'method': 'capability_report', 'capabilities': {'shell': True}}``

A response from the server may look like:

``{'method': 'alert', 'alert': {'devices': ['d1', 'd2']}}``
