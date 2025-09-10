<!--
Copyright (c) 2024-2025 Antmicro <www.antmicro.com>

SPDX-License-Identifier: Apache-2.0
-->

<!--
Component wraps functionality for displaying and working with a single rdfm device.
-->

<template>
    <div v-if="devicesLoaded">
        <TitleBar v-if="device" :title="'Device ' + device.mac_address" :subtitle="device.name" />
        <TitleBar
            v-if="!device"
            :title="`Device with ${pattern} '${id}' was not found`"
            :subtitle="''"
        />

        <div class="actions-container" v-if="actions.length > 0">
            <button
                v-on:click="() => runAction(action.action_id)"
                class="action"
                :class="{ running: action.running }"
                v-for="action in actions"
            >
                <div class="name">{{ action.action_name }}</div>
                <div class="description three-lines">{{ action.description }}</div>
                <div class="run">
                    <svg
                        class="if-not-running"
                        width="30"
                        height="31"
                        viewBox="0 0 20 21"
                        fill="none"
                        xmlns="http://www.w3.org/2000/svg"
                    >
                        <path d="M6 16V5L14.5 10.5L6 16Z" fill="#E8EAED" />
                    </svg>

                    <svg
                        class="if-running rotating"
                        width="30"
                        height="31"
                        viewBox="0 0 20 21"
                        fill="none"
                        xmlns="http://www.w3.org/2000/svg"
                    >
                        <path
                            d="M10 19C8.90667 19 7.87333 18.79 6.9 18.37C5.92667 17.95 5.07667 17.3767 4.35 16.65C3.62333 15.9233 3.05 15.0733 2.63 14.1C2.21 13.1267 2 12.0933 2 11C2 9.89333 2.20986 8.85667 2.62958 7.89C3.04917 6.92333 3.62201 6.07667 4.34813 5.35C5.07424 4.62333 5.92354 4.05 6.89604 3.63C7.86868 3.21 8.90118 3 9.99354 3C10.2201 3 10.4028 3.06944 10.5417 3.20833C10.6806 3.34722 10.75 3.52438 10.75 3.73979C10.75 3.95521 10.6806 4.13576 10.5417 4.28146C10.4028 4.42715 10.2222 4.5 10 4.5C8.19903 4.5 6.66542 5.12847 5.39917 6.38542C4.13306 7.64236 3.5 9.17708 3.5 10.9896C3.5 12.8021 4.13306 14.3403 5.39917 15.6042C6.66542 16.8681 8.19903 17.5 10 17.5C11.8194 17.5 13.3576 16.8669 14.6146 15.6008C15.8715 14.3346 16.5 12.801 16.5 11C16.5 10.7778 16.5728 10.5972 16.7185 10.4583C16.8642 10.3194 17.0448 10.25 17.2602 10.25C17.4756 10.25 17.6528 10.3194 17.7917 10.4583C17.9306 10.5972 18 10.7799 18 11.0065C18 12.0988 17.79 13.1313 17.37 14.104C16.95 15.0765 16.3767 15.9258 15.65 16.6519C14.9233 17.378 14.0767 17.9508 13.11 18.3704C12.1433 18.7901 11.1067 19 10 19Z"
                            fill="#67A5FF"
                        />
                    </svg>
                </div>
            </button>
        </div>

        <template v-if="device?.capabilities.shell">
            <div :class="['terminal-container', { fullscreen: isFullscreen }]">
                <button :class="['action-button gray', { 'tab-active': isTerminalOpened }]">
                    <div @click="toggleTerminal">
                        {{ terminalButton }}
                    </div>
                    <div @click="terminalFullscreen" v-if="isTerminalOpened">
                        <Expand v-if="!isFullscreen" />
                        <Collapse v-if="isFullscreen" />
                    </div>
                </button>
                <div
                    :class="['terminal-wrapper', { fullscreen: isFullscreen }]"
                    v-if="isTerminalOpened"
                >
                    <Terminal class="terminal" :device="device?.mac_address" />
                </div>
            </div>
        </template>

        <div class="device-container" v-if="device">
            <div class="block">
                <p class="title">MAC Address</p>
                <pre class="small"><code>{{ device.mac_address }}</code></pre>
            </div>
            <div class="block">
                <p class="title">Device Type</p>
                <pre class="small"><code>{{ device.metadata['rdfm.hardware.devtype'] }}</code></pre>
            </div>
            <div class="block">
                <p class="title">Software Version</p>
                <pre class="small"><code>{{ device.metadata['rdfm.software.version'] }}</code></pre>
            </div>
            <div class="block">
                <p class="title">Groups</p>
                <p class="value">
                    <span
                        class="group-block"
                        v-if="(device.groups || []).length > 0"
                        v-for="group in groups"
                        :title="group.metadata['rdfm.group.description']"
                    >
                        <span class="groupid">#{{ group.id }}</span>
                        {{ group.metadata['rdfm.group.name'] }}
                    </span>
                    <span v-if="(device.groups || []).length == 0"
                        >This device is not assigned to any group</span
                    >
                </p>
            </div>
            <div class="block">
                <p class="title">Last Access</p>
                <p class="value">{{ device.last_access }}</p>
            </div>
            <div class="block">
                <p class="title">capabilities</p>
                <pre class="large"><code >{{ device.capabilities }}</code></pre>
            </div>
            <div class="block">
                <p class="title">Metadata</p>
                <pre><code >{{ device.metadata }}</code></pre>
            </div>
        </div>
    </div>
</template>

<style scoped>
@-webkit-keyframes rotating {
    from {
        -webkit-transform: rotate(360deg);
    }
    to {
        -webkit-transform: rotate(0deg);
    }
}

.rotating {
    -webkit-animation: rotating 2s linear infinite;
}

.three-lines {
    display: block;
    display: -webkit-box;
    -webkit-line-clamp: 3; /* max line number */
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
}

.actions-container {
    margin: 30px;

    display: grid;
    gap: 20px;
    grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
    grid-template-rows: repeat(auto-fill, 130px);

    button.action {
        all: unset;
        cursor: pointer;

        border: 1px solid #2e2e2e;
        background-color: #0a0a0a;
        border-radius: 8px;
        gap: 10px;

        padding: 15px;
        display: grid;
        grid-template-columns: auto 50px;
        grid-template-rows: min-content auto;
        height: 100px;

        &:hover {
            background-color: var(--gray-400);
            transition-duration: 500ms;
        }

        .description {
            max-height: 70px;
            color: #a1a1a1;
        }

        .run {
            grid-area: 1 / 2 / 3 / 2;
            align-content: center;
            justify-self: center;
        }

        &.running {
            cursor: default;
            pointer-events: none;
            opacity: 70%;
        }

        &.running .if-not-running {
            display: none;
        }

        .if-running {
            display: none;
        }

        &.running .if-running {
            display: block;
        }
    }
}

.terminal-container {
    margin: 2em;
    transition: transform 1s;
    display: flex;
    flex-direction: column;

    button.tab-active {
        display: flex;
        flex-direction: row;
        column-gap: 10px;

        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        border-bottom-left-radius: 0;
        border-bottom-right-radius: 0;

        margin-bottom: -2px;
    }
}

.terminal-container.fullscreen {
    position: fixed;
    top: 0;
    left: 0;
    margin: 0;
    height: 100vh;
    width: 100%;

    background: var(--background-200);
    z-index: 9999;
}

.terminal-wrapper {
    position: relative;
    height: 900px;
    width: 100%;
    border: 2px solid var(--gray-400);
    border-radius: 5px;
}

.terminal-wrapper.fullscreen {
    flex: 1;
}

.device-container {
    background-color: var(--background-200);

    border: 2px solid var(--gray-400);
    border-radius: 5px;

    margin: 2em;
    padding: 12px;

    .block {
        padding: 10px;
        border-bottom: 2px solid var(--gray-400);
        &:last-child {
            border-bottom: none;
        }

        pre {
            border: 1px solid var(--gray-400);
            border-radius: 5px;
            padding: 10px;
        }

        pre.small {
            width: fit-content;
            max-width: 95%;
        }

        pre,
        code {
            font-family: monospace;
            font-size: 13px;
            background-color: var(--background-100);
            white-space: pre-wrap;
            word-break: break-word;
        }

        p.title,
        p.value {
            margin: 5px;
            word-break: break-word;
        }

        p.title {
            text-transform: capitalize;
            padding: 0px;
            color: var(--gray-900);
            text-wrap: nowrap;
        }
    }
}
</style>

<script lang="ts">
import { computed, effect, ref, watch } from 'vue';

import {
    POLL_INTERVAL,
    useNotifications,
    type Group,
    type RegisteredDevice,
} from '../../common/utils';
import TitleBar from '../TitleBar.vue';
import Terminal from '../Terminal.vue';
import Expand from '../icons/Expand.vue';
import Collapse from '../icons/Collapse.vue';
import {
    registeredDevicesResources,
    groupResources,
    getDeviceActions,
    execAction,
    type Action,
} from './devices';
import { useRoute, useRouter } from 'vue-router';
import { ActiveTab } from '@/views/HomeView.vue';

const MAC_ADDR_REGEX = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/;

const notif = useNotifications();

export default {
    components: {
        TitleBar,
        Terminal,
        Expand,
        Collapse,
    },
    unmounted() {
        if (this.interval !== null) clearInterval(this.interval);
    },
    setup() {
        const route = useRoute();
        const router = useRouter();
        const notify = useNotifications();
        const interval = ref<number | null>(null);

        groupResources.fetchResources();
        registeredDevicesResources.fetchResources();
        interval.value = setInterval(
            () => registeredDevicesResources.fetchResources(),
            POLL_INTERVAL,
        );

        // Parse the route and find the relavant device. The id can be one of:
        //   * MAC address
        //   * URL-encoded device name
        //   * Device id from the RDFM Management Server
        // If there are 2 matches then the order above applies (e.g. MAC Address is prioritized over device name)
        const routeId = route.params.id.toString();
        const device = ref<RegisteredDevice>();
        const groups = ref<Group[]>();
        const pattern = ref<string>();
        const stop = watch(
            () => registeredDevicesResources.resources.value,
            async () => {
                if (!registeredDevicesResources.resources.value) return;
                if (device.value) return;

                let foundDevice: RegisteredDevice | undefined;
                let foundPattern;

                if (routeId.match(MAC_ADDR_REGEX)) {
                    foundDevice = registeredDevicesResources.resources.value.find(
                        (d) => d.mac_address == routeId,
                    );
                    foundPattern = 'MAC address';
                } else {
                    foundDevice = registeredDevicesResources.resources.value.find(
                        (d) => d.name == decodeURIComponent(routeId),
                    );
                    foundPattern = 'name';
                }

                if (!foundDevice && /^\d+$/g.test(routeId)) {
                    foundDevice = registeredDevicesResources.resources.value.find(
                        (d) => d.id == Number(routeId),
                    );
                    foundPattern = 'id';
                }

                if (foundDevice) {
                    device.value = foundDevice;
                    groups.value = foundDevice?.groups
                        ?.map(
                            (deviceGroupId) =>
                                groupResources.resources.value?.find((g) => g.id == deviceGroupId)!,
                        )
                        .filter(Boolean);
                    pattern.value = foundPattern;
                } else {
                    await router.push({ name: ActiveTab.Devices.toString() });
                    notify.notifyError({
                        headline: `Device with ${foundPattern} '${routeId}' not found.`,
                    });
                    stop();
                }
            },
        );

        const devicesLoaded = computed(() => !!registeredDevicesResources.resources.value);

        // Actions interface

        const actions = ref<(Action & { running?: boolean })[]>([]);
        effect(async () => {
            if (!device.value) return;
            if (actions.value.length > 0) return;

            const newActions = await getDeviceActions(device.value.mac_address);

            if (newActions.success && newActions.data) {
                actions.value = newActions.data;
            } else {
                console.warn('Failed to fetch actions');
            }
        });

        const isRunning = (action_id: string) =>
            actions.value.some((a) => a.action_id == action_id && a.running);

        const setRunning = (action_id: string, running: boolean) => {
            actions.value = actions.value.map((a) => {
                if (a.action_id != action_id) return a;
                return { ...a, running };
            });
        };

        const runAction = async (action_id: string) => {
            if (isRunning(action_id)) return;

            setRunning(action_id, true);

            const action = actions.value.find((a) => a.action_id == action_id);

            notif.notifySuccess({
                headline: device.value?.name + ' — ' + action!.action_name,
                msg: `Action started`,
            });

            const outcome = await execAction(device.value!.mac_address, action_id);
            setRunning(action_id, false);

            if (outcome.success) {
                if (outcome.data.status_code != 0) {
                    notif.notifyError({
                        headline: device.value?.name + ' — ' + action!.action_name,
                        msg: `Action finished with non-zero exit code: ${outcome.data.status_code}`,
                    });
                } else {
                    notif.notifySuccess({
                        headline: device.value?.name + ' — ' + action!.action_name,
                        msg: `Action finished successfully`,
                    });
                }
            } else {
                notif.notifyError({
                    headline: device.value?.name + ' — ' + action!.action_name,
                    msg: `Action failed to execute`,
                });
            }
        };

        const isTerminalOpened = ref<boolean>(false);
        const isFullscreen = ref<boolean>(false);

        const terminalButton = computed(() => {
            if (isTerminalOpened.value) return 'Close device shell';
            else return 'Open device shell';
        });

        const toggleTerminal = () => {
            isTerminalOpened.value = !isTerminalOpened.value;
            isFullscreen.value = false;
        };

        const terminalFullscreen = () => {
            isFullscreen.value = !isFullscreen.value;
        };

        return {
            id: route.params.id,
            interval,
            devicesLoaded,
            device,
            pattern,
            groups,
            actions,
            runAction,
            toggleTerminal,
            isTerminalOpened,
            terminalButton,
            terminalFullscreen,
            isFullscreen,
        };
    },
};
</script>
