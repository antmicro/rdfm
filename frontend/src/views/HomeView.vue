<!--
Copyright (c) 2024-2025 Antmicro <www.antmicro.com>

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
            <div
                v-for="tab in SECTIONS"
                class="navbar-item"
                :class="{ active: tab.startsWith(route.name!.toString()) }"
                @click="router.push('/' + tab)"
            >
                {{ tab }}
            </div>
        </div>

        <DevicesList :tag="tag" v-if="tag !== undefined" />
        <DevicesList v-if="route.name === ActiveTab.Devices" />
        <PackagesList v-if="route.name === ActiveTab.Packages" />
        <GroupsList v-if="route.name === ActiveTab.Groups" />
        <Device v-if="route.name === ActiveTab.Device" />
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
    background-color: var(--background-100);
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
        background-color: var(--background-200);
        padding: 0 1.8em;

        > .navbar-item {
            color: var(--gray-800);
            cursor: pointer;
            padding: 0.5em;
            font-size: larger;
            text-transform: capitalize;

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
        padding-bottom: 0em;
        background-color: var(--background-200);

        display: flex;
        justify-content: space-between;
        align-items: center;

        & > #logo {
            height: 4em;
            width: 10em;
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
import { ref, computed, type PropType } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { EventSourcePolyfill } from 'event-source-polyfill';
import {
    fetchWrapper,
    LOGIN_PATH,
    LOGOUT_PATH,
    permissions,
    PERMISSIONS_ENDPOINT,
    adminRoles,
    type Permission,
    DEVICE_PROGRESS_ENDPOINT,
    useNotifications,
} from '../common/utils';

import DevicesList from '../components/devices/DevicesList.vue';
import PackagesList from '../components/packages/PackagesList.vue';
import GroupsList from '../components/groups/GroupsList.vue';
import Logo from '../images/Logo.vue';
import LogoutIcon from '@/images/LogoutIcon.vue';
import Device from '@/components/devices/Device.vue';
import { deviceUpdates, deviceVersions } from '../components/devices/devices';

export enum ActiveTab {
    Device = 'device',
    Devices = 'devices',
    Packages = 'packages',
    Groups = 'groups',
}

export const SECTIONS = [ActiveTab.Devices, ActiveTab.Packages, ActiveTab.Groups];
const notif = useNotifications();

export default {
    props: {
        activeTab: Object as PropType<ActiveTab>,
        tag: {
            type: String,
            required: false,
        },
    },
    components: {
        Logo,
        LogoutIcon,
        DevicesList,
        PackagesList,
        GroupsList,
        Device,
    },
    setup(props) {
        const router = useRouter();
        const route = useRoute();
        const loggedIn = ref(false);
        const accMenuOpen = ref(false);

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
            ...props,
            loggedIn,
            accMenuOpen,
            LOGIN_PATH,
            LOGOUT_PATH,
            SECTIONS,
            userName,
            userRoles,
            ActiveTab,
            router,
            route,
            parsedToken,
        };
    },
    watch: {
        userRoles(newValue) {
            adminRoles.value = newValue.map((role: { name: string }) => role.name);
            fetchWrapper(PERMISSIONS_ENDPOINT, 'GET').then(
                (response) =>
                    (permissions.value = response.data.filter(
                        (p: Permission) => p.user_id == this.parsedToken.sub,
                    )),
            );
        },
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

        const accessToken = localStorage.getItem('access_token');

        const sse = new EventSourcePolyfill(DEVICE_PROGRESS_ENDPOINT, {
            headers: {
                Authorization: `Bearer token=${accessToken}`,
            },
        });

        sse.addEventListener('update', async (event: MessageEvent) => {
            const message = JSON.parse(event.data);

            if (!deviceUpdates.has(message.device) && !deviceVersions.has(message.device)) {
                notif.notifySuccess({
                    headline: `Device ${message.device}`,
                    msg: 'Device update started',
                });
            }
            if (message.version && !deviceVersions.has(message.device)) {
                deviceVersions.set(message.device, message.version);
            }
            if (message.progress) {
                deviceUpdates.set(message.device, message.progress);
            }
            if (deviceUpdates.get(message.device) === 100) {
                notif.notifySuccess({
                    headline: `Device ${message.device}`,
                    msg: 'Device update finished',
                });
                deviceUpdates.delete(message.device);
                deviceVersions.delete(message.device);
            }
        });

        sse.addEventListener('error', (error: Event) => {
            console.error(
                'Connection to event stream failed. Will not be able to show device update progress.',
            );
        });
    },
};
</script>
