<!--
Copyright (c) 2024 Antmicro <www.antmicro.com>

SPDX-License-Identifier: Apache-2.0
-->

<!--
Component wraps functionality for displaying and working with rdfm devices.
-->

<template>
    <div id="devices">
        <TitleBar title="Devices" subtitle="manage your devices" />
        <div id="container">
            <div id="overview">
                <a href="#device-list-overview">Overview</a>
                <a href="#device-list-unregistered" v-if="pendingDevicesCount !== 0"
                    >Unregistered</a
                >
                <a href="#device-list-registered" v-if="registeredDevicesCount !== 0">Registered</a>
            </div>
            <div id="device-list">
                <div id="device-list-overview">
                    <p>Overview</p>
                    <div class="resources-table-wrapper checked">
                        <table class="resources-table">
                            <tbody>
                                <tr class="resources-table-row no-border">
                                    <td class="entry">
                                        <div class="value">Total devices</div>
                                    </td>
                                    <td class="entry">
                                        <div class="value">{{ devicesCount }}</div>
                                    </td>
                                </tr>
                                <tr class="resources-table-row no-border">
                                    <td class="entry">
                                        <div class="value">Unregistered devices</div>
                                    </td>
                                    <td class="entry">
                                        <div class="value">
                                            {{ pendingDevicesCount }}/{{ devicesCount }}
                                        </div>
                                    </td>
                                </tr>
                                <tr class="resources-table-row">
                                    <td class="entry">
                                        <div class="value">Registered devices</div>
                                    </td>
                                    <td class="entry">
                                        <div class="value">
                                            {{ registeredDevicesCount }}/{{ devicesCount }}
                                        </div>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
                <div id="device-list-unregistered" v-if="pendingDevicesCount !== 0">
                    <p>Unregistered</p>
                    <div class="resources-table-wrapper">
                        <table class="resources-table">
                            <tbody>
                                <tr
                                    v-for="device in pendingDevices"
                                    :key="device.mac_address"
                                    class="resources-table-row"
                                >
                                    <td class="entry">
                                        <div class="title">MAC Address</div>
                                        <div class="value">{{ device.mac_address }}</div>
                                    </td>
                                    <td class="entry">
                                        <div class="title">Last appeared</div>
                                        <div class="value">{{ device.last_appeared }}</div>
                                    </td>
                                    <td class="entry">
                                        <div class="title">Device type</div>
                                        <div class="value">
                                            {{ device.metadata['rdfm.hardware.devtype'] }}
                                        </div>
                                    </td>
                                    <td class="entry">
                                        <div class="title">Software version</div>
                                        <div class="value">
                                            {{ device.metadata['rdfm.software.version'] }}
                                        </div>
                                    </td>
                                    <td class="entry">
                                        <div class="title">Public key</div>
                                        <div class="value">
                                            {{ device.public_key.slice(0, 15) }}...
                                        </div>
                                    </td>
                                    <td class="entry">
                                        <button
                                            class="action-button blue"
                                            @click="
                                                registerDevice(
                                                    device.mac_address,
                                                    device.public_key,
                                                )
                                            "
                                        >
                                            Register
                                        </button>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <div id="device-list-registered" v-if="registeredDevicesCount !== 0">
                    <p>Registered</p>
                    <table class="resources-table">
                        <tbody>
                            <tr
                                v-for="device in registeredDevices"
                                :key="device.id"
                                class="resources-table-row"
                            >
                                <td class="entry">
                                    <div class="title">ID</div>
                                    <div class="value">#{{ device.id }}</div>
                                </td>
                                <td class="entry">
                                    <div class="title">Name</div>
                                    <div class="value">{{ device.name }}</div>
                                </td>
                                <td class="entry">
                                    <div class="title">Capabilities</div>
                                    <div class="value">{{ device.capabilities }}</div>
                                </td>
                                <td class="entry">
                                    <div class="title">MAC Address</div>
                                    <div class="value">
                                        {{ device.mac_address }}
                                    </div>
                                </td>
                                <td class="entry">
                                    <div class="title">Software version</div>
                                    <div class="value">
                                        {{ device.metadata['rdfm.software.version'] }}
                                    </div>
                                </td>
                                <td class="entry">
                                    <div class="title">Last Accessed</div>
                                    <div class="value">{{ device.last_access }}</div>
                                </td>
                                <td class="entry">
                                    <div class="title">Groups</div>
                                    <div class="value" v-if="device.groups!.length > 0">
                                        {{ device.groups }}
                                    </div>
                                    <div class="value" v-else>-</div>
                                </td>

                                <!-- Last auxiliary entry to fill up the space -->
                                <td class="entry"></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
#devices {
    p {
        color: var(--gray-1000);
        font-size: 1.5em;
    }

    & > #container {
        display: flex;
        flex-direction: row;
        color: var(--gray-1000);
        padding: 2em;

        & > #overview {
            display: flex;
            flex-direction: column;
            gap: 1em;
            width: 20%;
            margin-right: 20px;

            & > a {
                color: inherit;
                text-decoration: none;
                padding: 10px;
                &:hover {
                    background-color: var(--background-200);
                }
            }
        }

        & > #device-list {
            width: 80%;
        }
    }
}
</style>

<script lang="ts">
import { computed, onMounted, onUnmounted } from 'vue';

import { useNotifications, POLL_INTERVAL } from '../../common/utils';
import TitleBar from '../TitleBar.vue';
import {
    pendingDevicesResources,
    registerDeviceRequest,
    registeredDevicesResources,
} from './devices';

export default {
    components: {
        TitleBar,
    },
    setup() {
        const notifications = useNotifications();

        let intervalID: undefined | number = undefined;

        const registerDevice = async (mac_address: string, public_key: string) => {
            const { success, message } = await registerDeviceRequest(mac_address, public_key);
            if (!success)
                notifications.notifyError({
                    headline: 'Error when registering device:',
                    msg: message || 'Registration of device failed',
                });
        };

        const fetchResources = async () => {
            await registeredDevicesResources.fetchResources();
            await pendingDevicesResources.fetchResources();
        };

        onMounted(async () => {
            await fetchResources();

            if (intervalID === undefined) {
                intervalID = setInterval(fetchResources, POLL_INTERVAL);
            }
        });

        onUnmounted(() => {
            if (intervalID !== undefined) {
                clearInterval(intervalID);
            }
        });

        const pendingDevicesCount = computed(
            () => pendingDevicesResources.resources.value?.length ?? 0,
        );
        const registeredDevicesCount = computed(
            () => registeredDevicesResources.resources.value?.length ?? 0,
        );
        const devicesCount = computed(
            () => pendingDevicesCount.value + registeredDevicesCount.value,
        );

        return {
            pendingDevices: pendingDevicesResources.resources,
            registeredDevices: registeredDevicesResources.resources,
            pendingDevicesCount,
            registeredDevicesCount,
            devicesCount,
            registerDevice,
        };
    },
};
</script>
