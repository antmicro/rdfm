<!--
Copyright (c) 2024 Antmicro <www.antmicro.com>

SPDX-License-Identifier: Apache-2.0
-->

<template>
    <div
        v-if="loggedIn"
        id="main"
        @click="(e: MouseEvent) => (accMenuOpen = $refs.menu.contains(e.target as HTMLElement))"
    >
        <div id="logobar">
            <Logo id="logo" />

            <div id="settings">
                <a v-if="!loggedIn" class="action-button gray" :href="LOGIN_PATH"> Login </a>

                <div style="position: relative" ref="menu">
                    <img
                        src="../../public/assets/person.png"
                        @click="() => (accMenuOpen = true)"
                        style="cursor: pointer; height: 40px; border-radius: 50%"
                    />

                    <div :style="{ display: accMenuOpen ? 'grid' : 'none' }" class="menu">
                        <div class="menu-section-header">Account</div>
                        <div class="menu-row username">
                            <span>username:</span>
                            <span style="text-align: end">{{ userName }}</span>
                        </div>
                        <a :href="LOGOUT_PATH" class="menu-row">
                            Logout
                            <LogoutIcon style="float: right" />
                        </a>
                        <div class="menu-section-header">Roles</div>
                        <div
                            v-for="role in userRoles"
                            :key="role"
                            class="tag"
                            :style="{ border: '1px solid' + role.colour, color: role.colour }"
                        >
                            {{ role.name }}
                        </div>
                    </div>
                </div>
            </div>
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
@keyframes animate-fade {
    0% {
        max-height: 0px;
    }
    100% {
        max-height: 700px;
    }
}

#main {
    background-color: var(--background-200);
    min-height: 100vh;

    .menu {
        position: absolute;
        right: 0px;
        top: 50px;

        background-color: var(--background-200);
        border: 1px solid var(--gray-400);
        border-radius: 10px;
        grid-template-rows: auto;
        grid-template-columns: auto;
        width: fit-content;
        min-width: 260px;

        overflow: hidden;

        animation-duration: 0.5s;
        animation-name: animate-fade;

        .menu-row.username {
            display: grid;
            grid-template-columns: auto auto;
            gap: 10px;
            text-wrap: nowrap;
        }

        .menu-row {
            padding: 10px;
            display: block;
        }

        .tag {
            display: block;
            padding: 0px;
            padding-left: 10px;
            padding-right: 10px;
            margin: 5px;
            margin-left: 10px;
            text-align: center;
            line-height: 2em;
            filter: brightness(130%);
            border-radius: 20px;
        }

        a.menu-row {
            cursor: pointer;
            text-decoration: none;
            color: white;
            &:hover {
                background-color: var(--gray-200);
            }
        }

        .menu-section-header {
            background-color: var(--gray-100);
            padding: 10px;
        }
    }

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

        display: flex;
        justify-content: space-between;
        align-items: center;

        & > #logo {
            height: 3em;
        }

        & > #settings {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 2em;
        }
    }
}
</style>

<script lang="ts">
import { ref, computed } from 'vue';
import { LOGIN_PATH, LOGOUT_PATH } from '../common/utils';

import DevicesList from '../components/devices/DevicesList.vue';
import PackagesList from '../components/packages/PackagesList.vue';
import GroupsList from '../components/groups/GroupsList.vue';
import Logo from '../images/Logo.vue';
import LogoutIcon from '@/images/LogoutIcon.vue';

const enum ActiveTab {
    Devices,
    Packages,
    Groups,
}

export default {
    components: {
        Logo,
        LogoutIcon,
        DevicesList,
        PackagesList,
        GroupsList,
    },
    setup() {
        const activeTab = ref(ActiveTab.Groups);
        const loggedIn = ref(false);
        const accMenuOpen = ref(false);

        const navbarItemClasses = (tabName: number) => {
            return {
                active: activeTab.value === tabName,
            };
        };

        const parseJWT = (token: string) => {
            const binaryString = atob(token.split('.')[1]);
            return JSON.parse(binaryString);
        };

        const parsedToken = computed(() => {
            if (loggedIn.value) {
                const accessToken = localStorage.getItem('access_token');
                if (accessToken !== null) {
                    return parseJWT(accessToken);
                }
            }
            return undefined;
        });

        const userName = computed(() => {
            if (loggedIn.value && parsedToken.value !== undefined) {
                return parsedToken.value['preferred_username'];
            }
            return undefined;
        });

        const stringToColour = (str: string) => {
            let hash = 0;
            const a = 2;
            const b = 3;
            const c = 3;
            const max = 0xffffff;
            for (let i = 0; i < str.length; i++) {
                hash = (a * hash + str.charCodeAt(i) * b + c) % max;
            }

            return '#' + hash.toString(16).padStart(6, '0');
        };

        const userRoles = computed(() => {
            if (loggedIn.value && parsedToken.value !== undefined) {
                return parsedToken.value['realm_access']['roles']
                    .filter((role: string) => role.startsWith('rdfm'))
                    .sort()
                    .map((role: string) => ({ name: role, colour: stringToColour(role) }));
            }
            return undefined;
        });

        return {
            activeTab,
            navbarItemClasses,
            loggedIn,
            accMenuOpen,
            LOGIN_PATH,
            LOGOUT_PATH,
            userName,
            userRoles,
        };
    },
    watch: {
        loggedIn(newValue: boolean) {
            if (!newValue) {
                window.location.href = LOGIN_PATH;
            }
        },
    },
    mounted() {
        if (localStorage.getItem('access_token') !== null) {
            this.loggedIn = true;
        } else {
            window.location.href = LOGIN_PATH;
        }
    },
};
</script>
