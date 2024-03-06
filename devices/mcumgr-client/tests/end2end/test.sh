#!/usr/bin/env bash
set -eo pipefail

this_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
base_dir=$( realpath "$this_dir/../../" )
samples_dir=$( realpath "$base_dir/tests/out" )

RENODE_PID=""
SERVER_PID=""
CLIENT_PID=""

serial_dev="serial"
udp_dev="udp"

target_version="2.1.2+34"

_log_info()
{
    echo "=== $1 ==="
}

start_renode() {
    net_if="testTap0"
    net_addr="192.0.2.2/24"

    _log_info "Starting Renode"

    renode \
        --disable-xwt \
        --hide-monitor \
        --hide-log \
        "$this_dir/test.resc" \
            -e 'start' &>/dev/null &
    RENODE_PID=$!

    while [ ! -e /tmp/uartDemo ]; do
        echo "Waiting for serial device..."
        sleep 2
    done

    while ! ip link show $net_if &> /dev/null; do
        echo "Waiting for $net_if interface..."
        sleep 2
    done

    ip link set $net_if
    ip addr add $net_addr dev $net_if
    ip link set $net_if up

    echo "Renode started ($RENODE_PID)"
}

start_rdfm_server() {
    _log_info "Starting RDFM server"

    JWT_SECRET=foobarbaz python \
        -m rdfm_mgmt_server \
            --no-api-auth \
            --no-ssl \
            --hostname localhost \
            --http-port 5000 \
            --database "sqlite:///$base_dir/development.db" \
            --local-package-dir "$base_dir/pkgs" \
                &> "$base_dir/server.log" &
    SERVER_PID=$!

    # Wait for server to start
    while ! curl -s http://localhost:5000 >/dev/null; do
        echo "Waiting for RDFM server..."
        sleep 2
    done

    echo "RDFM server started ($SERVER_PID)"
}

start_mcumgr_client() {
    _log_info "Starting MCUmgr RDFM client"

    rdfm-mcumgr-client \
        --verbose \
        --config "$this_dir/test.config.json" \
            2>&1 | tee "$base_dir/client.log" &
    CLIENT_PID=`pgrep -f -n rdfm-mcumgr-client`

    echo "MCUmgr RDFM client started ($CLIENT_PID)"
}

_dev_id=1
_setup_device() {
    local art="rdfm-artifact"
    local mgmt="rdfm-mgmt --no-api-auth"

    local id=$(( _dev_id++ ))
    local mac_addr="00:00:00:00:00:$(printf '%02d' "$id")"

    echo "Setting up '$1' device"

    echo "Checking device key"
    openssl rsa -check -in "$base_dir/keys/$1.key" | grep "RSA key ok" &> /dev/null

    echo "Creating artifact"
    $art write zephyr-image \
        --output-path "$1.rdfm" \
        --device-type $1 \
        --file "$samples_dir/$1.signed.bin"

    $mgmt packages upload \
        --path "$1.rdfm" \
        --device $1 \
        --version $target_version

    echo "Setting up device group"
    $mgmt groups create \
        --name $1 \
        --description $1

    $mgmt groups assign-package \
        --package-id $id \
        --group-id $id

    $mgmt groups target-version \
        --group-id $id \
        --version $target_version

    echo "Assigning device to group"
    $mgmt devices auth $mac_addr

    $mgmt groups modify-devices \
        --group-id $id \
        --add $id
}

setup_devices() {
    _log_info "Setting up test devices"
    timeout --preserve-status 10 \
        rdfm-mcumgr-client \
            --config "$this_dir/test.config.json" \
            --verbose \
            --retries 1

    _setup_device $serial_dev
    _setup_device $udp_dev
}

run_test() {
    # 1 hour
    test_timeout=$(( 60 * 60 ))

    SECONDS=0
    while [ $SECONDS -lt $test_timeout ]; do
        # Make sure all components still running
        if ! ps -p $RENODE_PID >/dev/null; then
            echo "Renode is not running"
            exit 1
        fi
        if ! ps -p $SERVER_PID >/dev/null; then
            echo "Server is not running"
            exit 1
        fi
        if ! ps -p $CLIENT_PID >/dev/null; then
            echo "Client is not running"
            exit 1
        fi

        # Check for client errors
        if grep -q -m 1 "ERROR" "$base_dir/client.log"; then
            echo "Client encountered error"
            exit 1
        fi

        if [ `grep -m 2 -c "new_version=$target_version" "$base_dir/client.log"` -eq 2 ]; then
            _log_info "Update finished"
            exit 0
        fi

        echo "Waiting for update to finish..."
        sleep 30
    done

    echo "Timeout"
    exit 1
}

start_renode
start_rdfm_server

setup_devices
start_mcumgr_client

run_test

