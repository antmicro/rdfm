#!/usr/bin/env bash

set -exo pipefail

this_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
out_dir="${OUT_DIR:-$( realpath "$this_dir/../out" )}"

zephyr_version="v3.5.0"

serial_board="nrf52840dk_nrf52840"
udp_board="stm32f746g_disco"
udp_overlay="$this_dir/stm32f7.overlay"

key_file="$this_dir/key.pem"

version1="1.0.1+23"
version2="2.1.2+34"

setup_zephyr() {
    pip install west

    mkdir -p $ZEPHYR_WORKSPACE
    pushd $ZEPHYR_WORKSPACE
    west init --mr $zephyr_version
    west update
    west zephyr-export
    pip install -r $ZEPHYR_BASE/scripts/requirements.txt
    popd

    mkdir -p $ZEPHYR_SDK_INSTALL_DIR
    pushd $ZEPHYR_SDK_INSTALL_DIR
    wget -q -O - https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v0.16.5-1/zephyr-sdk-0.16.5-1_linux-x86_64.tar.xz | tar xJ --strip-components=1
    ./setup.sh -c -t arm-zephyr-eabi
    popd
}

generate_key() {
    $ZEPHYR_WORKSPACE/bootloader/mcuboot/scripts/imgtool.py keygen -k "$key_file" -t rsa-2048
}

# name, board, ...rest
build_mcuboot() {
    west build \
        -d "mcuboot-$1" \
        -b "$2" \
        $ZEPHYR_WORKSPACE/bootloader/mcuboot/boot/zephyr \
        -- \
            -DCONFIG_BOOT_SIGNATURE_KEY_FILE="\"$key_file\"" \
            "${@:3}"

    mkdir -p "$out_dir"
    cp "mcuboot-$1/zephyr/zephyr.elf" "$out_dir/$1.elf"
}

# overlay_type, board_type, target_version, ...rest
build_smp_sample() {
    west build \
        -d $1 \
        -b "$2" \
        "$ZEPHYR_BASE/samples/subsys/mgmt/mcumgr/smp_svr" \
        -- \
            -DEXTRA_CONF_FILE="overlay-$1.conf" \
            -DCONFIG_MCUBOOT_SIGNATURE_KEY_FILE="\"$key_file\"" \
            -DCONFIG_MCUBOOT_IMGTOOL_SIGN_VERSION="\"$3\"" \
            "${@:4}"
}

# overlay_type, board_type, ...rest
build_samples() {
    build_smp_sample \
        "$1" \
        "$2" \
        "$version1" \
        "${@:3}"
    cp "$1/zephyr/zephyr.signed.hex" "$out_dir/$1.signed.hex"

    build_smp_sample \
        "$1" \
        "$2" \
        "$version2" \
        "${@:3}"
    cp "$1/zephyr/zephyr.signed.bin" "$out_dir/$1.signed.bin"
}


setup_zephyr
generate_key

# Build bootloader for serial
build_mcuboot serial \
    $serial_board \
    -DCONFIG_BOOT_SWAP_USING_MOVE=y

# Build bootloader for udp
build_mcuboot udp \
    $udp_board \
    -DDTC_OVERLAY_FILE="$udp_overlay;app.overlay" \
    -DCONFIG_BOOT_SWAP_USING_SCRATCH=y

# Build serial samples
build_samples serial \
    "$serial_board" \
    -DCONFIG_MCUBOOT_BOOTLOADER_MODE_SWAP_WITHOUT_SCRATCH=y

# Build udp samples
build_samples udp \
    "$udp_board" \
    -DCONFIG_NET_CONFIG_MY_IPV4_ADDR="\"192.0.2.1\"" \
    -DCONFIG_ETH_STM32_HAL_API_V1=y \
    -DDTC_OVERLAY_FILE="$udp_overlay" \
    -DCONFIG_MCUBOOT_BOOTLOADER_MODE_SWAP_SCRATCH=y
