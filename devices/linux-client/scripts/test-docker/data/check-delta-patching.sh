#!/usr/bin/env bash
# This script runs in the spawned Docker container.
# You should execute test-deltas.sh instead to run the associated test.
set -e -o pipefail

if [[ -z "$1" || -z "$2" ]]; then
	echo "missing loop device paths!"
	exit 1
fi

ARTIFACT_DUMMY="RDFM_TEST_ARTIFACT_NAME"
PROVIDES_DUMMY="rootfs-image.checksum=RDFM_TEST_DUMMY_VALUE"
PART_A="$1"
PART_B="$2"
echo "Running tests in container with loop devices: $PART_A $PART_B"

# More pleasing logging
log_info()
{
	local TEAL="\E[36m"
	local NO_COLOUR="\E[0m"

	echo -ne "$TEAL"
	echo -ne "[i] $@"
	echo -ne "$NO_COLOUR"
	echo ""
}

# Compile RDFM and install it into the container
# This also sets up some dummy configuration values, which are later overwritten
setup_environment()
{
	cd /data/

	# When mounting the repository in the container, the UIDs will match the user on the host machine
	# This script is running as root to allow for installation into system directories in the container
	# Workaround for Git complaining about mismatch ("detected dubious ownership in repository at '/data'")
	git config --global --add safe.directory /data

	# Install RDFM in the container
	make install
	make install-conf

	mkdir -p /etc/rdfm/
	mkdir -p /var/lib/rdfm/

	# Add dummy artifact/device information
	cat >/etc/rdfm/artifact_info << EOF
artifact_name=$ARTIFACT_DUMMY
EOF
	cat >/etc/rdfm/provides_info << EOF
$PROVIDES_DUMMY
EOF
	cat >/var/lib/rdfm/device_type << EOF
device_type=dummy
EOF

	# Copy custom config to the configuration directory
	cp -v ./scripts/test-docker/data/etc_rdfm.conf /etc/rdfm/rdfm.conf
	cp -v ./scripts/test-docker/data/var_lib_rdfm.conf /var/lib/rdfm/rdfm.conf

	# Patch the configuration for rootfs partitions to pass in the loop devices
	# # A/B are /dev/dummydevA and /dev/dummydevB respectively
	sed -i "s;/dev/dummydevA;$PART_A;" /var/lib/rdfm/rdfm.conf
	sed -i "s;/dev/dummydevB;$PART_B;" /var/lib/rdfm/rdfm.conf
}

# This tests the dependency tracking for delta updates
# The install should fail at this point, as the rootfs-image.checksum does not contain the
# correct checksum.
test_dependency_tracking()
{
	set +e
	OUT="$(rdfm --log-level debug install ./scripts/test-docker/vloop0_to_vloop1.delta.rdfm 2>&1)"
	if echo -ne "$OUT" | grep "not satisfied"; then
		log_info "test dependency tracking: OK"
		set -e
		return 0
	fi

	log_info "test dependency tracking: FAIL"
	set -e
	return 1
}

# Prepare for actual delta instalation tests
# Sets up the environment for faking installation to the loop device
setup_test_delta_installation()
{
	# Reset the database, while passing the correct checksum now
	CHECKSUM=($(sha256sum $PART_A))
	cat >/etc/rdfm/provides_info << EOF
rootfs-image.checksum=$CHECKSUM
EOF
	rm /var/lib/rdfm/*-store

	# We need to fake a boot environment getter, which will return the currently booted partition
	# fw_printenv and fw_setenv are required to complete the installation process
	# Both are just no-ops
	cat >/usr/bin/fw_printenv<< EOF
#!/bin/sh
exit 0
EOF
	cat >/usr/bin/fw_setenv << EOF
#!/bin/sh
exit 0
EOF
	chmod +x /usr/bin/fw_setenv
	chmod +x /usr/bin/fw_printenv

	# We fake that the root partition is mounted on PART_A, so that the delta will be installed
    # on PART_B.
	mkdir -p /tmp/mount_wrapper/
	cat >/tmp/mount_wrapper/mount<< EOF
#!/bin/sh
echo "$PART_A on / type ext4 (dummyvalues)"
EOF
	chmod +x /tmp/mount_wrapper/mount
	# Ensure the mount wrapper is before everything else in PATH
	export PATH=/tmp/mount_wrapper/:$PATH
}

# Install the delta artifact and validate the checksum on the secondary partition
test_delta_installation()
{
	if ! rdfm install ./scripts/test-docker/vloop0_to_vloop1.delta.rdfm; then
		log_info "test delta installation: FAIL"
		return 1
	fi

	# Validate the checksum of the secondary partition
	CHECKSUM=($(sha256sum $PART_B))
	TARGET=($(sha256sum ./scripts/test-docker/vloop1good.img))

	if [[ "$CHECKSUM" != "$TARGET" ]]; then
		log_info "test delta installation: FAIL"
		return 1
	fi

	log_info "test delta installation: OK"
	return 0
}

# =====================================================

setup_environment

test_dependency_tracking

setup_test_delta_installation
test_delta_installation

log_info "Test successful"
exit 0

