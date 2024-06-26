# RDFM MCUmgr Device Client

## Introduction

The RDFM MCUmgr Device Client (`rdfm-mcumgr-client`) allows for integrating an embedded device running ZephyrRTOS with the RDFM server via its MCUmgr SMP server implementation.
Currently, only the update functionality is implemented with support for serial, UDP and BLE transports.

`rdfm-mcumgr-client` runs on a proxy device that's connected to the targets via one of the supported transports that handles the process of checking for updates, fetching update artifacts and pushing update images down to correct targets.

## Getting started

In order to properly function, both the Zephyr application and the `rdfm-mcumgr-client` have to be correctly configured in order for the update functionality to work.
Specifically:
* Zephyr applications must be built with MCUmgr support, with any transport method of your choice and with image management and reboot command groups enabled.
* The device running Zephyr must be connected to a proxy device running `rdfm-mcumgr-client` as the updates are coming from it.
* For reliable updates, the SMP server must be running alongside your application and be accessible at all times.


## Building client from source

### Requirements

* C compiler
* Go compiler (1.22+)
* liblzma-dev and libssl-dev packages

### Steps

To install the proxy client from source, first clone the repository and build the binary:
```sh
git clone https://github.com/antmicro/rdfm.git
cd rdfm/devices/mcumgr-client/
make
```

Then run the install command:
```sh
make install
```

## Setting up target device

### Setting up the bootloader

To allow rollbacks and update verification, the MCUboot bootloader is used. 
Images uploaded by `rdfm-mcumgr-client` are written to a secondary flash partition, while leaving the primary (currently running) image intact.
During update, the images are swapped by the bootloader.
If the update was successful, the new image is permanently set as the primary one, otherwise the images are swapped back to restore the previous version.
For more details on MCUboot, you can read the [official guide](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/mcuboot/readme-zephyr.html#building-and-using-mcuboot-with-zephyr) from MCUboot's website.

#### Generating image signing key

In order to enable updates, MCUboot requires all images to be signed.
During update, the bootloader will first validate the image using this key.

MCUboot provides `imgtool.py` image tool script which can be used to generate appropriate signing key.
Below are the steps needed to generate a new key using this tool:

Install additional packages required by the tool (replace `~/zephyrproject` with path to your Zephyr workspace):
```sh
cd ~/zephyrproject/bootloader/mcuboot
pip3 install --user -r ./scripts/requirements.txt
```

Generate new key:
```sh
cd ~/zephyrproject/bootloader/mcuboot/scripts
./imgtool.py keygen -k <filename.pem> -t <key-type>
```
MCUboot currently supports `rsa-2048`, `rsa-3072`, `ecdsa-p256` or `ed25519` key types.
For more details on the image tool, please refer to its [official documentation](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/mcuboot/imgtool.html).

#### Building the bootloader

Besides the signing key, MCUboot also requires that the target board has specific flash partitions defined in its devicetree.
These partitions are:
* `boot_partition`: for MCUboot itself
* `slot0_partition`: the priamry slot of image 0
* `slot1_partition`: the secondary slot of image 0

If you choose the *swap-using-scratch* update algorithm, one more partition has to be defined:
* `scratch_partition`: the scratch slot

You can check whether your board has those partitions predefined by looking at its devicetree file (`boards/<arch>/<board>/<board>.dts`).
Look for `fixed-partitions` compatible entry. If your default board configuration doesn't specify those partitions (or you would like to modify them),
you can either modify the devicetree file directly or use [devicetree overlays](https://docs.zephyrproject.org/latest/build/dts/howtos.html#set-devicetree-overlays).

Sample overlay file for the `stm32f746g_disco` board:

```dts
#include <mem.h>

/delete-node/ &quadspi;

&flash0 {
    partitions {
        compatible = "fixed-partitions";
        #address-cells = <1>;
        #size-cells = <1>;

        boot_partition: partition@0 {
            label = "mcuboot";
            reg = <0x00000000 DT_SIZE_K(64)>;
        };

        slot0_partition: partition@40000 {
            label = "image-0";
            reg = <0x00040000 DT_SIZE_K(256)>;
        };

        slot1_partition: partition@80000 {
            label = "image-1";
            reg = <0x00080000 DT_SIZE_K(256)>;
        };

        scratch_partition: partition@c0000 {
        	label = "scratch";
        	reg = <0x000c0000 DT_SIZE_K(256)>;
        };
    };
};

/ {
    aliases {
        /delete-property/ spi-flash0;
    };

    chosen {
        zephyr,flash = &flash0;
        zephyr,flash-controller = &flash;
        zephyr,boot-partition = &boot_partition;
        zephyr,code-partition = &slot0_partition;
    };
};
```

:::{note}
If you do use devicetree overlay, make sure to add `app.overlay` as the last overlay file
since it's needed to correctly store the MCUboot image in `boot_partition`.
:::

Besides the devicetree, you also have to specify:
* `BOOT_SIGNATURE_KEY_FILE`: path to the previously generate signing key
* `BOOT_SIGNATURE_TYPE`: signing key type:
    * `BOOT_SIGNATURE_TYPE_RSA` and `BOOT_SIGNATURE_TYPE_RSA_LEN`
    * `BOOT_SIGNATURE_TYPE_ECDSA_P256`
    * `BOOT_SIGNATURE_TYPE_ED25519`
* `BOOT_IMAGE_UPGRADE_MODE`: the [update algorithm](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/mcuboot/design.html#image-slots) used for swapping images in primary and secondary slots:
    * `BOOT_SWAP_USING_MOVE`
    * `BOOT_SWAP_USING_SCRATCH`

For example, if you wanted to build the bootloader for the `stm32f746g_disco` board with partitions defined in `stm32_disco.overlay`,
using *swap-using-scratch* update algorithm and using `rsa-2048` `key.pem` signing key,
you would run (replace `~/zephyrproject` with path to your Zephyr workspace):

```sh
    west build \
        -d mcuboot \
        -b stm32f746g_disco \
        ~/zephyrproject/bootloader/mcuboot/boot/zephyr \
        -- \
            -DDTC_OVERLAY_FILE="stm32_disco.overlay;app.overlay" \
            -DCONFIG_BOOT_SIGNATURE_KEYFILE='"key.pem"' \
            -DCONFIG_BOOT_SIGNATURE_TYPE_RSA=y \
            -DCONFIG_BOOT_SIGNATURE_TYPE_RSA_LEN=2048 \
            -DCONFIG_BOOT_SWAP_USING_SCRATCH=y
```

The produced image can be flashed to your device.
For more details on building and using MCUboot with Zephyr, please refer to [official MCUboot guide](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/mcuboot/readme-zephyr.html#building-and-using-mcuboot-with-zephyr).

### Setting up the Zephyr application

#### Building the image

To allow your application to be used with MCUmgr client, you will have to enable Zephyr's [device management subsystem](https://docs.zephyrproject.org/latest/services/device_mgmt/index.html#device-mgmt).
For the client to function properly, both [*image management*](https://docs.zephyrproject.org/latest/services/device_mgmt/smp_groups/smp_group_1.html)
and [*OS management*](https://docs.zephyrproject.org/latest/services/device_mgmt/smp_groups/smp_group_0.html) groups need to be enabled.
You will also have to enable and configure [SMP transport](https://docs.zephyrproject.org/latest/services/device_mgmt/smp_transport.html)
(either serial, BLE or udp) that you wish to use.
To learn how to do that, you can reference Zephyr's [`smp_svr` sample](https://github.com/zephyrproject-rtos/zephyr/tree/main/samples/subsys/mgmt/mcumgr/smp_svr)
which provides configuration for all of them.

You will also have set `MCUBOOT_BOOTLOADER_MODE` setting to match the *swapping algorithm* you've configured for the [bootloader](#building-the-bootloader):

:::{table}
:name: Swap algorithm configuration options

MCUboot | Zephyr
--- | ---
`BOOT_SWAP_USING_MOVE` | `MCUBOOT_BOOTLOADER_MODE_SWAP_WITHOUT_SCRATCH`
`BOOT_SWAP_USING_SCRATCH` | `MCUBOOT_BOOTLOADER_MODE_SWAP_SCRATCH`
:::

:::{important}
#### Bluetooth specific

Bluetooth transport additionally requires you to manually start SMB Bluetooth advertising.
Refer to the [`main.c`](https://github.com/zephyrproject-rtos/zephyr/blob/dbfc1aaec697b78573c18d83fd40ba66ff63c0b3/samples/subsys/mgmt/mcumgr/smp_svr/src/main.c#L70-L72)
and [`bluetooth.c`](https://github.com/zephyrproject-rtos/zephyr/blob/dbfc1aaec697b78573c18d83fd40ba66ff63c0b3/samples/subsys/mgmt/mcumgr/smp_svr/src/bluetooth.c) 
from the [`smp_svr` sample](https://github.com/zephyrproject-rtos/zephyr/tree/main/samples/subsys/mgmt/mcumgr/smp_svr) for details on that.
:::

To build the [`smp_svr` sample](https://github.com/zephyrproject-rtos/zephyr/tree/main/samples/subsys/mgmt/mcumgr/smp_svr)
for the `stm32f746g_disco` board with `stm32_disco.overlay` devicetree overlay,
configured to use serial transport with *swap-using-scratch* update algorithm,
you would run (replace `~/zephyrproject` with path to your Zephyr workspace):

```sh
    west build \
        -d build \
        -b stm32f746g_disco \
        "~/zephyrproject/zephyr/samples/subsys/mgmt/mcumgr/smp_svr" \
        -- \
            -DDTC_OVERLAY_FILE="stm32_disco.overlay" \
            -DEXTRA_CONF_FILE="overlay-serial.conf" \
            -DCONFIG_MCUBOOT_BOOTLOADER_MODE_SWAP_SCRATCH=y
```

For more information on the `smp_svr` sample, please refer to [Zephyr's documentation](https://docs.zephyrproject.org/latest/samples/subsys/mgmt/mcumgr/smp_svr/README.html#smp-svr).

#### Signing the image

By default MCUboot will only accept images that are properly signed with the same key as the bootloader itself.
Only `BIN` and `HEX` output types can be signed.
The recommended way for managing signing keys is using [MCUboot's image tool](#generating-image-signing-key),
which is shipped together with Zephyr's MCUboot implementation.
When signing an image, you also have to provide an image version, that's embedded in the signed image header.
This is also the value that will be reported by the MCUmgr client as the current running software version back to the [RDFM server](./rdfm_mgmt_server.md).
Image version is specified in `major.minor.revision+build` format.

##### Automatically

Zephyr build system can automatically sign the final image for you.
To enable this functionality, you will have to set:

* `MCUBOOT_SIGNATURE_KEY_FILE`: path to the signing key
* `MCUBOOT_IMGTOOL_SIGN_VERSION`: version of the produced image
before building your application.
Here's a modification of the build command from [building the image](#building-the-image) with those settings applied:

```sh
    west build \
        -d build \
        -b stm32f746g_disco \
        "~/zephyrproject/zephyr/samples/subsys/mgmt/mcumgr/smp_svr" \
        -- \
            -DDTC_OVERLAY_FILE="stm32_disco.overlay" \
            -DEXTRA_CONF_FILE="overlay-serial.conf" \
            -DCONFIG_MCUBOOT_BOOTLOADER_MODE_SWAP_SCRATCH=y \
            -DCONFIG_MCUBOOT_SIGNATURE_KEY_FILE='"key.pem"' \
            -DCONFIG_IMGTOOL_SIGN_VERSION='"1.2.3+4"'
```

##### Manually

You can also sign the produced images yourself using the [image tool](#generating-image-signing-key).
Below is a sample showing how to sign previously built image:

```sh
west sign -d build -t imgtool -- --key <key-file> --version <sign-version>
```

Either way, the signed images will be stored next to their unsigned counterparts. They will have `signed` inserted into the filename (e.g. unsigned `zephyr.bin` will produce `zephyr.signed.bin` signed image).

## Configuring MCUmgr client

### Search locations

The client is configured using `config.json` configuration file.
By default, the client will look for this file in:

- current working directory
- `$HOME/.config/rdfm-mcumgr`
- `/etc/rdfm-mcumgr`

stopping at first configuration file found.
You can override this by specifying path to a different configuration file with `-c/--config` flag:

```sh
rdfm-mcumgr-client --config <path-to-config>
```

All of the non-device specific options can also be overwritten by specifying their flag counterpart.
For a full list you can run:

```sh
rdfm-mcumgr-client --help
```

### Configuration values

- `server` - URL of the RDFM server the client should connect to
- `key_dir` - path (relative or absolute) to the directory where all device keys are stored
- `update_interval` - interval between each update poll to RDFM server (accepts time suffixes 's', 'm', 'h')
- `retries` - (optional) how many times should an update be attempted for a device in case of an error
              (no value or value `0` means no limit)
- `devices` - an array containing configuration for each device the client should handle
    - `name` - display name for device, used only for logging
    - `id` - unique device identifier used when communicating with RDFM server
    - `device_type` - device type reported to RDFM server used to specify compatible artifacts
    - `key` - name of the file containing device private key in PEM format. Key should be stored in `key_dir` directory.
    - `update_interval` - (optional) override global `update_interval` for this device
    - `transport` - specifies the transport type for the device and it's specific options

- `groups` - an array containing configuration for device groups
    - `name` - display name for group, used for logging
    - `id` - unique group identifier used when communicating with RDFM server
    - `type` - type reported to RDFM server to specify compatible artifacts
    - `key` - name of the file containing group private key in PEM format. Key should be stored in `key_dir` directory.
    - `update_interval` - (optional) override global `update_interval` for this group
    - `members` - an array containing configuration for each device that's a member of this group
        - `name` - display name for device, used for logging
        - `device` - name of target image to match from an artifact
        - `transport` - specifies the transport type for the device and its specific options

Transport specific:
- `type` - specific transport type for this device. Currently supported: `ble`, `serial`, `udp`

* BLE transport:
    - `device_index` - controller index to be used for connection (e.g. `hci0` -> `0`)
    - `peer_name` - the name the target BLE device advertises. Should match with `CONFIG_BT_DEVICE_NAME`

* Serial transport:
    - `device` - device name used for communicating with device. OS specific (e.g. `"/dev/ttyUSB0"`, `"/dev/tty.usbserial"`)
    - `baud` - communication speed; must match the baudrate of connected device
    - `mtu` - Maximum Transmission Unit, maximum protocol packet size

* UDP transport:
    - `address`: IPv4 / IPv6 address and port in `IP`:`port` form

### Device groups

The client supports grouping multiple Zephyr MCUboot boards to act as one complete device from management server's perspective.
While each device in a group can be running different Zephyr application,
all devices are synchronized by the MCUmgr client to be running the exact same software version.
Group updates are performed using [zephyr group artifacts](./rdfm_artifact.md#creating-a-zephyr-mcuboot-group-artifact)
which contain update images for each member of the group and metadata on how to match image to device.

During an update, the MCUmgr client matches each image to its target member and tries to apply it.
Group update is considered successful only if **all** members of the group went through the update process without errors.
Otherwise all members are rolled back by the client to the previous version.

### Example configuration

```json
{
  "server": "http://localhost:5000",
  "key_dir": "keys",
  "update_interval": "10s",
  "retries": 3,
  "devices": [
    {
      "name": "zephyr-ble",
      "id": "11:11:11:11:11:11",
      "dev_type": "zeph-ble",
      "update_interval": "15s",
      "key": "ble.key",
      "transport": {
        "type": "ble",
        "device_index": 0,
        "peer_name": "test0"
      }
    },
    {
      "name": "zephyr-serial",
      "id": "22:22:22:22:22:22",
      "dev_type": "zeph-ser",
      "key": "serial.key",
      "transport": {
        "type": "serial",
        "device": "/dev/ttyACM0",
        "baud": 115200,
        "mtu": 128
      }
    }
  ],
  "groups": [
    {
      "name": "group-one",
      "id": "gr1",
      "type": "group1",
      "key": "group1.key",
      "members": [
        {
          "name": "udpl",
          "device": "udp-left",
          "transport": {
            "type": "udp",
            "address": "192.168.1.2:1337"
          }
        },
        {
          "name": "udpr",
          "device": "udp-right",
          "transport": {
            "type": "udp",
            "address": "192.168.1.3:1337"
          }
        },
        {
          "name": "bleh",
          "device": "ble",
          "transport": {
            "type": "ble",
            "device_index": 0,
            "peer_name": "ble_head",
          }
        }
      ]
    }
  ]
}
```

### Device keys

Each device uses its own private key for authentication with `rdfm-server` as described in [device authentication](./server_operation.md#device-authentication).
Each key should be stored under `key_dir` specified in configuration.
If the client doesn't find corresponding device key for configured device, it will attempt to generate one itself.
The resulting key will be saved to the configured location with `0600` permissions.

:::{note}
Device keys are different from the signing key used for signing the bootloader and application images!
:::
