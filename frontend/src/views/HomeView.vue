<!--
Copyright (c) 2024 Antmicro <www.antmicro.com>

SPDX-License-Identifier: Apache-2.0
-->

<template>
    <div id="main">
        <div id="logobar">
            <img src="../images/rdfm-logo.svg" alt="logo" id="logo" />
        </div>

        <!-- Navbar for navigation between views -->
        <div id="navbar">
            <div class="navbar-item" :class="navbarItemClasses(0)" @click="activeTab = 0">
                Devices
            </div>
            <div class="navbar-item" :class="navbarItemClasses(1)" @click="activeTab = 1">
                Packages
            </div>
            <div class="navbar-item" :class="navbarItemClasses(2)" @click="activeTab = 2">
                Groups
            </div>
        </div>

        <DevicesList v-if="activeTab === 0" />
        <PackagesList v-if="activeTab === 1" />
        <GroupsList v-if="activeTab === 2" />
    </div>
</template>

<style scoped>
#main {
    background-color: var(--background-200);
    height: 100%;

    & > #navbar {
        display: flex;
        justify-content: left;
        gap: 0.5em;
        padding: 0 3em;

        > .navbar-item {
            color: var(--gray-800);
            cursor: pointer;
            padding: 0.5em;

            &.active {
                color: var(--gray-1000);
                border-bottom: 1px solid var(--gray-1000);
            }

            &:hover {
                color: var(--gray-900);
                border-bottom: 1px solid var(--gray-900);
            }
        }
    }

    & > #logobar {
        color: white;
        padding: 2em;

        > #logo {
            height: 3em;
        }
    }
}
</style>

<script lang="ts">
import { ref } from 'vue';

import DevicesList from '../components/devices/DevicesList.vue';
import PackagesList from '../components/packages/PackagesList.vue';
import GroupsList from '../components/groups/GroupsList.vue';

const enum ActiveTab {
    Devices,
    Packages,
    Groups,
}

export default {
    components: {
        DevicesList,
        PackagesList,
        GroupsList,
    },
    setup() {
        const activeTab = ref(ActiveTab.Groups);

        const navbarItemClasses = (tabName: number) => {
            return {
                active: activeTab.value === tabName,
            };
        };

        return { activeTab, navbarItemClasses };
    },
};
</script>
