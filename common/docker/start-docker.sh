#!/usr/bin/env bash
set -e

# This script starts the docker daemon inside a container
# This is used to run delta artifact tests without having to
# build and run a separate OS in a VM

if [ "$(id -u)" != "0" ]; then
	echo "You must be root to run this script."
	exit 1
fi

export DOCKER_DATA_ROOT="$CI_PROJECT_DIR/.docker_data_root"
export DOCKER_HOST="unix:///var/run/docker.sock"
export DOCKER_DRIVER=vfs
export DOCKER_CONTEXT=dind
export LOGDIR="$(pwd)/logs/"

mkdir -v -p "$LOGDIR"
ls /var/run/docker.sock || true

# Start dockerd in the background
dockerd \
	--data-root=$DOCKER_DATA_ROOT \
	-s fuse-overlayfs \
	--add-runtime=crun=/usr/bin/crun \
	--default-runtime=crun \
	--config-file="" > /dev/null 2>&1 &
# Wait until daemon starts
while ! test -S /var/run/docker.sock; do echo "Waiting for Docker..." && sleep 1; done; echo "Docker started"

# For debugging, print some docker info
docker info
docker version

