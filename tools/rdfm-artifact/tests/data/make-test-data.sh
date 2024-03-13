#!/usr/bin/env bash
set -e

if ! which rdfm-artifact; then
	echo "rdfm-artifact not found, cannot generate test artifacts"
	exit 1
fi

if [ ! -f ./dummy-rootfs.img ]; then
	DUMMYSIZE="1048576"
	BLOCKSIZE="512"
	# Create a dummy "rootfs image"
	dd if=/dev/random of=dummy-rootfs.img bs=$BLOCKSIZE count=$(( DUMMYSIZE / BLOCKSIZE ))

	# Create a dummy "updated rootfs image"
	# Overwrite a part of the above file to simulate changes in the partition
	cp dummy-rootfs.img dummy-update-rootfs.img
	dd if=/dev/random of=dummy-update-rootfs.img bs=$BLOCKSIZE count=1 conv=notrunc

	echo "WARNING: Payload images were regenerated"
	echo "WARNING: You must change the hashes in the tests to match the generated images"
	echo "WARNING: The tests WILL fail if you do not do this!"
fi

if [ ! -f ./dummy-zephyr.img ]; then
	DUMMYSIZE="25600"
	BLOCKSIZE="512"

	# Create a dummy invalid "zephyr binary"
	dd if=/dev/random of=dummy-zephyr.invalid.img bs=$BLOCKSIZE count=$(( DUMMYSIZE / BLOCKSIZE ))

	# Create a dummy valid "zephyr binary"
	# Prepend valid magic bytes (in little endian order) to invalid binary
	printf '\x3d\xb8\xf3\x96' | cat - dummy-zephyr.invalid.img > dummy-zephyr.img

	# Keep the valid image with random version for group artifact tests
	cp dummy-zephyr.img dummy-group.invalid.img

	# Set valid image version to 0.1.2+3
	printf '\x00\x01\x02\x00\x03\x00\x00\x00' | dd of=dummy-zephyr.img bs=1 seek=20 count=8 conv=notrunc

	# Create a second valid image for group artifact tests
	# Overwrite a part of the copy to simulate different image
	cp dummy-zephyr.img dummy-group.img
	dd if=/dev/random of=dummy-group.img bs=$BLOCKSIZE seek=30 count=1 conv=notrunc

	echo "WARNING: Zephyr images were regenerated"
	echo "WARNING: You must change the hashes in the tests to match the generated images"
	echo "WARNING: The tests WILL fail if do not do this!"
fi

rdfm-artifact write rootfs-image \
	--file "dummy-rootfs.img" \
	--artifact-name "dummy-artifact" \
	--device-type "dummy-device-type" \
	--output-path "dummy-artifact.rdfm"

# Generate base artifact for delta tests
rdfm-artifact write rootfs-image \
	--file "dummy-rootfs.img" \
	--artifact-name "delta-base" \
	--device-type "some-device-type" \
	--output-path "delta-base.rdfm"

# Generate target artifact for delta tests
# We add some custom depends value to test whether the metadata is cloned properly
# when generating the delta.
rdfm-artifact write rootfs-image \
	--file "dummy-update-rootfs.img" \
	--artifact-name "delta-target" \
	--device-type "some-device-type" \
	--output-path "delta-target.rdfm" \
	--provides AAAAAAAA:11111111 \
	--depends BBBBBBBB:22222222
