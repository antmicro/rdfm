# Server Integration flows

This chapter describes the various integration flows between device clients and the RDFM Management server.

## Device authentication

At the start of their execution, all RDFM-compatible device clients shall authenticate with the server.
This shall be done by utilizing the `/api/v1/auth/device` endpoint.
For details on the request schema, refer to the [Server API Reference](api.rst) chapter.
An example request made to this endpoint is shown below:

```json
{
    "metadata": {
        "rdfm.hardware.devtype": "device-type",
        "rdfm.software.version": "foo",
        "rdfm.hardware.macaddr": "00:11:22:33:44:55",
    }
    "public_key": "<RSA public key of the device in PEM format>",
    "timestamp": 1694681536,
}
```

The JSON payload bytes must be signed by the device client with its securely stored RSA private key using PKCS #1 v1.5 signature with SHA-256 digest (function `RSASSA-PKCS1-V1_5-SIGN` defined in [RFC 8017](https://datatracker.ietf.org/doc/html/rfc8017#section-8.2.1))
The calculated signature must then be attached, encoded as base64, to the authorization request in the header `X-RDFM-Device-Signature`.
If the server successfully validates the attached signature, the device will be registered in the server's database, if it wasn't previously registered already.
The device-specified MAC address is used as a unique identifier for this specific device.

Before the device is authorized to access the RDFM API, it must be accepted first by an  administrative entity interacting via a separate API with the RDFM server.
If the device was not accepted, or its acceptation status was revoked, the above request shall fail with the `401 Unauthorized` HTTP status code. **The device client must handle this status code gracefully**, for example by retrying the attempted request after a certain time has passed.

Once the device is accepted into the RDFM server, the above request shall return a device-specific app token, that can be used to interact with device-side API endpoints.
The app token is not permanent, and will expire after a certain time period.
The device client must not make any assumptions about the length of the usability period, and instead should take a defensive approach to any requests made to the device-side API and reauthenticate when a response with the `401` status code is received.

## Device update check

Once authorized, a device client will have access to the device-side API of the RDFM server.
The device client is expected to regularly poll for updates by utilizing the `/api/v1/update/check` endpoint.

In the update check request, the device client must provide all of its local metadata.
The metadata, which consists of simple key/value pairs, uniquely describes the set of software and/or hardware present on the device, but may also represent other transient
properties not persisted in storage, such as temperature sensor values.

When making the update check, the device client is advised to provide all of its metadata to the server in the update request.
At the time of writing, below three metadata properties are mandatory and must be present in all update checks:

- `rdfm.software.version` - version identifier of the currently running software package
- `rdfm.hardware.devtype` - device type, used for limiting package compatibility only to a subset of devices
- `rdfm.hardware.macaddr` - MAC address of the device's main network interface

For future compatibility, device clients are advised to provide all of their metadata, not only the mandatory keys, in the update check request.
For more details on the structure of an update check request, consult the [Update API Reference](api.rst#post--api-v1-update-check)

When a new package is available, the response shall be as described in the API Reference, and a one-time download URL to the package is generated.
The device client shall use this URL to download and install, or in the case of clients capable of stream installation, directly install the package.
The device client **MUST** verify the hash of the package as described in the update check response.

Additionally, the device client **MUST** verify whether the package contents look sane before attempting to install it.
The server shall never return a package that is not of the same device type as the one advertised by the client.
However, the server itself currently imposes **no limitations** on the binary contents of the packages themselves.

## Management WebSocket

If supported, the device may also connect to a device management WebSocket.
This provides additional management functionality of registered devices, such as reverse shell and file transfer.
To connect to the WebSocket, a device token is required to be provided in the `Authorization` header of the WebSocket handshake.
The format of the header is exactly the same as in other device routes and is described [in the API Reference chapter](api.rst#api-authentication).

The general management flow is as follows:
1. Device connects to the management WebSocket: `/api/v1/devices/ws`
1. Device sends a `CapabilityReport` message indicating the capabilities it supports
1. Device reads incoming management messages from the server and handles them accordingly
1. Device may also send messages to the server to notify of certain situations

### RDFM Management Protocol

The management protocol is message-oriented and all messages are expected to be sent in WebSocket text mode.
Each message is a JSON object in the form:
```json
{
    "method": "<method_name>",
    "arg0": "...",
    "arg1": {"...": "..."},
    "...": "..."
}
```

The type of message sent is identified by the `method` field.
The rest of the object fields are unspecified and depend on the specific message type.
Schema for messages used by the server can be found in `common/communication/src/request_models.py`.
On error during handling of a request, the server may return a custom WebSocket status code.
A list of status codes used by the server can be found in `common/communication/src/rdfm/ws.py`.

### Capabilities

A capability indicates what management functionality is supported by a device.
The device should report its capabilities using the `CapabilityReport` message immediately after connecting to the server.
By default it is assumed that the device does not provide any capabilities.

#### Capability - `shell`

This capability indicates that a device supports spawning a reverse shell.
The following methods must be supported by the device:
- `shell_attach`

A device with the `shell` capability should react to `shell_attach` messages by connecting to a shell WebSocket at `/api/v1/devices/<shell_attach.mac_addr>/shell/attach/<shell_attach.uuid>`.
This establishes a connection between the requesting manager and the device.
This WebSocket can then be used to stream the contents of the shell session and receive user input.
The format of messages sent over this endpoint is implementation defined.
However, generally the shell output/input are simply sent as binary WebSocket messages containing the standard output/input as raw bytes.
