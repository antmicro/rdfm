<template>
    <div id="devices">
        <!-- TODO: Research how are devices created -->
        <!-- <BlurPanel></BlurPanel> -->
        <TitleBar
            title="Devices"
            subtitle="manage your devices"
            actionButtonName="Create new device"
            :buttonCallback="createDevice"
        />
        <div id="container">
            <div id="overview">
                <a href="#device-list-overview">Overview</a>
                <a href="#device-list-unregistered">Unregistered</a>
                <a href="#device-list-registered">Registered</a>
            </div>
            <div id="device-list">
                <div id="device-list-overview">
                    <p>Overview</p>
                    <table cellspacing="0" cellpadding="0" class="resources-table">
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
                    </table>
                </div>
                <div id="device-list-unregistered">
                    <p>Unregistered</p>
                    <table cellspacing="0" cellpadding="0" class="resources-table">
                        <tr
                            v-for="device in pendingDevices"
                            :key="device.id"
                            class="resources-table-row"
                        >
                            <td
                                v-for="[name, value] in Object.entries(device)"
                                class="entry"
                                :key="name"
                            >
                                <div class="title">{{ name }}</div>
                                <div class="value">
                                    <!-- TODO: display it differently -->
                                    <template v-if="name !== 'Public key'"> {{ value }} </template>
                                    <template v-else> {{ value.slice(0, 5) }}... </template>
                                </div>
                            </td>
                            <td class="entry">
                                <button
                                    class="action-button blue"
                                    @click="
                                        registerDevice(device['MAC Address'], device['Public key'])
                                    "
                                >
                                    Register
                                </button>
                            </td>
                        </tr>
                    </table>
                </div>

                <div id="device-list-registered">
                    <p>Registered</p>
                    <table cellspacing="0" cellpadding="0" class="resources-table">
                        <tr
                            v-for="device in registeredDevices"
                            :key="device.id"
                            class="resources-table-row"
                        >
                            <td
                                v-for="[name, value] in Object.entries(device)"
                                class="entry"
                                :key="name"
                            >
                                <div class="title">{{ name }}</div>
                                <div class="value">{{ value }}</div>
                            </td>
                            <!-- Last auxiliary entry to fill up the space -->
                            <td class="entry"></td>
                        </tr>
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
            min-width: 20vw;

            & > a {
                color: inherit;
            }
        }

        & > #device-list {
            width: 80vw;
        }
    }
}
</style>

<script lang="ts">
import { computed, onMounted, onUnmounted } from 'vue';

import {
    PENDING_ENDPOINT,
    DEVICES_ENDPOINT,
    POLL_INTERVAL,
    REGISTER_DEVICE_ENDPOINT,
    resourcesGetter,
} from '../common/utils';
import { type PendingDevice, type RegisteredDevice } from '../common/utils';
import TitleBar from './TitleBar.vue';
// import BlurPanel from './BlurPanel.vue';

export default {
    components: {
        TitleBar,
        // BlurPanel,
    },
    setup() {
        const pendingDevicesResources = resourcesGetter<PendingDevice[]>(PENDING_ENDPOINT);
        const registeredDevicesResources = resourcesGetter<RegisteredDevice[]>(DEVICES_ENDPOINT);
        let intervalID: undefined | number = undefined;

        onMounted(async () => {
            await pendingDevicesResources.fetchResources();
            await registeredDevicesResources.fetchResources();

            if (intervalID === undefined) {
                intervalID = setInterval(async () => {
                    await pendingDevicesResources.fetchResources();
                    await registeredDevicesResources.fetchResources();
                }, POLL_INTERVAL);
            }
        });

        onUnmounted(() => {
            if (intervalID !== undefined) {
                clearInterval(intervalID);
            }
        });

        const registerDevice = async (mac_address: string, public_key: string) => {
            const body = JSON.stringify({
                mac_address,
                public_key,
            });

            const headers = new Headers();
            headers.set('Content-type', 'application/json');
            headers.set('Accept', 'application/json, text/javascript');

            const [status] = await pendingDevicesResources.fetchPOST(
                REGISTER_DEVICE_ENDPOINT,
                headers,
                body,
            );
            if (status) {
                await pendingDevicesResources.fetchResources();
                await registeredDevicesResources.fetchResources();
            } else {
                console.error('Failed to register device');
            }
        };

        const parsedRegisteredDevices = computed(() => {
            const parsedState: Record<string, string>[] = [];
            registeredDevicesResources.resources.value?.forEach((device) => {
                const newEntry: Record<string, string> = {
                    ID: `#${device.id.toString()}`,
                    Name: device.name,
                    Capabilities: JSON.stringify(device.capabilities),
                    'MAC Address': device.metadata['rdfm.hardware.macaddr'],
                    'Last Accessed': device.last_access,
                    Groups: JSON.stringify(device.groups) ?? '[]',
                };
                parsedState.push(newEntry);
            });
            return parsedState;
        });

        const parsedPendingDevices = computed(() => {
            const parsedState: Record<string, string>[] = [];
            pendingDevicesResources.resources.value?.forEach((device) => {
                const newEntry: Record<string, string> = {
                    'MAC Address': device.mac_address,
                    'Last appeared': device.last_appeared,
                    Devtype: device.metadata['rdfm.hardware.devtype'],
                    'Software version': device.metadata['rdfm.software.version'],
                    'Public key': device.public_key,
                };
                parsedState.push(newEntry);
            });
            return parsedState;
        });

        const pendingDevicesCount = computed(() => parsedPendingDevices.value.length);
        const registeredDevicesCount = computed(() => parsedRegisteredDevices.value.length);
        const devicesCount = computed(
            () => pendingDevicesCount.value + registeredDevicesCount.value,
        );

        const createDevice = () => alert('TODO!');

        return {
            createDevice,
            pendingDevicesPollStatus: pendingDevicesResources.pollingStatus,
            registeredDevicesPollStatus: registeredDevicesResources.pollingStatus,
            pendingDevices: parsedPendingDevices,
            registeredDevices: parsedRegisteredDevices,
            pendingDevicesCount,
            registeredDevicesCount,
            devicesCount,
            registerDevice,
        };
    },
};
</script>
