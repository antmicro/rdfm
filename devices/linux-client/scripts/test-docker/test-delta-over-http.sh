#!/usr/bin/env bash
set -e -o pipefail

BASEIMAGE="rdfmbuilder"
SCRIPTDIR=$(dirname "$(readlink -f "$0")")
BASEDIR="$SCRIPTDIR/../../"
echo "Script directory: $SCRIPTDIR"

(
	# Build the RDFM docker image
	cd $BASEDIR
	docker build -t rdfmbuilder .
)

echo "Mounting virtual block devices"
VBLOCK0=$(sudo losetup --show -f $SCRIPTDIR/vloop0.img)
VBLOCK1=$(sudo losetup --show -f $SCRIPTDIR/vloop1.img)
echo "Path to vblock0: $VBLOCK0"
echo "Path to vblock1: $VBLOCK1"

cleanup()
{
	echo "Cleaning up loop devices"
	sudo losetup -d "$VBLOCK0"
	sudo losetup -d "$VBLOCK1"
}
trap cleanup EXIT

# Mount the sources to /data and spawn a Docker container
docker run \
	-v "$BASEDIR:/data" \
	--device "$VBLOCK0" \
	--device "$VBLOCK1" \
	--rm \
	-it	$BASEIMAGE \
	bash -c "/data/scripts/test-docker/data/check-delta-patching.sh $VBLOCK0 $VBLOCK1 1"
