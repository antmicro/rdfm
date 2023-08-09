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

## Developer Guide

### Running tests

Use the `test` make target to run the unit tests:

```
make test
```

Additionally, run the scripts available in the `scripts/test-docker` directory. These scripts test basic functionality of the RDFM client.
