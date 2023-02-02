#!/usr/bin/env bash
set -e -o pipefail

if ! which rdfm-artifact; then
	echo "rdfm-artifact is required for making delta sample artifacts"
	exit 1
fi
if ! which rdiff; then
	echo "rdiff is required for creating deltas"
	exit 1
fi

# Create dummy system "images"
dd if=/dev/random of=vloop0.img bs=512 count=2048
cp vloop0.img vloop1.img
# Replace a part of the second image with random data
dd if=/dev/random of=vloop1.img bs=512 count=2 seek=16 conv=notrunc
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

if [ -f /tmp/rootfs-old.sig ]; then
	rm /tmp/rootfs-old.sig
fi

BASEHASH=($(tar -xOf vloop0.rdfm data/0000.tar.gz | tar -xzOf- | sha256sum))
tar -xOf vloop0.rdfm data/0000.tar.gz | tar -xzOf- | rdiff signature -R rollsum -b 4096 - /tmp/rootfs-old.sig
cp -v vloop1.rdfm /tmp/delta-artifact.rdfm

rdfm-artifact modify \
	--delta-compress /tmp/rootfs-old.sig \
	--depends "rootfs-image.checksum:$BASEHASH" \
	/tmp/delta-artifact.rdfm

cp -v /tmp/delta-artifact.rdfm vloop0_to_vloop1.delta.rdfm

