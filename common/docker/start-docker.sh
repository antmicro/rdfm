#!/usr/bin/env bash
set -e

# This script starts the docker daemon inside a container
# This is used to run delta artifact tests without having to
# build and run a separate OS in a VM

if [ "$(id -u)" != "0" ]; then
	echo "You must be root to run this script."
	exit 1
fi

export DOCKER_HOST="unix:///var/run/docker-dind.sock"
export DOCKER_DRIVER=vfs
export DOCKER_CONTEXT=dind
export LOGDIR="$(pwd)/logs/"

mkdir -v -p "$LOGDIR"
ls /var/run/docker.sock || true

# Start dockerd in the background
dockerd \
	-H $DOCKER_HOST \
	-s $DOCKER_DRIVER >$LOGDIR/dockerd.log 2>&1 & disown

# Sleep for a bit until the daemon starts
sleep 10

# Set up a custom context so we use the right socket (the daemon
# we just started)
docker context create "$DOCKER_CONTEXT" --docker host="$DOCKER_HOST"
docker context use "$DOCKER_CONTEXT"

# For debugging, print some docker info
docker info
docker version

