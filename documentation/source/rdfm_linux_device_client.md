# RDFM Linux Device Client

## Introduction

The RDFM Linux Device Client (`rdfm-client`) integrates an embedded Linux device with the RDFM Server.
This allows for performing robust Over-The-Air (OTA) updates of the running system and remote management of the device.

`rdfm-client` runs on the target Linux device and handles the process of checking for updates in the background along with maintaining a connection to the RDFM Management Server.

## Getting started

In order to support robust updates and rollback, the RDFM Client requires proper partition layout and integration with the U-Boot bootloader. To make it easy to integrate the RDFM Client into your Yocto image-building project, it's recommended to use the [meta-rdfm](https://github.com/antmicro/meta-antmicro/tree/master/meta-rdfm) Yocto layer when building the BSPs.

## Installing from source

### Requirements

* C compiler
* Go compiler
* liblzma-dev, libssl-dev and libglib2.0-dev packages

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
