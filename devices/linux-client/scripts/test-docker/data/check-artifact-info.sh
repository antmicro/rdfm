#!/usr/bin/env bash
# This script runs in the spawned Docker container.
# You should execute run-integration-test.sh instead to run the tests.
set -e -o pipefail

cd /data/

# When mounting the repository in the container, the UIDs will match the user on the host machine
# This script is running as root to allow for installation into system directories in the container
# Workaround for Git complaining about mismatch ("detected dubious ownership in repository at '/data'")
git config --global --add safe.directory /data

# Install RDFM in the container
make install
make install-conf

ARTIFACT_DUMMY="RDFM_TEST_ARTIFACT_NAME"
PROVIDES_DUMMY="rootfs-image.checksum=RDFM_TEST_DUMMY_VALUE"

mkdir -p /etc/rdfm/
mkdir -p /var/lib/rdfm/

# Add dummy artifact information
cat >/etc/rdfm/artifact_info << EOF
artifact_name=$ARTIFACT_DUMMY
EOF
cat >/etc/rdfm/provides_info << EOF
$PROVIDES_DUMMY
EOF

# Copy custom config to the configuration directory
cp -v ./scripts/test-docker/data/etc_rdfm.conf /etc/rdfm/rdfm.conf
cp -v ./scripts/test-docker/data/var_lib_rdfm.conf /var/lib/rdfm/rdfm.conf

# Check if the output is sane
if ! rdfm show-artifact | grep $ARTIFACT_DUMMY; then
	echo "Artifact name is invalid!"
	echo "Expected $ARTIFACT_DUMMY, got $(rdfm show-artifact)"
	exit 1
fi

if ! rdfm show-provides | grep $PROVIDES_DUMMY; then
	echo "Provides are invalid!"
	echo "Expected $PROVIDES_DUMMY, got $(rdfm show-provides)"
	exit 1
fi

echo "Test successful"
exit 0

