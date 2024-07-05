#!/usr/bin/env bash

set -exo pipefail

this_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
work_dir=${WORK_DIR:-$( realpath "$this_dir/../work" )}
out_dir="${OUT_DIR:-$( realpath "$this_dir/../out" )}"

zephyr_version="v3.6.0"

serial_board="nrf52840dk_nrf52840"
udp_board="stm32f746g_disco"
udp_overlay="$this_dir/boards/$udp_board.overlay"

key_file="$work_dir/key.pem"

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
    wget -q -O - https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v0.16.8/zephyr-sdk-0.16.8_linux-x86_64.tar.xz | tar xJ --strip-components=1
    ./setup.sh -c -t arm-zephyr-eabi
    popd
}

generate_key() {
    mkdir -p "$work_dir"
    $ZEPHYR_WORKSPACE/bootloader/mcuboot/scripts/imgtool.py keygen -k "$key_file" -t rsa-2048
}

# name, board, ...rest
build_mcuboot() {
    west build \
        -d "$work_dir/mcuboot-$1" \
        -b "$2" \
        $ZEPHYR_WORKSPACE/bootloader/mcuboot/boot/zephyr \
        -- \
            -DCONFIG_BOOT_SIGNATURE_KEY_FILE="\"$key_file\"" \
            "${@:3}"

    mkdir -p "$out_dir"
    cp "$work_dir/mcuboot-$1/zephyr/zephyr.elf" "$out_dir/$1.elf"
}

# overlay_type, out_file, board_type, target_version, ...rest
build_smp_sample() {
    west build \
        -d "$work_dir/$2" \
        -b "$3" \
        "$this_dir" \
        -- \
            -DEXTRA_CONF_FILE="overlay-$1.conf" \
            -DCONFIG_MCUBOOT_SIGNATURE_KEY_FILE="\"$key_file\"" \
            -DCONFIG_MCUBOOT_IMGTOOL_SIGN_VERSION="\"$4\"" \
            "${@:5}"
}

# overlay_type, out_file, board_type, ...rest
build_samples() {
    build_smp_sample \
        "$1" \
        "$2" \
        "$3" \
        "$version1" \
        "${@:4}"
    cp "$work_dir/$2/zephyr/zephyr.signed.hex" "$out_dir/$2.signed.hex"

    build_smp_sample \
        "$1" \
        "$2" \
        "$3" \
        "$version2" \
        "${@:4}"
    cp "$work_dir/$2/zephyr/zephyr.signed.bin" "$out_dir/$2.signed.bin"
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

# Build serial sample
build_samples serial \
    serial \
    "$serial_board" \
    -DCONFIG_MCUBOOT_BOOTLOADER_MODE_SWAP_WITHOUT_SCRATCH=y \
    -DCONFIG_UPDATE_SELF_CONFIRM=y

# Build udp sample
build_samples udp \
    udp \
    "$udp_board" \
    -DCONFIG_NET_CONFIG_MY_IPV4_ADDR="\"192.0.2.2\"" \
    -DCONFIG_ETH_STM32_HAL_API_V1=y \
    -DCONFIG_MCUBOOT_BOOTLOADER_MODE_SWAP_SCRATCH=y

# Build group device sample
build_samples serial \
    serial-gr \
    "$serial_board" \
    -DCONFIG_MCUBOOT_BOOTLOADER_MODE_SWAP_WITHOUT_SCRATCH=y

build_samples udp \
    udp-gr \
    "$udp_board" \
    -DCONFIG_NET_CONFIG_MY_IPV4_ADDR="\"192.0.2.3\"" \
    -DCONFIG_ETH_STM32_HAL_API_V1=y \
    -DCONFIG_MCUBOOT_BOOTLOADER_MODE_SWAP_SCRATCH=y \
    -DCONFIG_UPDATE_SELF_CONFIRM=y
