# rdfm-artifact - artifact creation tool for RDFM

Copyright (c) 2023 [Antmicro](https://www.antmicro.com)

Artifact creation and management utility for RDFM.

## Description

RDFM is an open-source over-the-air (OTA) update set of tools that enables the management and delivery of system releases to embedded Linux devices.

This repository contains the `rdfm-artifact` command line tool. It allows for easy creation and modification of RDFM-compatible artifacts containing rootfs partition images.
A basic RDFM artifact consists of a rootfs image, as well as its checksum, metadata and compatibility with certain device types. 

Additionally, `rdfm-artifact` allows for the generation of delta updates, which contain only the differences between two versions of an artifact rather than the entire artifact itself.
This can be useful for reducing the size of updates and improving the efficiency of the deployment process.


## Getting started
In order to support rollback, the RDFM requires proper partition layout and integration with the U-Boot bootloader. To make it easy to integrate RDFM into your Yocto image-building project, it's recommended to use the [meta-rdfm](https://github.com/antmicro/meta-antmicro/tree/master/meta-rdfm) Yocto layer when building the BSPs.

To start using RDFM, we recommend that you begin with ['How to use'](https://github.com/antmicro/meta-antmicro/tree/master/meta-rdfm#how-to-use) section in the [meta-rdfm](https://github.com/antmicro/meta-antmicro/tree/master/meta-rdfm) Yocto layer documentation.

## Building from source
### Requirements
* Go compiler
* C Compiler
* liblzma-dev and libglib2.0-dev packages

### Steps
To build `rdfm-artifact` on a device from source, clone the repository and build the binary using `make`:
```
git clone https://github.com/antmicro/rdfm-artifact.git && cd rdfm-artifact/
make
```

## Basic usage

The basic functionality of writing an artifact is available by using the `write` subcommand:

```
NAME:
   rdfm-artifact write - Allows creation of RDFM-compatible artifacts

USAGE:
   rdfm-artifact write command [command options] [arguments...]

COMMANDS:
   rootfs-image        Create a full rootfs image artifact
   delta-rootfs-image  Create a delta rootfs artifact

OPTIONS:
   --help, -h  show help
```

### Creating a full-rootfs artifact

For example, to create a simple rootfs artifact for a given system image:

```
rdfm-artifact write rootfs-image \
	--file "my-rootfs-image.img" \
	--artifact-name "my-artifact-name" \
	--device-type "my-device-type" \
	--output-path "path-to-output.rdfm"
```

### Creating a delta rootfs artifact

For creating a delta artifact, you must have already created two separate full-rootfs artifacts:
- base artifact - the rootfs image that the deltas will be applied on top of, or in other words: the currently running rootfs on the device
- target artifact - the updated rootfs image that will be installed on the device

Given these two artifacts, a delta artifact can be generated like this:
```
rdfm-artifact write delta-rootfs-image \
    --base-artifact "base.rdfm" \
    --target-artifact "target.rdfm" \
    --output-path "base-to-target.rdfm"
```

## Running tests

To run `rdfm-artifact` tests, use the `test`  Makefile target:

```
make test
```

## License

`rdfm-artifact` is licensed under the Apache-2.0 license. For details, see the [LICENSE](LICENSE) file.
