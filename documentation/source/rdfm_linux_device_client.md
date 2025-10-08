# RDFM Linux Device Client

## Introduction

The RDFM Linux Device Client (`rdfm-client`) integrates an embedded Linux device with the RDFM Server.
This allows for performing robust Over-The-Air (OTA) updates of the running system and remote management of the device.

`rdfm-client` runs on the target Linux device and handles the process of checking for updates in the background along with maintaining a connection to the RDFM Management Server.

## Getting started

In order to support robust updates and rollback, the RDFM Client requires proper partition layout and integration with the U-Boot bootloader. To make it easy to integrate the RDFM Client into your Yocto image-building project, it's recommended to use the [meta-rdfm](https://github.com/antmicro/meta-antmicro/tree/master/meta-rdfm) Yocto layer when building the BSPs.

## Management functionality

Other than the always-available OTA component, `rdfm-client` implements some additional remote management functionality.

### Actions

Actions allow execution of predefined sets of commands remotely via the RDFM server.
These commands are defined in an `actions.conf` JSON configuration file found in the daemon's configuration directory.
For the configuration schema, see the [RDFM actions config](#rdfm-actions-config) section.

The action list is synchronized with the server, and is available for querying via the [Action List API](api.rst#get--api-v2-devices-\(string-mac_address\)-action-list) endpoint.
Actions can be executed using the [Action Execute API](api.rst#get--api-v2-devices-(string-mac_address)-action-exec-(string-action_id)) endpoint.

All action execution requests are stored in a persistent queue on a disk and fulfilled in a First-In, First-Out order.
By default, there can be a maximum of **32 action requests** in the queue, and any further action execution requests are rejected by the client.
This limit can be configured via the [ActionQueueSize](#actionqueuesize-int) configuration key.
An identical queue is also present for action responses, and action status is reported to the server as soon as it is possible to do so.
This allows actions to remain usable, even when the device faces connectivity or power loss issues.

Action functionality can be disabled entirely via the [ActionEnable](#actionenable-bool) configuration key.

### Reverse shell

The client supports spawning a reverse shell that can be accessed via the RDFM server.
This utilizes an on-demand WebSocket connection between the server and the device to stream contents of the shell session.
To connect to the device, [`rdfm-mgmt`](./rdfm_manager.md) can be used to request a shell session:

```bash
rdfm-mgmt devices shell <device-identifier>
```

By default, a maximum of 5 concurrent shell sessions can be opened.
This limit can be configured via the [ShellConcurrentMaxCount](#shellconcurrentmaxcount-int) configuration key.
Further shell session requests will be rejected by the client.

Shell functionality can be disabled entirely via the [ShellEnable](#shellenable-bool) configuration key.

### File downloading

The client supports downloading files from the device its running on. It utilizes intermediate S3 bucket or local storage, depending on RDFM server configuration. To download files [`rdfm-mgmt`](./rdfm_manager.md) can be used:

```bash
rdfm-mgmt devices download <device> <remote-file-path> <local-file-path>
```

You can limit locations of downloadable files to the specific directory using the [FileSystemBaseDir](filesystembasedir-string) configuration key. You can also disable the functionality completely via the [FileSystemEnable](filesystemenable-bool) configuration key.

## Installing from source

### Requirements

* C compiler
* Go compiler
* liblzma-dev, libssl-dev and libglib2.0-dev packages
* [go-xdelta](https://github.com/antmicro/go-xdelta) library

### Steps

To install an RDFM client on a device from source, first clone the repository and build the binary:
```
git clone https://github.com/antmicro/rdfm.git && cd devices/linux-client/
make
```

Then run the install command:
```
make install
```

Ensure the go-xdelta library is installed beforehand. You can install it by following the instructions in the go-xdelta repository. Use the CMake options `-DCGO_INTEGRATION=ON -DENCODER=ON` during the build process.

### Installation notes

Installing `rdfm` this way does not offer a complete system updater.
System updates require additional integration with the platform's bootloader and a dual-root partition setup for robust updates.
For this, it's recommended to build complete BSPs containing `rdfm` using the [meta-rdfm](https://github.com/antmicro/meta-antmicro/tree/master/meta-rdfm) Yocto layer.

## Building using Docker

All build dependencies for compiling the RDFM Client are included in a dedicated Dockerfile. To build a development container image, you can use:

```
git clone https://github.com/antmicro/rdfm.git && cd devices/linux-client/
sudo docker build -t rdfmbuilder .
```

This will create a Docker image that can be later used to compile the RDFM binary:

```
sudo docker run --rm -v <rdfm-dir>:/data -it rdfmbuilder
cd data/devices/linux-client
make
```

## Configuring the client

### RDFM default config

The main config file contents are located in `/etc/rdfm/rdfm.conf`. It's JSON formatted and with the following keys of interest:

#### RootfsPartA `string`

Partition A for the A/B updating scheme.

#### RootfsPartB `string`

Partition B for the A/B updating scheme.

### RDFM overlay config

The file `/var/lib/rdfm/rdfm.conf` defines the high-level RDFM client configurations. They are overlaid over the configuration located in `/etc/rdfm/rdfm.conf` during client startup.

#### DeviceTypeFile `string`

Path to the device type file.

#### UpdatePollIntervalSeconds `int`

Poll interval for checking for new updates.

#### RetryPollIntervalSeconds `int`

Maximum number of seconds between each retry when authorizing.

#### ServerCertificate `string`

Path to a server SSL certificate.

#### ServerURL `string`

Management server URL.

#### HttpCacheEnabled `bool`

Describing if artifact caching is enabled. True by default.

#### ReconnectRetryCount `int`

HTTP reconnect retry count.

#### ReconnectRetryTime `int`

HTTP reconnect retry time.

#### TelemetryEnable `bool`

Describing if telemetry is enabled. False by default.

#### TelemetryBatchSize `int`

Number of log entries to be sent to a management server at a time. Fifty by default.

#### TelemetryLogLevel `string`

Denotes which log levels produced by the client should be captured provided that telemetry is enabled. There are seven levels of logs:

1. trace
2. debug
3. info
4. warn
5. error
6. fatal
7. panic

Setting a level encapsulates all the levels that are above it in severity. For example, setting this to `"fatal"` will capture all fatal *and* panic level logs. This config entry is not case sensitive. In the case of this field being left empty or with an incorrect value, the daemon will produce a warning and continue running normally.

#### ActionEnable `bool`

Allows enabling/disabling action functionality.
True by default.

#### ActionQueueSize `int`

Specifies the size of the action queue.
`32` by default.

#### ShellEnable `bool`

Allows enabling/disabling reverse shell functionality.
True by default.

#### ShellConcurrentMaxCount `int`

Specifies how many concurrent shell sessions can be spawned.
`5` by default.

#### FileSystemEnable `bool`

Allows enabling/disabling filesystem functionality.
True by default.

#### FileSystemBaseDir `string`

Specifies base directory of downloadable files.
`/` by default.

### RDFM telemetry config

The JSON structured `loggers.conf` file, laying under `/etc/rdfm/`, serves as a configuration file that defines a set of loggers to be executed once the client establishes a connection to the RDFM management server. Each logger can be any executable binary, which will be invoked by the client at predefined intervals. The client captures and processes the output generated by these loggers, providing a flexible mechanism for collecting and reporting system or application data during runtime.

The `loggers.json` file contains an array of dictionaries, each of which describes a logger.

Consider the following example:

```json
[
    {
    "name": "current date",
    "path": "date",
    "args": ["--rfc-email"],
    "tick": 1000
    }
]
```

:::{note} Since the file gives the capacity to run arbitrary binaries, its permissions must be set to `-rw-r--r--`.
:::

#### name `string`

Denotes the name of the logger, each one should have a unique name. Loggers lower in the file will overwrite their counterparts that are above them.

#### path `string`

A path to an executable to be ran.

#### args `[]string`

A list of arguments for the given executable.

#### tick `int`

Number of milliseconds between each time a logger is ran. In the case of a logger taking more than `tick` to execute, it is killed and the client reports a timeout error.

### RDFM actions config

The JSON structured `/var/lib/rdfm/actions.conf` file contains a list of actions that can be executed on the device.
Each action contains a command to execute and a timeout.
Identifiers are used in `action_exec` messages sent from the server to select the action to execute.
Name and description can be used for user-friendly display.
Actions defined in the configuration can be queried using `action_list_query`.

Example configuration:
```json
[
{
    "Id": "echo",
    "Name": "Echo",
    "Command": ["echo", "Executing echo action"],
    "Description": "Description of echo action",
    "Timeout": 1.0
},
{
    "Id": "sleepTwoSeconds",
    "Name": "Sleep 2",
    "Command": ["sleep", "2"],
    "Description": "Description of sleep 2 seconds action",
    "Timeout": 3.0
},
{
    "Id": "sleepFiveSeconds",
    "Name": "Sleep 5",
    "Command": ["sleep", "5"],
    "Description": "This action will timeout",
    "Timeout": 3.0
}
]
```

:::{note} Since the file gives the capacity to run arbitrary binaries, its permissions must be set to `-rw-r--r--`.
:::

#### Id `string`

Identifier used in execution requests, must be unique.

#### Name `string`

Human readable name, should be unique.

#### Command `[]string`

Command to execute, the first elements is an executable, others are arguments.

#### Description `string`

Human readable action description.

#### Timeout `float`

Maximum duration of command execution in seconds, command is killed if it doesn't finish in the time provided.

## Testing server-device integration with a demo Linux device client

For development purposes, it's often necessary to test server integration with an existing device client.
To do this, it is possible to use the [RDFM Linux device client](rdfm_linux_device_client.md), without having to build a compatible system image utilizing the Yocto [meta-rdfm layer](https://github.com/antmicro/meta-antmicro/tree/master/meta-rdfm).
First, build the demo container image:

```
cd devices/linux-client/
make docker-demo-client
```

You can then start a demo Linux client by running the following:
```
docker-compose -f docker-compose.demo.yml up
```

If required, the following environment variables can be changed in the above `docker-compose.demo.yml` file:

- `RDFM_CLIENT_SERVER_URL` - URL to the RDFM Management Server, defaults to `http://127.0.0.1:5000/`.
- `RDFM_CLIENT_SERVER_CERT` **(optional)** - path (within the container) to the CA certificate to use for verification of the connection to the RDFM server. When this variable is set, the server URL must also be updated to use HTTPS instead of HTTP.
- `RDFM_CLIENT_DEVTYPE` - device type that will be advertised to the RDFM server; used for determining package compatibility, defaults to `x86_64`.
- `RDFM_CLIENT_PART_A`, `RDFM_CLIENT_PART_B` **(optional)** - specifies path (within the container) to the rootfs A/B partitions that updates will be installed to. They do not need to be specified for basic integration testing; any updates that are installed will go to `/dev/zero` by default.

The demo client will automatically connect to the specified RDFM server and fetch any available packages.
To manage the device and update deployment, you can use the [RDFM Manager utility](rdfm_manager.md).

## Developer Guide

### Running tests

Use the `test` make target to run the unit tests:

```
make test
```

Additionally, run the scripts available in the `scripts/test-docker` directory. These scripts test basic functionality of the RDFM client.
