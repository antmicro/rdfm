<!--
Copyright (c) 2024-2025 Antmicro <www.antmicro.com>

SPDX-License-Identifier: Apache-2.0
-->

<!--
Component wraps functionality for displaying and working with a single rdfm device.
-->

<template>
    <div v-if="devicesLoaded">
        <TitleBar
            v-if="device"
            :title="'Device ' + device.mac_address"
            :subtitle="device.metadata['rdfm.software.version'] as string"
            :device="device.mac_address"
            smallButtonName="Open action log"
            :buttonCallback="fetchActionLog"
            :connected="
                deviceConnections.has(device.mac_address)
                    ? deviceConnections.get(device.mac_address)
                    : device.connected
            "
        />
        <TitleBar
            v-if="!device"
            :title="`Device with ${pattern} '${id}' was not found`"
            :subtitle="''"
        />

        <div
            class="actions-container"
            v-if="actions.length > 0 && allowedTo('update', 'device', device?.id)"
        >
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

        <Transition>
            <BlurPanel v-if="showingActionLog" @click.self="closeActionLogPopup">
                <div class="popup">
                    <div class="header-with-buttons">
                        <div class="title-container">
                            <div class="header">
                                <p class="title">Action log</p>
                                <p class="description">
                                    Actions assigned to device {{ device!.mac_address }}
                                </p>
                            </div>
                            <button class="action-button" @click="closeActionLogPopup">
                                <Cross />
                            </button>
                        </div>
                        <div class="divider"></div>
                        <div class="button-wrapper">
                            <p class="selected-count">{{ selectedCount }}</p>
                            <div class="buttons">
                                <button
                                    class="action-button gray"
                                    v-if="allowedTo('update', 'device', device?.id)"
                                    @click="clearActionLog()"
                                >
                                    <Completed />
                                    Clear completed tasks
                                </button>
                                <button
                                    class="action-button gray"
                                    v-if="allowedTo('update', 'device', device?.id)"
                                    @click="removePendingActions()"
                                >
                                    <Pending />
                                    Clear pending tasks
                                </button>
                                <button
                                    class="action-button red"
                                    v-if="allowedTo('update', 'device', device?.id)"
                                    @click="removeSelectedActions()"
                                >
                                    <Delete />
                                    Remove selected
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="body action-log">
                        <table>
                            <thead>
                                <tr>
                                    <th></th>
                                    <th>Action</th>
                                    <th>Created date</th>
                                    <th>Status</th>
                                    <th></th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="task in tasks" @click="selectTask(task, $event)">
                                    <td>
                                        <div class="checkbox">
                                            <div :class="task.selected ? 'selected' : ''"></div>
                                        </div>
                                    </td>
                                    <td>{{ task.action }}</td>
                                    <td>{{ task.created }}</td>
                                    <td>
                                        <div :class="['status', task.status]">
                                            {{ task.status }}
                                        </div>
                                    </td>
                                    <td>
                                        <div v-if="task.download_url" class="dots">
                                            <DownloadButton
                                                :url="task.download_url"
                                                :smallButton="true"
                                            />
                                        </div>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </BlurPanel>
        </Transition>

        <template v-if="device?.capabilities.filesystem && allowedTo('read', 'device', device?.id)">
            <div class="download-container">
                <p>Download file from path</p>
                <table class="file-selector">
                    <tbody>
                        <td class="icon">
                            <File />
                        </td>
                        <td class="input">
                            <input type="text" ref="fileToDownload" />
                        </td>
                        <td>
                            <button class="action-button" @click="downloadFile">
                                <Download />
                                Download file
                            </button>
                        </td>
                    </tbody>
                </table>
                <div v-if="emptyPathError" class="errors">
                    <p>File not found</p>
                </div>
            </div>
        </template>

        <template v-if="device?.capabilities.shell && allowedTo('shell', 'device', device?.id)">
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
                    <Terminal
                        class="terminal"
                        :device="device?.mac_address"
                        @shell-disconnected="disconnect"
                    />
                </div>
            </div>
        </template>

        <div class="device-container" v-if="device">
            <div class="block">
                <p class="title">MAC Address</p>
                <pre class="small"><code>{{ device.mac_address }}</code></pre>
            </div>
            <div class="block" v-if="tags.length > 0">
                <p class="title">Tags</p>
                <div id="tags">
                    <div v-for="tag in tags">
                        <pre class="small"><code>{{ tag }}</code></pre>
                    </div>
                </div>
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

.popup {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 2em;
}

.action-log {
    overflow-y: auto;
    overflow-x: hidden;
    max-height: 70vh;
    max-width: 95vw;

    @media screen and (max-width: 1650px) {
        font-size: small;
        max-height: 50vh;
    }

    table {
        border-collapse: separate;
        border-spacing: 0;
    }

    th {
        color: var(--gray-900);
        font-size: small;
    }

    tbody {
        td {
            border-bottom: 1px solid var(--gray-400);
            vertical-align: middle;
        }
        tr:first-child td {
            border-top: 1px solid var(--gray-400);
        }
        td:first-child {
            border-left: 1px solid var(--gray-400);
        }
        td:last-child {
            border-right: 1px solid var(--gray-400);
            text-align: center;
        }

        tr:first-child td:first-child {
            border-top-left-radius: 8px;
        }
        tr:first-child td:last-child {
            border-top-right-radius: 8px;
        }
        tr:last-child td:first-child {
            border-bottom-left-radius: 8px;
        }
        tr:last-child td:last-child {
            border-bottom-right-radius: 8px;
        }

        tr:hover {
            background: var(--gray-200);
            cursor: pointer;
        }

        .checkbox {
            border: 0.88px solid var(--gray-400);
            color: var(--gray-400);
            background: var(--gray-100);
            width: 14px;
            height: 14px;

            div {
                width: 14px;
                height: 14px;
            }
        }

        .status {
            color: var(--gray-900);
            background-color: var(--gray-100);
            border: 1px solid var(--gray-400);
            border-radius: 8px;

            text-align: center;
            vertical-align: middle;
        }

        .success {
            color: var(--success);
            background-color: var(--success-bg);
            border: 1px solid var(--success-border);
        }

        .error {
            color: var(--destructive-900);
            background-color: var(--destructive-100);
            border: 1px solid var(--destructive-400);
        }

        .dots {
            padding-left: 1em;
            padding-right: 1em;
        }

        @media screen and (max-width: 1650px) {
            td:nth-child(2) {
                word-break: break-all;
            }
        }
    }
}

.header-with-buttons {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 1.5em;

    & > .title-container {
        display: flex;
        flex-direction: row;
        justify-content: space-between;

        & > .action-button {
            background-color: var(--background-200);
            border: none;

            svg {
                width: 15px;
                height: 15px;
                fill: var(--gray-900);
            }
        }
    }

    & > .divider {
        flex-grow: 1;
        border-bottom: 1px solid var(--gray-400);
    }

    & > .button-wrapper {
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        align-items: center;

        & > .selected-count {
            color: var(--gray-900);
            padding: 0;
            margin: 0;
        }

        & > .buttons {
            display: flex;
            flex-direction: row;
            justify-content: flex-end;
            gap: 0.75em;

            & > .action-button {
                white-space: nowrap;
                display: flex;
                flex-direction: row;
                align-items: center;
                padding: 0.5em;
                border-radius: 8px;

                svg {
                    width: 15px;
                    height: 15px;
                    margin-right: 10px;
                }

                &.gray {
                    color: var(--gray-1000);
                    background-color: var(--gray-100);
                    border: 1px solid var(--gray-400);

                    svg {
                        fill: var(--gray-1000);
                    }

                    &:hover {
                        background-color: var(--gray-300);
                    }
                }

                &.red {
                    border: 1px solid var(--destructive-400);
                    svg {
                        fill: var(--destructive-900);
                    }
                }
            }
        }
    }

    @media screen and (max-width: 2000px) {
        .button-wrapper {
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 0.75em;
            align-items: start;
        }
    }

    @media screen and (max-width: 1650px) {
        .button-wrapper {
            .buttons {
                display: flex;
                flex-direction: column;
                justify-content: space-between;
            }
        }
    }
}

.download-container {
    margin: 2em;
    display: flex;
    flex-direction: column;

    .file-selector {
        width: 520px;
        height: 40px;

        border-radius: 8px;
        border-width: 1px;
        border: 1px solid var(--gray-400);
        border-collapse: separate;
        border-spacing: 0;

        td {
            padding: 0;
        }

        .icon {
            border-right: 1px solid var(--gray-400);

            height: 100%;
            display: flex;
            justify-content: center;
            align-items: center;

            & > svg {
                fill: var(--gray-900);
                width: 20px;
                height: 20px;
                padding: 8px;
            }
        }

        .input {
            border-right: 1px solid var(--gray-400);

            width: 100%;
            height: 100%;
            box-sizing: border-box;
            background: transparent;
            padding: 8px;

            input {
                height: 100%;
                width: 100%;
                margin: 0;
                padding: 0;
                border: none;
                box-sizing: border-box;
                background: transparent;
            }
        }

        .action-button {
            margin: 0px !important;
            height: 100%;
            width: fit-content;
            white-space: nowrap;
            border: 0px;
            border-radius: 0px 8px 8px 0px;
            display: flex;
            align-items: center;
            text-align: left;
            color: var(--gray-900);
            background-color: var(--background-100);

            &:hover {
                background-color: var(--gray-200);
                color: var(--gray-1000);

                svg {
                    fill: var(--gray-1000);
                }
            }

            svg {
                margin-right: 10px;
                fill: var(--gray-900);
            }
        }
    }

    .errors {
        p {
            color: var(--destructive-900);
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

    #tags {
        display: flex;
        flex-direction: row;
        gap: 0.5em;
    }
}
</style>

<script lang="ts">
import { computed, effect, ref, watch } from 'vue';

import {
    POLL_INTERVAL,
    useNotifications,
    allowedTo,
    type Group,
    type RegisteredDevice,
} from '../../common/utils';
import TitleBar from '../TitleBar.vue';
import Terminal from '../Terminal.vue';
import BlurPanel from '../BlurPanel.vue';
import UpdateProgress from '../UpdateProgress.vue';
import DownloadButton from '../DownloadButton.vue';
import Expand from '../icons/Expand.vue';
import Collapse from '../icons/Collapse.vue';
import Cross from '../icons/Cross.vue';
import Download from '../icons/Download.vue';
import File from '../icons/File.vue';
import Completed from '../icons/Completed.vue';
import Pending from '../icons/Pending.vue';
import Delete from '../icons/Delete.vue';
import {
    registeredDevicesResources,
    groupResources,
    getDeviceTags,
    getDeviceActions,
    getDeviceActionLog,
    clearDeviceActionLog,
    removePendingDeviceActions,
    removeSelectedDeviceActions,
    downloadDeviceFile,
    execAction,
    type Action,
    deviceConnections,
    deviceActions,
} from './devices';
import { useRoute, useRouter } from 'vue-router';
import { ActiveTab } from '@/views/HomeView.vue';

const MAC_ADDR_REGEX = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/;

const notif = useNotifications();

export default {
    components: {
        TitleBar,
        Terminal,
        BlurPanel,
        UpdateProgress,
        DownloadButton,
        Expand,
        Collapse,
        Cross,
        Download,
        File,
        Completed,
        Pending,
        Delete,
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

        const tags = ref<string[]>([]);
        effect(async () => {
            if (!device.value) return;

            const newTags = await getDeviceTags(device.value.id);

            if (newTags.success && newTags.data) {
                tags.value = newTags.data;
            } else {
                console.warn('Failed to fetch tags');
            }
        });

        // Actions interface

        const actions = ref<(Action & { running?: boolean })[]>([]);

        effect(async () => {
            if (!device.value) return;
            if (actions.value.length > 0) return;

            const newActions = await getDeviceActions(device.value.mac_address);

            if (newActions.success && newActions.data) {
                newActions.data.sort((a: Action, b: Action) =>
                    a.action_name.localeCompare(b.action_name),
                );
                actions.value = newActions.data;
                deviceActions.set(device.value!.mac_address, newActions.data);
            } else {
                console.warn('Failed to fetch actions');
                if (deviceActions.has(device.value!.mac_address)) {
                    actions.value = deviceActions.get(device.value!.mac_address)!;
                }
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

        const tasks = ref<any[]>([]);
        const showingActionLog = ref<boolean>(false);
        const selectedCount = computed(() => {
            const selectedTasks = tasks.value
                .filter((task: any) => task.selected)
                .map((task: any) => task.id);

            const selected = selectedTasks.length;
            const total = tasks.value.length;
            return `${selected} out of ${total} row(s) selected.`;
        });

        const fetchActionLog = async () => {
            const result = await getDeviceActionLog(device.value!.mac_address);

            if (result.success) {
                tasks.value = result.data as any[];
                tasks.value = tasks.value.map((task: any) => {
                    task.selected = false;
                    if (task.status === '0') task.status = 'success';
                    if (task.status === '-1') task.status = 'error';
                    return task;
                });
                showingActionLog.value = true;
            } else {
                notif.notifyError({
                    headline: device.value?.name + ' action log',
                    msg: `Failed to fetch action log`,
                });
            }
        };

        const clearActionLog = async () => {
            const result = await clearDeviceActionLog(device.value!.mac_address);

            if (result.success) {
                fetchActionLog();
            } else {
                notif.notifyError({
                    headline: device.value?.name + ' action log',
                    msg: `Failed to clear action log`,
                });
            }
        };

        const removePendingActions = async () => {
            const result = await removePendingDeviceActions(device.value!.mac_address);

            if (result.success) {
                fetchActionLog();
            } else {
                notif.notifyError({
                    headline: device.value?.name + ' action log',
                    msg: `Failed to remove pending actions`,
                });
            }
        };

        const removeSelectedActions = async () => {
            const selectedTasks = tasks.value
                .filter((task: any) => task.selected)
                .map((task: any) => task.id);

            const result = await removeSelectedDeviceActions(
                device.value!.mac_address,
                selectedTasks,
            );

            if (result.success) {
                fetchActionLog();
            } else {
                notif.notifyError({
                    headline: device.value?.name + ' action log',
                    msg: `Failed to remove actions`,
                });
            }
        };

        const selectTask = (task: any, e: MouseEvent) => {
            const target = e!.target as HTMLElement;

            if (!target.closest('.dots')) {
                task.selected = !task.selected;
            }
        };

        const closeActionLogPopup = () => {
            showingActionLog.value = false;
        };

        const fileToDownload = ref<HTMLInputElement | null>(null);
        const emptyPathError = ref<boolean>(false);

        const downloadFile = async () => {
            if (!fileToDownload.value!.value) {
                emptyPathError.value = true;
            }

            const result = await downloadDeviceFile(device.value!.id, fileToDownload.value!.value);

            if (!result.success) {
                notif.notifyError({
                    headline: device.value?.name + ' download',
                    msg: `Failed to download file`,
                });
                emptyPathError.value = true;
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

        const disconnect = () => {
            toggleTerminal();
            device.value!.connected = false;
        };

        return {
            id: route.params.id,
            interval,
            devicesLoaded,
            device,
            pattern,
            tags,
            groups,
            actions,
            tasks,
            runAction,
            fetchActionLog,
            clearActionLog,
            removePendingActions,
            removeSelectedActions,
            selectTask,
            selectedCount,
            showingActionLog,
            closeActionLogPopup,
            downloadFile,
            fileToDownload,
            emptyPathError,
            toggleTerminal,
            isTerminalOpened,
            terminalButton,
            terminalFullscreen,
            isFullscreen,
            disconnect,
            allowedTo,
            deviceConnections,
        };
    },
};
</script>
