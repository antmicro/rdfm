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
IS_HTTP=${3:-0}
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
	sed -i "s;/dev/dummydevA;$PART_A;" /etc/rdfm/rdfm.conf
	sed -i "s;/dev/dummydevB;$PART_B;" /etc/rdfm/rdfm.conf
}

# Reset the environment to its initial state
reset_environment()
{
	# Remove database files
	rm -f /var/lib/rdfm/*-store

	# Restore default provides_info
	cat >/etc/rdfm/provides_info << EOF
$PROVIDES_DUMMY
EOF

	# Restore default artifact_info
	cat >/etc/rdfm/artifact_info << EOF
artifact_name=$ARTIFACT_DUMMY
EOF
}

# This tests the dependency tracking for delta updates
# The install should fail at this point, as the rootfs-image.checksum does not contain the
# correct checksum.
test_dependency_tracking()
{
	local delta_algorithm=$1
	local artifact_path=$2

	set +e
	OUT="$(rdfm --log-level debug install $artifact_path 2>&1)"
	if echo -ne "$OUT" | grep "not satisfied"; then
		log_info "test dependency tracking for $delta_algorithm: OK"
		set -e
		return 0
	fi

	log_info "test dependency tracking for $delta_algorithm: FAIL"
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
	local delta_algorithm=$1
	local artifact_path=$2
	local target_image=$3

	if [[ $IS_HTTP == 0 ]]; then
		if ! rdfm install $artifact_path; then
			log_info "test delta installation for $delta_algorithm: FAIL"
			return 1
		fi
	else
		set +e
		log_info "Running first update for $delta_algorithm"
		timeout 5 rdfm install http://127.0.0.1:8000/$artifact_path
		log_info "Killed first update for $delta_algorithm"
		set -e
		log_info "Running second update for $delta_algorithm"
		if ! rdfm install http://127.0.0.1:8000/$artifact_path; then
			log_info "test delta installation for $delta_algorithm: FAIL"
			return 1
		fi
	fi

	# Validate the checksum of the secondary partition
	CHECKSUM=($(sha256sum $PART_B))
	TARGET=($(sha256sum $target_image))

	if [[ "$CHECKSUM" != "$TARGET" ]]; then
		log_info "test delta installation for $delta_algorithm: FAIL"
		return 1
	fi

	log_info "test delta installation for $delta_algorithm: OK"
	return 0
}

setup_http_server()
{
	DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -qy python3-pip
	pip install rangehttpserver --break-system-packages
	pushd ./scripts/test-docker
	echo "Starting HTTP server"
	python3 ./data/server.py 8000 &
	sleep 1
	popd
}

# Main test function for a given delta algorithm (rsync or xdelta)
run_tests_for_algorithm()
{
    local delta_algorithm=$1
    local artifact_file="vloop0_to_vloop1.$delta_algorithm.rdfm"
    local local_artifact_path="./scripts/test-docker/$artifact_file"
    local artifact_path="$local_artifact_path"
    local target_image="./scripts/test-docker/vloop1good.img"

    if [[ $IS_HTTP == 1 ]]; then
        artifact_path="$artifact_file"
    fi

    reset_environment

    test_dependency_tracking "$delta_algorithm" "$local_artifact_path"
    setup_test_delta_installation
    test_delta_installation "$delta_algorithm" "$artifact_path" "$target_image"
}

# =====================================================
# Main execution flow
setup_environment

if [[ $IS_HTTP == 1 ]]; then
	setup_http_server
fi

# Run tests for both algorithms
run_tests_for_algorithm "rsync"
run_tests_for_algorithm "xdelta"

log_info "All tests successful"
exit 0
