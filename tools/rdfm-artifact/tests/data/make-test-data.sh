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

if [ ! -f ./dummy-single-file.bin ]; then
	DUMMYSIZE="1048576"
	BLOCKSIZE="512"

	# Create a dummy invalid "zephyr binary"
	dd if=/dev/random of=dummy-single-file.bin.img bs=$BLOCKSIZE count=$(( DUMMYSIZE / BLOCKSIZE ))

	echo "WARNING: Single file binaries were regenerated"
	echo "WARNING: You must change the hashes in the tests to match the generated images"
	echo "WARNING: The tests WILL fail if you do not do this!"
fi

INVALID_SINGLE_FILE_DIR="./invalid_single_file"

if [ ! -d $INVALID_SINGLE_FILE_DIR ]; then
	mkdir -p invalid_single_file
fi

DEST_DIR_FILENAME="dest_dir"
if [ ! -f "$INVALID_SINGLE_FILE_DIR/${DEST_DIR_FILENAME}" ]; then
	echo "'${INVALID_SINGLE_FILE_DIR}/${DEST_DIR_FILENAME}' file not found, creating a dummy file"
	echo "This is a dummy ${DEST_DIR_FILENAME} file" > "$INVALID_SINGLE_FILE_DIR/${DEST_DIR_FILENAME}"
fi

PERMISSIONS_FILENAME="permissions"
if [ ! -f "$INVALID_SINGLE_FILE_DIR/${PERMISSIONS_FILENAME}" ]; then
	echo "'${INVALID_SINGLE_FILE_DIR}/${PERMISSIONS_FILENAME}' file file not found, creating a dummy file"
	echo "This is a dummy ${PERMISSIONS_FILENAME} file" > "$INVALID_SINGLE_FILE_DIR/${PERMISSIONS_FILENAME}"
fi

ROLLBACK_SUPPORT_FILENAME="rollback_support"
if [ ! -f "$INVALID_SINGLE_FILE_DIR/${ROLLBACK_SUPPORT_FILENAME}" ]; then
	echo "'${INVALID_SINGLE_FILE_DIR}/${ROLLBACK_SUPPORT_FILENAME}' file file not found, creating a dummy file"
	echo "This is a dummy ${ROLLBACK_SUPPORT_FILENAME} file" > "$INVALID_SINGLE_FILE_DIR/${ROLLBACK_SUPPORT_FILENAME}"
fi

FILENAME_FILENAME="filename"
if [ ! -f "$INVALID_SINGLE_FILE_DIR/${FILENAME_FILENAME}" ]; then
	echo "'${INVALID_SINGLE_FILE_DIR}/${FILENAME_FILENAME}' file file not found, creating a dummy file"
	echo "This is a dummy ${FILENAME_FILENAME} file" > "$INVALID_SINGLE_FILE_DIR/${FILENAME_FILENAME}"
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
