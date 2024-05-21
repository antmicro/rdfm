# RDFM Artifact utility

## Introduction

The RDFM Artifact tool (`rdfm-artifact`) allows for easy creation and modification of RDFM Linux client-compatible artifacts containing rootfs partition images. 
A basic RDFM artifact consists of a rootfs image, as well as its checksum, metadata and compatibility with certain device types.

Additionally, `rdfm-artifact` allows for the generation of delta updates, which contain only the differences between two versions of an artifact rather than the entire artifact itself.
This can be useful for reducing the size of updates and improving the efficiency of the deployment process.

`rdfm-artifact` can also be used for generation of Zephyr MCUboot artifacts, which allows for updating embedded devices running Zephyr.
Additionally, multiple Zephyr images can be combined into one grouped artifact to allow multiple boards to act as one logical device.

## Getting started

In order to support robust updates and rollback, the RDFM Client requires proper partition layout and a bootloader that supports A/B update scheme. To make it easy to integrate the RDFM Client into your Yocto image-building project, it's recommended to use the [meta-rdfm](https://github.com/antmicro/meta-antmicro/tree/master/meta-rdfm) Yocto layer when building the BSPs.

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
   zephyr-image        Create a full Zephyr MCUboot image artifact
   zephyr-group-image  Create a Zephyr MCUboot group image artifact

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

### Creating a Zephyr MCUboot artifact

To create a Zephyr MCUboot artifact, you'll have to have already created a Zephyr image with MCUboot support enabled.
You should use the signed bin image (by default `zephyr.signed.bin`).
Artifact version will be extracted from provided image.

With this image, you can generate an artifact like so:

```
rdfm-artifact write zephyr-image \
   --file "my-zephyr-image.signed.bin" \
   --artifact-name "my-artifact-name" \
   --device-type "my-device-type" \
   --output-path "path-to-output.rdfm"
```

### Creating a Zephyr MCUboot group artifact

To create a grouped Zephyr MCUboot artifact, you should have already created at least two Zephyr images with MCUboot support enabled.
The version of individual images in a grouped artifact must be identical.

Given images `one.bin` and `two.bin` for group targets `one` and `two` respectively, an artifact can be generated with:

```
rdfm-artifact write zephyr-group-image \
	--group-type "my-group" \
	--target "one:one.bin" \
	--target "two:two.bin" \
	--ouptput-path "path-to-output.rdfm"
```

:::{note}
It's possible to create a grouped artifact with just one image,
however in cases like that you should create simple [zephyr-image](#creating-a-zephyr-mcuboot-artifact) instead.
:::

## Running tests

To run `rdfm-artifact` tests, use the `test`  Makefile target:

```
make test
```
