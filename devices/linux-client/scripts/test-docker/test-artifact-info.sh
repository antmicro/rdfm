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

# Mount the sources to /data and spawn a Docker container
docker run \
	-v "$BASEDIR:/data" \
	--rm \
	-it	$BASEIMAGE \
	bash -c /data/scripts/test-docker/data/check-artifact-info.sh

