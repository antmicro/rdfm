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
                        <div v-if="validationErrors.get('name')" class="errors">
                            <p>{{ validationErrors.get('name') }}</p>
                        </div>
                    </div>
                    <div class="entry">
                        <p>Description</p>
                        <input
                            type="text"
                            v-model="newGroupData.description"
                            placeholder="Group description"
                        />
                        <div v-if="validationErrors.get('description')" class="errors">
                            <p>{{ validationErrors.get('description') }}</p>
                        </div>
                    </div>
                    <div class="entry">
                        <p>Priority</p>
                        <input type="number" v-model="newGroupData.priority" placeholder="10" />
                        <div v-if="validationErrors.get('priority')" class="errors">
                            <p>{{ validationErrors.get('priority') }}</p>
                        </div>
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
                            :toggleDropdown="() => toggleDropdown(DropDownOpen.Packages)"
                            :dropdownOpen="packageDropdownOpen"
                        />
                    </div>
                    <div v-if="groupConfiguration.policy" class="entry policy-entry">
                        <p>Update policy</p>
                        <div class="policy-type" v-if="availablePolicies.length >= 1">
                            <SimpleDropdown
                                :initial="groupConfiguration.policy"
                                :options="availablePolicies"
                                :select="
                                    (val: string) => {
                                        groupConfiguration.policy = val;
                                    }
                                "
                            />
                            <p v-if="unapplicablePolicyWarning" class="warning">
                                The selected update policy will not affect any device in this group
                            </p>
                        </div>
                    </div>

                    <div class="entry">
                        <p>Devices</p>
                        <Dropdown
                            @click.stop
                            placeholder="Choose devices"
                            :columns="deviceDropdownColumns"
                            :data="deviceList"
                            :select="selectDevice"
                            :toggleDropdown="() => toggleDropdown(DropDownOpen.Devices)"
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
        :buttonCallback="hasAdminRole(AdminRole.RW) ? openAddGroupPopup : undefined"
    />

    <div class="container">
        <p>Overview</p>
        <div class="resources-table-wrapper checked">
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
                                    v-if="allowedTo('update', 'group', group.id)"
                                    @click="openConfigureGroupPopup(group)"
                                >
                                    Configure
                                </button>
                                <button
                                    class="action-button red"
                                    v-if="allowedTo('delete', 'group', group.id)"
                                    @click="openRemoveGroupPopup(group.id)"
                                >
                                    Remove
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="group-row single-item">
                        <div class="entry">
                            <div class="title" v-if="group.packages.length == 1">Package</div>
                            <div class="title" v-else>
                                Packages <span class="count">{{ group.packages.length }}</span>
                            </div>
                            <div class="values">
                                <div v-for="pckg in group.packages" :key="pckg" class="item">
                                    <div class="item-layout">
                                        <p title="Package version">
                                            {{
                                                findPackage(pckg)?.metadata[
                                                    'rdfm.software.version'
                                                ] || ' - '
                                            }}
                                        </p>
                                        <p title="Device type">
                                            {{
                                                findPackage(pckg)?.metadata[
                                                    'rdfm.hardware.devtype'
                                                ] || ' - '
                                            }}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="group-row single-item">
                        <div class="entry">
                            <div class="title" v-if="group.devices.length == 1">Device</div>
                            <div class="title" v-else>
                                Devices <span class="count">{{ group.devices.length }}</span>
                            </div>
                            <div class="values">
                                <div
                                    v-for="device in group.devices.map((d) => ({
                                        id: d,
                                        ...findDevice(d),
                                    }))"
                                    :key="device.id"
                                    class="item"
                                >
                                    <div
                                        class="item-layout"
                                        :class="{ grid: allowedTo('update', 'group', group.id) }"
                                    >
                                        <div>
                                            <p title="MAC address">
                                                {{ device.mac_address || ' - ' }}
                                            </p>
                                            <p title="Device type">
                                                {{
                                                    device.metadata?.['rdfm.hardware.devtype'] ||
                                                    ' - '
                                                }}
                                            </p>
                                        </div>
                                        <div>
                                            <button
                                                style="margin: 10px"
                                                class="action-button red small-padding"
                                                v-if="allowedTo('update', 'group', group.id)"
                                                @click="
                                                    patchDevicesRequest(group.id, [], [device.id])
                                                "
                                            >
                                                <Cross></Cross>
                                            </button>
                                        </div>
                                    </div>
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
.warning {
    color: yellow;
    font-size: 0.8em;
    margin-top: 5px;
}

.container {
    padding: 2em;
    padding-top: 0em;

    & > p {
        color: var(--gray-1000);
        font-size: 1.5em;
    }

    .group {
        background: var(--background-200);

        display: flex;
        flex-direction: column;

        border: 2px solid var(--gray-400);
        border-radius: 5px;
        margin-bottom: 2em;

        & > .group-row {
            position: relative;
            display: grid;
            grid-template-columns: 80px repeat(5, auto) 220px;
            border-bottom: 2px solid var(--gray-400);
            padding: 12px;

            &:last-child {
                border: none;
            }

            &.single-item {
                display: block;
            }

            @media only screen and (max-width: 1000px) {
                & {
                    display: block;
                }

                .entry {
                    display: block !important;
                }

                .button-wrapper {
                    position: absolute;
                    top: 10px;
                    right: 10px;
                }
            }

            & > .entry {
                padding: 0.5em 1em;
                display: inline-block;

                & > .title {
                    color: var(--gray-900);
                    text-wrap: nowrap;

                    .count {
                        margin-left: 5px;
                        padding-left: 15px;
                        padding-right: 15px;
                        border-radius: 30px;
                        color: white;
                        background-color: var(--gray-100);
                    }
                }

                & > .value {
                    color: var(--gray-1000);
                    word-break: break-word;
                }

                & > .values {
                    margin-top: 10px;

                    & > .item {
                        border: 1px solid var(--gray-400);
                        border-radius: 5px;
                        background-color: var(--gray-100);
                        margin: 0.25em;
                        padding: 0.25em 0.5em;
                        display: inline-block;
                        max-width: 100%;

                        .item-layout.grid {
                            display: grid;
                            grid-template-columns: auto 35px;
                        }

                        .item-layout {
                            font-size: large;
                            margin-left: 2px;
                            word-break: break-word;

                            & > div {
                                align-content: center;
                            }

                            p {
                                line-height: 1.25em;
                                margin: 0px;
                                text-align: left;
                                font-family: monospace;
                            }

                            p:nth-child(2) {
                                color: var(--gray-700);
                            }
                        }
                    }
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
import {
    POLL_INTERVAL,
    useNotifications,
    allowedTo,
    type Group,
    type Package,
    type RegisteredDevice,
    hasAdminRole,
    AdminRole,
} from '../../common/utils';
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
    updatePolicyRequest,
    updatePriorityRequest,
    type GroupConfiguration,
    type InitialGroupConfiguration,
    type NewGroupData,
    type PolicyType,
} from './groups';

import type { Column, DataEntry } from '../Dropdown.vue';

import BlurPanel from '../BlurPanel.vue';
import RemovePopup from '../RemovePopup.vue';
import TitleBar from '../TitleBar.vue';
import Cross from '../icons/Cross.vue';
import Dropdown from '../Dropdown.vue';
import SimpleDropdown from '../SimpleDropdown.vue';

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
        SimpleDropdown,
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

        const validationErrors: Reactive<Map<string, string>> = reactive(new Map());

        const notifications = useNotifications();

        const openAddGroupPopup = () => {
            popupOpen.value = GroupPopupOpen.AddGroup;
            validationErrors.clear();
        };

        const closeAddGroupPopup = () => {
            newGroupData.name = null;
            newGroupData.description = null;
            newGroupData.priority = null;

            popupOpen.value = GroupPopupOpen.None;
        };

        const addGroup = async () => {
            validationErrors.clear();

            const { success, message, errors } = await addGroupRequest(newGroupData!);

            if (errors) {
                for (let [field, error] of errors) {
                    validationErrors.set(field, error);
                }
            }

            if (!success) {
                notifications.notifyError({
                    headline: 'Error when adding group:',
                    msg: message || 'Adding group failed',
                });
            } else {
                notifications.notifySuccess({ headline: `Group ${newGroupData.name} was added` });
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
                notifications.notifyError({
                    headline: 'Error when removing group:',
                    msg: message || 'Removing group failed',
                });
            } else {
                notifications.notifySuccess({ headline: 'Group was removed' });
            }
            closeRemoveGroupPopup();
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
            policy: null,
            devices: null,
            packages: null,
        });

        let initialGroupConfiguration: InitialGroupConfiguration | null = null;

        /**
         * Packages selected in the group configuration. Might be different than the group' packages if there are unsubmitted changes.
         */
        const selectedPackages = computed(
            () =>
                (packageList.value
                    .filter(({ selected }) => selected)
                    ?.map(({ id }) => packagesResources.resources.value?.find((p) => p.id == id))
                    .filter(Boolean) as Package[]) || [],
        );

        /**
         * Devices selected in the group configuration. Might be different than the group's devices if there are unsubmitted changes.
         */
        const selectedDevices = computed(
            () =>
                (deviceList.value
                    .filter(({ selected }) => selected)
                    ?.map(({ id }) => devicesResources.resources.value?.find((d) => d.id == id))
                    .filter(Boolean) as RegisteredDevice[]) || [],
        );

        /**
         * Warn the user if the current policy has no effect on the selected devices.
         */
        const unapplicablePolicyWarning = computed(() => {
            const policyArg = groupConfiguration.policy?.split(',')[1];

            if (selectedDevices.value.length == 0) return false;
            if (!policyArg) return false;

            const matchingPackages = selectedPackages.value.filter(
                (p) => p.metadata['rdfm.software.version'] == policyArg,
            );

            return selectedDevices.value.every((d) =>
                matchingPackages.every(
                    (p) =>
                        p.metadata['rdfm.hardware.devtype'] != d.metadata['rdfm.hardware.devtype'],
                ),
            );
        });

        const availablePolicies = computed(() => {
            const availableVersions = selectedPackages.value
                .map((p) => p.metadata['rdfm.software.version'])
                .sort((p1, p2) => p1.localeCompare(p2));
            return [
                { id: 'no_update,', display: 'No Update' },
                ...[...new Set(availableVersions)].map((version) => ({
                    id: `exact_match,${version}`,
                    display: `Match version ${version}`,
                })),
            ];
        });

        const openConfigureGroupPopup = async (group: Group) => {
            groupConfiguration.id = group.id;
            groupConfiguration.priority = group.priority;
            groupConfiguration.devices = [...group.devices];
            groupConfiguration.packages = [...group.packages];
            groupConfiguration.policy = group.policy;

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
                policy: group.policy,
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
                original.policy === initial.policy &&
                JSON.stringify(original.packages) === JSON.stringify(initial.packages) &&
                JSON.stringify(original.devices) === JSON.stringify(initial.devices)
            );
        };

        const configureGroup = async () => {
            var requestWasMade = false;

            const groupToModify = groupResources.resources.value!.find(
                (group) => group.id === groupConfiguration.id!,
            );

            if (wasGroupModified(groupToModify!, initialGroupConfiguration!)) {
                notifications.notifyError({
                    headline:
                        'Modification detected during configuration! Configuration is aborted.',
                });
                return;
            }

            // Updating priority
            if (groupConfiguration.priority! !== initialGroupConfiguration!.priority) {
                requestWasMade = true;
                const { success, message } = await updatePriorityRequest(
                    groupConfiguration.id!,
                    groupConfiguration.priority!,
                );
                if (!success) {
                    notifications.notifyError({
                        headline: 'Error when updating group priority:',
                        msg: message || 'Updating group priority failed',
                    });
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
                requestWasMade = true;
                const { success, message } = await patchDevicesRequest(
                    groupConfiguration.id!,
                    addedDevices,
                    removedDevices,
                );
                if (!success) {
                    notifications.notifyError({
                        headline: 'Error when updating group devices:',
                        msg: message || 'Updating group devices failed',
                    });
                    return;
                }
            }

            // Updating packages
            const initialPackages = initialGroupConfiguration!.packages;

            let newPackages = packageList.value
                .filter(({ selected }) => selected)
                .map(({ id }) => id);

            if (JSON.stringify(initialPackages) !== JSON.stringify(newPackages)) {
                requestWasMade = true;
                const { success, message } = await updatePackagesRequest(
                    groupConfiguration.id!,
                    newPackages,
                );
                if (!success) {
                    notifications.notifyError({
                        headline: 'Error when updating group packages:',
                        msg: message || 'Updating group packages failed',
                    });
                    return;
                }
            }

            if (
                JSON.stringify(groupConfiguration.policy) !=
                JSON.stringify(initialGroupConfiguration!.policy)
            ) {
                if (!groupConfiguration.policy) {
                    notifications.notifyError({
                        headline: 'Error when updating group policy:',
                        msg: 'Policy is a required field',
                    });
                    return false;
                }

                const { success, message } = await updatePolicyRequest(
                    groupConfiguration.id!,
                    groupConfiguration.policy,
                );
                if (!success) {
                    notifications.notifyError({
                        headline: 'Error when updating group update policy',
                        msg: message || 'Updating group update policy failed',
                    });
                    return;
                }
            }

            if (requestWasMade)
                notifications.notifySuccess({ headline: 'Group configuration was updated' });

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
            DropDownOpen,
            openDropdown,
            openRemoveGroupPopup,
            closeAddGroupPopup,
            addGroup,
            groupsCount,
            removeGroup,
            groups: groupResources.resources,
            newGroupData,
            validationErrors,
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
            availablePolicies,
            unapplicablePolicyWarning,
            hasAdminRole,
            AdminRole,
            allowedTo,
        };
    },
};
</script>
