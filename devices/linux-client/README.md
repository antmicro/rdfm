RDFM: over-the-air updater for embedded Linux devices
=====================================================

Remote Device Fleet Manager (RDFM) is an open-source the over-the-air (OTA) software updater for embedded Linux
devices.
To address the challenges of updating embedded Linux devices, RDFM offers both *robust* and *easy to integrate* OTA updater.

This repository contains sources for the `rdfm` command-line tool, which is used for artifact update installation on the device.

## Getting started
In order to support rollback, the RDFM requires proper partition layout and integration with the U-Boot bootloader. To make it easy to integrate RDFM into your Yocto image-building project, it's recommended to use the [meta-rdfm](https://github.com/antmicro/meta-antmicro/tree/master/meta-rdfm) Yocto layer when building the BSPs.

To start using RDFM, we recommend that you begin with ['How to use'](https://github.com/antmicro/meta-antmicro/tree/master/meta-rdfm#how-to-use) section in the [meta-rdfm](https://github.com/antmicro/meta-antmicro/tree/master/meta-rdfm) Yocto layer documentation.

## Building using Docker
All build dependencies for RDFM compilation are included in a dedicated Dockerfile. To build a development container image, you can use:
```
git clone https://github.com/antmicro/rdfm.git && cd rdfm/
sudo docker build -t rdfmbuilder .
```

This will create a Docker image that can be later used to compile the RDFM binary:
```
sudo docker run --rm -v <rdfm-dir>:/data -it rdfmbuilder
cd data/
make
```

## Installing from source
### Requirements
* C compiler
* Go compiler
* liblzma-dev, libssl-dev and libglib2.0-dev packages

### Steps
To install RDFM client on a device from source, first clone the repository and build the binary:
```
git clone https://github.com/antmicro/rdfm.git && cd rdfm/
make
```

Then run the install command:
```
make install
```

### Installation notes
Installing `rdfm` this way does not offer a complete system updater.
For this, it's recommended to build complete BSPs containing `rdfm` using [meta-rdfm](https://github.com/antmicro/meta-antmicro/tree/master/meta-rdfm) Yocto layer.

## Running tests
Use the `test` make target to run the unit tests:
```
make test
```

Additionally, run the scripts available in the `scripts/test-docker` directory. These scripts test basic functionality of the RDFM client.
