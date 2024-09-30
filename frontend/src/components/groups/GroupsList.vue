<!--
Copyright (c) 2024 Antmicro <www.antmicro.com>

SPDX-License-Identifier: Apache-2.0
-->

<!--
Component wraps functionality for displaying and working with rdfm groups.
-->

<template>
    <Transition>
        <BlurPanel v-if="popupOpen == GroupPopupOpen.AddGroup" @click.self="closeAddGroupPopup">
            <div class="popup">
                <div class="header">
                    <p class="title">Create a new group</p>
                    <p class="description">Configure new devices group and add packages to it</p>
                </div>
                <div class="body">
                    <div class="entry">
                        <p>Name</p>
                        <input type="text" v-model="newGroupData.name" placeholder="New group" />
                    </div>
                    <div class="entry">
                        <p>Description</p>
                        <input
                            type="text"
                            v-model="newGroupData.description"
                            placeholder="Group description"
                        />
                    </div>
                    <div class="entry">
                        <p>Priority</p>
                        <input type="number" v-model="newGroupData.priority" placeholder="10" />
                    </div>

                    <div class="buttons">
                        <button class="action-button gray" @click="closeAddGroupPopup">
                            Cancel
                        </button>
                        <button class="action-button blue white" @click="addGroup">Create</button>
                    </div>
                </div>
            </div>
        </BlurPanel>
    </Transition>

    <RemovePopup
        @click.self="closeRemoveGroupPopup"
        title="Are you absolutely sure?"
        :enabled="popupOpen == GroupPopupOpen.RemoveGroup"
        :description="`This action cannot be undone. It will permanently delete #${groupToRemove} group.`"
        :cancelCallback="closeRemoveGroupPopup"
        :removeCallback="removeGroup"
    />

    <Transition>
        <BlurPanel
            v-if="popupOpen == GroupPopupOpen.ConfigureGroup"
            @click.self="closeConfigureGroupPopup"
        >
            <div class="popup" @click="closeDropdowns">
                <div class="header">
                    <p class="title">Configure the #{{ groupConfiguration.id }} group</p>
                    <p class="description">Configure group packages, devices and priority</p>
                </div>
                <div class="body">
                    <div class="entry">
                        <p>Priority</p>
                        <input
                            type="text"
                            v-model="groupConfiguration.priority"
                            placeholder="Priority"
                        />
                    </div>
                    <div class="entry">
                        <p>Packages</p>
                        <Dropdown
                            @click.stop
                            placeholder="Choose packages"
                            :columns="packageDropdownColumns"
                            :data="packageList"
                            :select="selectPackage"
                            :toggleDropdown="() => toggleDropdown(0)"
                            :dropdownOpen="packageDropdownOpen"
                        />
                    </div>
                    <div class="entry">
                        <p>Devices</p>
                        <Dropdown
                            @click.stop
                            placeholder="Choose devices"
                            :columns="deviceDropdownColumns"
                            :data="deviceList"
                            :select="selectDevice"
                            :toggleDropdown="() => toggleDropdown(1)"
                            :dropdownOpen="deviceDropdownOpen"
                        />
                    </div>

                    <div class="buttons">
                        <button class="action-button gray" @click="closeConfigureGroupPopup">
                            Cancel
                        </button>
                        <button class="action-button blue white" @click="configureGroup">
                            Configure
                        </button>
                    </div>
                </div>
            </div>
        </BlurPanel>
    </Transition>

    <TitleBar
        title="Groups"
        subtitle="manage your groups"
        actionButtonName="Create new group"
        :buttonCallback="openAddGroupPopup"
    />

    <div class="container">
        <p>Overview</p>
        <div class="resources-table-wrapper">
            <table class="resources-table">
                <tbody>
                    <tr class="resources-table-row">
                        <td class="entry">
                            <div class="value">Total groups</div>
                        </td>
                        <td class="entry">
                            <div class="value">{{ groupsCount }}</div>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        <template v-if="groups && groups.length !== 0">
            <p>Groups</p>
            <div class="resources-table-wrapper">
                <div v-for="group in groups" :key="group.id" class="group">
                    <div class="group-row">
                        <div class="entry">
                            <div class="title">ID</div>
                            <div class="value">#{{ group.id }}</div>
                        </div>
                        <div class="entry">
                            <div class="title">Created</div>
                            <div class="value">{{ group.created }}</div>
                        </div>
                        <div class="entry">
                            <div class="title">Name</div>
                            <div class="value">{{ group.metadata['rdfm.group.name'] }}</div>
                        </div>
                        <div class="entry">
                            <div class="title">Description</div>
                            <div class="value">{{ group.metadata['rdfm.group.description'] }}</div>
                        </div>
                        <div class="entry">
                            <div class="title">Policy</div>
                            <div class="value">{{ group.policy }}</div>
                        </div>
                        <div class="entry">
                            <div class="title">Priority</div>
                            <div class="value">{{ group.priority }}</div>
                        </div>
                        <div class="entry right">
                            <div class="button-wrapper">
                                <button
                                    class="action-button gray"
                                    @click="openConfigureGroupPopup(group)"
                                >
                                    Configure
                                </button>
                                <button
                                    class="action-button red"
                                    @click="openRemoveGroupPopup(group.id)"
                                >
                                    Remove
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="group-row">
                        <div class="entry">
                            <div class="title" v-if="group.packages.length == 1">1 Package</div>
                            <div class="title" v-else>{{ group.packages.length }} Packages</div>
                            <div class="values">
                                <div v-for="pckg in group.packages" :key="pckg" class="item">
                                    #{{ pckg }}
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="group-row">
                        <div class="entry">
                            <div class="title" v-if="group.devices.length == 1">1 Device</div>
                            <div class="title" v-else>{{ group.devices.length }} Devices</div>
                            <div class="values">
                                <div v-for="device in group.devices" :key="device" class="item">
                                    #{{ device }} - {{ findDevice(device) }}
                                    <button
                                        class="action-button red small-padding"
                                        @click="patchDevicesRequest(group.id, [], [device])"
                                    >
                                        <Cross></Cross>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </template>
    </div>
</template>

<style scoped>
.container {
    padding: 2em;

    & > p {
        color: var(--gray-1000);
        font-size: 1.5em;
    }

    .group {
        display: flex;
        flex-direction: column;
        min-width: max-content;

        border: 2px solid var(--gray-400);
        border-radius: 5px;
        margin-bottom: 2em;

        & > .group-row {
            display: flex;
            flex-direction: row;
            border-bottom: 2px solid var(--gray-400);

            &:last-child {
                border: none;
            }

            & > .entry {
                padding: 0.5em 1em;

                & > .title {
                    color: var(--gray-900);
                    text-wrap: nowrap;
                }

                & > .value {
                    color: var(--gray-1000);
                    text-wrap: nowrap;
                }

                & > .values {
                    display: flex;
                    flex-direction: row;

                    & > .item {
                        border: 1px solid var(--gray-400);
                        border-radius: 5px;
                        background-color: var(--gray-100);
                        margin: 0.25em 1em;
                        padding: 0.25em 0.5em;
                    }
                }

                &:last-child {
                    flex-grow: 1;
                }

                & > .button-wrapper {
                    display: flex;
                    justify-content: flex-end;
                    gap: 1em;
                }
            }
        }

        color: var(--gray-1000);
    }
}
</style>

<script lang="ts">
import { computed, onMounted, onUnmounted, ref, type Ref, reactive, type Reactive } from 'vue';

import { POLL_INTERVAL, type Group } from '../../common/utils';
import {
    addGroupRequest,
    devicesResources,
    findDevice,
    findPackage,
    groupResources,
    packagesResources,
    patchDevicesRequest,
    removeGroupRequest,
    updatePackagesRequest,
    updatePriorityRequest,
    type GroupConfiguration,
    type InitialGroupConfiguration,
    type NewGroupData,
} from './groups';

import type { Column, DataEntry } from '../Dropdown.vue';

import BlurPanel from '../BlurPanel.vue';
import RemovePopup from '../RemovePopup.vue';
import TitleBar from '../TitleBar.vue';
import Cross from '../icons/Cross.vue';
import Dropdown from '../Dropdown.vue';

export enum GroupPopupOpen {
    AddGroup,
    RemoveGroup,
    ConfigureGroup,
    None,
}

export enum DropDownOpen {
    Packages,
    Devices,
    None,
}

export default {
    components: {
        BlurPanel,
        RemovePopup,
        TitleBar,
        Cross,
        Dropdown,
    },
    setup() {
        const popupOpen = ref(GroupPopupOpen.None);

        // =======================
        // Add group functionality
        // =======================
        const newGroupData: Reactive<NewGroupData> = reactive({
            name: null,
            description: null,
            priority: null,
        });

        const openAddGroupPopup = () => {
            popupOpen.value = GroupPopupOpen.AddGroup;
        };

        const closeAddGroupPopup = () => {
            newGroupData.name = null;
            newGroupData.description = null;
            newGroupData.priority = null;

            popupOpen.value = GroupPopupOpen.None;
        };

        const addGroup = async () => {
            const { success, message } = await addGroupRequest(newGroupData!);
            if (!success) {
                alert(message);
            } else {
                closeAddGroupPopup();
            }
        };
        // =======================
        // Remove group functionality
        // =======================

        const groupToRemove: Ref<number | null> = ref(null);

        const removeGroup = async () => {
            const { success, message } = await removeGroupRequest(groupToRemove.value!);
            if (!success) {
                alert(message);
            } else {
                closeRemoveGroupPopup();
            }
        };

        const openRemoveGroupPopup = async (groupId: number) => {
            groupToRemove.value = groupId;
            popupOpen.value = GroupPopupOpen.RemoveGroup;
        };

        const closeRemoveGroupPopup = () => {
            groupToRemove.value = null;
            popupOpen.value = GroupPopupOpen.None;
        };
        // =======================
        // Configure group functionality
        // =======================
        const groupConfiguration: Reactive<GroupConfiguration> = reactive({
            id: null,
            priority: null,
            devices: null,
            packages: null,
        });

        let initialGroupConfiguration: InitialGroupConfiguration | null = null;

        const openConfigureGroupPopup = async (group: Group) => {
            groupConfiguration.id = group.id;
            groupConfiguration.priority = group.priority;
            groupConfiguration.devices = [...group.devices];
            groupConfiguration.packages = [...group.packages];

            packageList.value = (packagesResources.resources.value ?? []).map((v) => ({
                id: v.id,
                version: v.metadata['rdfm.software.version'],
                type: v.metadata['rdfm.hardware.devtype'],
                selected: group.packages.includes(v.id),
            }));

            deviceList.value = (devicesResources.resources.value ?? []).map((v) => ({
                id: v.id,
                mac_address: v.mac_address,
                name: v.name,
                selected: group.devices.includes(v.id),
            }));

            // Storing a copy of the initial configuration to detect any changes that could occur
            // during group configuration
            initialGroupConfiguration = {
                id: group.id,
                priority: group.priority,
                packages: [...group.packages],
                devices: [...group.devices],
            };

            popupOpen.value = GroupPopupOpen.ConfigureGroup;
        };

        const closeConfigureGroupPopup = () => {
            groupConfiguration.id = null;
            groupConfiguration.priority = null;
            initialGroupConfiguration = null;

            popupOpen.value = GroupPopupOpen.None;
            closeDropdowns();
        };

        const wasGroupModified = (original: Group, initial: InitialGroupConfiguration) => {
            return !(
                original.id === initial.id &&
                original.priority === initial.priority &&
                JSON.stringify(original.packages) === JSON.stringify(initial.packages) &&
                JSON.stringify(original.devices) === JSON.stringify(initial.devices)
            );
        };

        const configureGroup = async () => {
            const groupToModify = groupResources.resources.value!.find(
                (group) => group.id === groupConfiguration.id!,
            );

            if (wasGroupModified(groupToModify!, initialGroupConfiguration!)) {
                alert('Modification detected during configuration! Configuration is aborted.');
                return;
            }

            // Updating priority
            if (groupConfiguration.priority! !== initialGroupConfiguration!.priority) {
                const { success, message } = await updatePriorityRequest(
                    groupConfiguration.id!,
                    groupConfiguration.priority!,
                );
                if (!success) {
                    alert(message);
                    return;
                }
            }

            // Updating devices
            const initialDevices = initialGroupConfiguration!.devices;

            const newDevices = deviceList.value
                .filter(({ selected }) => selected)
                .map(({ id }) => id);

            const removedDevices = initialDevices.filter((device) => !newDevices.includes(device));
            const addedDevices = newDevices.filter((device) => !initialDevices.includes(device));

            if (removedDevices.length > 0 || addedDevices.length > 0) {
                const { success, message } = await patchDevicesRequest(
                    groupConfiguration.id!,
                    addedDevices,
                    removedDevices,
                );
                if (!success) {
                    alert(message);
                    return;
                }
            }

            // Updating packages
            const initialPackages = initialGroupConfiguration!.packages;

            let newPackages = packageList.value
                .filter(({ selected }) => selected)
                .map(({ id }) => id);

            if (JSON.stringify(initialPackages) !== JSON.stringify(newPackages)) {
                const { success, message } = await updatePackagesRequest(
                    groupConfiguration.id!,
                    newPackages,
                );
                if (!success) {
                    alert(message);
                    return;
                }
            }

            closeConfigureGroupPopup();
        };
        // =======================

        let intervalID: undefined | number = undefined;

        const fetchResources = async () => {
            await packagesResources.fetchResources();
            await devicesResources.fetchResources();
            await groupResources.fetchResources();
        };

        const startPolling = () => {
            if (intervalID === undefined) {
                intervalID = setInterval(fetchResources, POLL_INTERVAL);
            }
        };

        const stopPolling = () => {
            if (intervalID !== undefined) {
                clearInterval(intervalID);
            }
        };

        onMounted(async () => {
            await fetchResources();
            startPolling();
        });

        onUnmounted(() => {
            stopPolling();
        });

        const openDropdown = ref(DropDownOpen.None);

        const packageList: Ref<DataEntry[]> = ref([]);
        const packageDropdownOpen = computed(() => openDropdown.value === DropDownOpen.Packages);

        const selectPackage = (i: number) => {
            packageList.value[i].selected = !packageList.value[i].selected;
        };

        const packageDropdownColumns: Column[] = [
            { id: 'id', name: 'ID' },
            { id: 'version', name: 'Version' },
            { id: 'type', name: 'Device type' },
        ];

        const deviceList: Ref<DataEntry[]> = ref([]);
        const deviceDropdownOpen = computed(() => openDropdown.value === DropDownOpen.Devices);

        const selectDevice = (i: number) => {
            deviceList.value[i].selected = !deviceList.value[i].selected;
        };

        const deviceDropdownColumns: Column[] = [
            { id: 'id', name: 'ID' },
            { id: 'name', name: 'Name' },
            { id: 'mac_address', name: 'MAC address' },
        ];

        const closeDropdowns = () => {
            openDropdown.value = DropDownOpen.None;
        };

        const toggleDropdown = (dropdown: DropDownOpen) => {
            openDropdown.value = openDropdown.value === dropdown ? DropDownOpen.None : dropdown;
        };

        const groupsCount = computed(() => groupResources.resources.value?.length ?? 0);

        return {
            openRemoveGroupPopup,
            closeAddGroupPopup,
            addGroup,
            groupsCount,
            removeGroup,
            groups: groupResources.resources,
            newGroupData,
            groupToRemove,
            closeRemoveGroupPopup,
            popupOpen,
            openAddGroupPopup,
            findPackage,
            patchDevicesRequest,
            findDevice,
            openConfigureGroupPopup,
            closeConfigureGroupPopup,
            groupConfiguration,
            configureGroup,
            GroupPopupOpen,
            packageDropdownColumns,
            packageList,
            selectPackage,
            deviceDropdownColumns,
            deviceList,
            selectDevice,
            packageDropdownOpen,
            deviceDropdownOpen,
            closeDropdowns,
            toggleDropdown,
        };
    },
};
</script>
