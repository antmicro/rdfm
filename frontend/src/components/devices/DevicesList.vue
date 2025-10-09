<!--
Copyright (c) 2024-2025 Antmicro <www.antmicro.com>

SPDX-License-Identifier: Apache-2.0
-->

<!--
Component wraps functionality for displaying and working with rdfm devices.
-->

<template>
    <div id="devices">
        <TitleBar title="Devices" subtitle="manage your devices" />
        <div class="container">
            <div class="resources-list">
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
                                        <div class="value">Registered devices</div>
                                    </td>
                                    <td class="entry">
                                        <div class="value">
                                            {{ registeredDevicesCount }}/{{ devicesCount }}
                                        </div>
                                    </td>
                                </tr>
                                <tr class="resources-table-row">
                                    <td class="entry">
                                        <div class="value">Unregistered devices</div>
                                    </td>
                                    <td class="entry">
                                        <div class="value">
                                            {{ pendingDevicesCount }}/{{ devicesCount }}
                                        </div>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
                <div id="device-list-registered" v-if="registeredDevicesCount !== 0">
                    <p>Registered</p>
                    <div class="device-list">
                        <div
                            v-for="device in registeredDevices"
                            :key="device.id"
                            class="row"
                            @click="() => router.push('/devices/' + device.id)"
                        >
                            <div class="entry">
                                <div class="title">ID</div>
                                <div class="value">#{{ device.id }}</div>
                            </div>
                            <div class="entry">
                                <div class="title">Name</div>
                                <div class="value">{{ device.name }}</div>
                            </div>
                            <div class="entry">
                                <div class="title">Capabilities</div>
                                <div class="value">{{ device.capabilities }}</div>
                            </div>
                            <div class="entry">
                                <div class="title">MAC Address</div>
                                <div class="value">
                                    {{ device.mac_address }}
                                </div>
                            </div>
                            <div class="entry">
                                <div class="title">Software version</div>
                                <div class="value">
                                    {{ device.metadata['rdfm.software.version'] }}
                                </div>
                            </div>
                            <div class="entry">
                                <div class="title">Last Accessed</div>
                                <div class="value">{{ device.last_access }}</div>
                            </div>
                            <div class="entry groups">
                                <div class="title">Groups</div>
                                <div class="value" v-if="!(device.groups!.length > 0)">-</div>
                                <div class="value" v-if="groups && device.groups!.length > 0">
                                    <div
                                        class="group-block"
                                        v-for="group in device.groups!.map((devGroup) =>
                                            groups!.find((g) => g.id == devGroup),
                                        )"
                                    >
                                        <span class="groupid">#{{ group?.id }}</span>
                                        {{
                                            group?.metadata?.['rdfm.group.name'] || 'Unknown group'
                                        }}
                                    </div>
                                </div>
                            </div>
                            <div class="entry">
                                <div class="button-wrapper">
                                    <button
                                        class="action-button red"
                                        v-if="allowedTo('delete', 'device', device.id)"
                                        @click="openRemoveDevicePopup(device.id)"
                                        @click.stop.prevent
                                    >
                                        Remove
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div id="device-list-unregistered" v-if="pendingDevicesCount !== 0">
                    <p>Unregistered</p>
                    <div class="device-list">
                        <div v-for="device in pendingDevices" :key="device.mac_address" class="row">
                            <div class="entry">
                                <div class="title">MAC Address</div>
                                <div class="value">{{ device.mac_address }}</div>
                            </div>
                            <div class="entry">
                                <div class="title">Last appeared</div>
                                <div class="value">{{ device.last_appeared }}</div>
                            </div>
                            <div class="entry">
                                <div class="title">Device type</div>
                                <div class="value">
                                    {{ device.metadata['rdfm.hardware.devtype'] }}
                                </div>
                            </div>
                            <div class="entry">
                                <div class="title">Software version</div>
                                <div class="value">
                                    {{ device.metadata['rdfm.software.version'] }}
                                </div>
                            </div>
                            <div class="entry">
                                <div class="title">Public key</div>
                                <div class="value">{{ device.public_key.slice(0, 15) }}...</div>
                            </div>
                            <div class="entry">
                                <div class="button-wrapper">
                                    <!-- TODO: Check a specific permission/role for registering devices once it's implemented server-side -->
                                    <button
                                        class="action-button blue"
                                        v-if="hasAdminRole(AdminRole.RW)"
                                        @click="
                                            registerDevice(device.mac_address, device.public_key)
                                        "
                                    >
                                        Register
                                    </button>
                                    <button
                                        class="action-button red"
                                        v-if="hasAdminRole(AdminRole.RW)"
                                        @click="
                                            openRemovePendingDevicePopup(
                                                device.mac_address,
                                                device.public_key,
                                            )
                                        "
                                    >
                                        Remove
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <RemovePopup
        @click.self="closeRemoveDevicePopup"
        title="Are you absolutely sure?"
        :enabled="popupOpen == DevicePopupOpen.RemoveDevice"
        :description="`This action cannot be undone. It will permanently delete the device #${deviceToRemove}.`"
        :cancelCallback="closeRemoveDevicePopup"
        :removeCallback="removeDevice"
    />

    <RemovePopup
        @click.self="closeRemoveDevicePopup"
        title="Are you absolutely sure?"
        :enabled="popupOpen == DevicePopupOpen.RemovePendingDevice"
        :description="`This action cannot be undone. It will permanently delete the unregistered device.`"
        :cancelCallback="closeRemoveDevicePopup"
        :removeCallback="removePendingDevice"
    />
</template>

<script lang="ts">
import { computed, onMounted, onUnmounted, ref, type Ref } from 'vue';

import {
    useNotifications,
    POLL_INTERVAL,
    hasAdminRole,
    AdminRole,
    allowedTo,
} from '../../common/utils';
import TitleBar from '../TitleBar.vue';
import RemovePopup from '../RemovePopup.vue';
import {
    filteredDevicesResources,
    groupResources,
    pendingDevicesResources,
    registerDeviceRequest,
    registeredDevicesResources,
    removePendingDeviceRequest,
    removeDeviceRequest,
} from './devices';
import router from '@/router';
import { useRouter } from 'vue-router';

export enum DevicePopupOpen {
    RemoveDevice,
    RemovePendingDevice,
    None,
}

type PendingDevice = {
    mac_address: string;
    public_key: string;
};

export default {
    props: {
        tag: {
            type: String,
            required: false,
        },
    },
    components: {
        TitleBar,
        RemovePopup,
    },
    setup(props) {
        const notifications = useNotifications();
        const router = useRouter();

        let intervalID: undefined | number = undefined;

        const registerDevice = async (mac_address: string, public_key: string) => {
            const { success, message } = await registerDeviceRequest(mac_address, public_key);
            if (!success)
                notifications.notifyError({
                    headline: 'Error when registering device:',
                    msg: message || 'Registration of device failed',
                });
        };

        const removePendingDevice = async () => {
            const { success, message } = await removePendingDeviceRequest(
                pendingDeviceToRemove.value!.mac_address,
                pendingDeviceToRemove.value!.public_key,
            );
            if (!success)
                notifications.notifyError({
                    headline: 'Error when removing device:',
                    msg: message || 'Removal of device failed',
                });
            closeRemoveDevicePopup();
        };

        const removeDevice = async () => {
            const { success, message } = await removeDeviceRequest(deviceToRemove.value!);
            if (!success)
                notifications.notifyError({
                    headline: 'Error when removing device:',
                    msg: message || 'Removal of device failed',
                });
            closeRemoveDevicePopup();
        };

        const devices = props.tag
            ? filteredDevicesResources(props.tag)
            : registeredDevicesResources;

        const fetchResources = async () => {
            await devices.fetchResources();
            await pendingDevicesResources.fetchResources();
            await groupResources.fetchResources();
        };

        onMounted(async () => {
            await fetchResources();

            if (intervalID === undefined) {
                intervalID = setInterval(fetchResources, POLL_INTERVAL);
            }

            if (props.tag && devices.resources.value?.length == 1) {
                router.push('/devices/' + devices.resources.value[0].id);
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
        const registeredDevicesCount = computed(() => devices.resources.value?.length ?? 0);
        const devicesCount = computed(
            () => pendingDevicesCount.value + registeredDevicesCount.value,
        );

        const popupOpen = ref(DevicePopupOpen.None);
        const deviceToRemove: Ref<number | null> = ref(null);
        const pendingDeviceToRemove: Ref<PendingDevice | null> = ref(null);

        const openRemoveDevicePopup = async (id: number) => {
            deviceToRemove.value = id;
            popupOpen.value = DevicePopupOpen.RemoveDevice;
        };

        const openRemovePendingDevicePopup = async (mac_address: string, public_key: string) => {
            pendingDeviceToRemove.value = { mac_address, public_key };
            popupOpen.value = DevicePopupOpen.RemovePendingDevice;
        };

        const closeRemoveDevicePopup = () => {
            popupOpen.value = DevicePopupOpen.None;
        };

        return {
            pendingDevices: pendingDevicesResources.resources,
            registeredDevices: devices.resources,
            groups: groupResources.resources,
            router,
            pendingDevicesCount,
            registeredDevicesCount,
            devicesCount,
            hasAdminRole,
            AdminRole,
            allowedTo,
            registerDevice,
            removePendingDevice,
            removeDevice,
            popupOpen,
            deviceToRemove,
            pendingDeviceToRemove,
            DevicePopupOpen,
            openRemoveDevicePopup,
            closeRemoveDevicePopup,
            openRemovePendingDevicePopup,
        };
    },
};
</script>
