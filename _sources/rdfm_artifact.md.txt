# RDFM Artifact utility

## Introduction

The RDFM Artifact tool (`rdfm-artifact`) allows for easy creation and modification of RDFM Linux client-compatible artifacts containing rootfs partition images. 
A basic RDFM artifact consists of a rootfs image, as well as its checksum, metadata and compatibility with certain device types.

Additionally, `rdfm-artifact` allows for the generation of delta updates, which contain only the differences between two versions of an artifact rather than the entire artifact itself.
This can be useful for reducing the size of updates and improving the efficiency of the deployment process.

## Getting started

In order to support robust updates and rollback, the RDFM Client requires proper partition layout and integration with the U-Boot bootloader. To make it easy to integrate the RDFM Client into your Yocto image-building project, it's recommended to use the [meta-rdfm](https://github.com/antmicro/meta-antmicro/tree/master/meta-rdfm) Yocto layer when building the BSPs.

## Building from source

### Requirements

* Go compiler
* C Compiler
* liblzma-dev and libglib2.0-dev packages

### Steps

To build `rdfm-artifact` on a device from source, clone the repository and build the binary using `make`:

```
git clone https://github.com/antmicro/rdfm.git && cd tools/rdfm-artifact/
make
```

## Basic usage

The basic functionality of writing an artifact is available with the `write` subcommand:

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

For creating a delta artifact, you should have already created two separate full-rootfs artifacts:

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
