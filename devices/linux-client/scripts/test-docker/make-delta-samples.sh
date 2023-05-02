#!/usr/bin/env bash
set -e -o pipefail

if ! which rdfm-artifact; then
	echo "rdfm-artifact is required for making delta sample artifacts"
	exit 1
fi

# Create dummy system "images"
dd if=/dev/urandom of=vloop0.img bs=512 count=2048 iflag=fullblock
cp vloop0.img vloop1.img
# Replace a part of the second image with random data
dd if=/dev/urandom of=vloop1.img bs=512 count=2 seek=16 conv=notrunc iflag=fullblock
# Save the "updated" image - the vloop1 will be overwritten by the tests
cp vloop1.img vloop1good.img

rdfm-artifact write rootfs-image \
	--file vloop0.img \
	--artifact-name "release-1" \
	--device-type "dummy" \
	--output-path vloop0.rdfm

rdfm-artifact write rootfs-image \
	--file vloop1.img \
	--artifact-name "release-2" \
	--device-type "dummy" \
	--output-path vloop1.rdfm

rdfm-artifact write delta-rootfs-image \
	--base-artifact vloop0.rdfm \
	--target-artifact vloop1.rdfm \
	--output-path vloop0_to_vloop1.delta.rdfm

