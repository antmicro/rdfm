<!--
Copyright (c) 2025 Antmicro <www.antmicro.com>

SPDX-License-Identifier: Apache-2.0
-->

<!--
Container for the hterm.js terminal.
-->

<template>
    <div id="hterm-terminal"></div>
</template>

<script lang="ts">
import {
    defineComponent,
    computed,
    onMounted,
    onUnmounted,
    watch,
    nextTick,
    defineEmits,
} from 'vue';

// @ts-ignore
import { hterm, lib } from '../third-party/hterm';
import { DEVICE_SHELL_ENDPOINT, useNotifications } from '../common/utils';

export default defineComponent({
    props: {
        device: {
            type: String,
        },
    },
    setup(props, { emit }) {
        const notifications = useNotifications();

        let term: any;
        let socket: WebSocket;
        const htermSettings: Record<string, string | boolean> = {
            'background-color': '#000000',
            'cursor-color': 'white',
            'mouse-right-click-paste': false,
            'pass-meta-v': false,
            'mouse-paste-button': 'no-button',
            'pass-on-drop': false,
            'shift-insert-paste': false,
        };
        const closeEventListener = (event: CloseEvent) => {
            emit('shell-disconnected');

            notifications.notifyError({
                headline: 'Device shell connection closed',
                msg: event.reason || 'Shell is not available',
            });
        };

        const setHTermPreferences = () => {
            Object.keys(htermSettings).forEach((key) => {
                localStorage.setItem(
                    `/hterm/profiles/default/${key}`,
                    JSON.stringify(htermSettings[key]),
                );
            });
        };

        onUnmounted(() => {
            if (socket) {
                socket.removeEventListener('close', closeEventListener);
                socket.close();
                notifications.notifySuccess({
                    headline: `Device ${props.device} shell closed`,
                });
            }
        });

        onMounted(async () => {
            await lib.init();
            setHTermPreferences();
            term = new hterm.Terminal();
            term.scrollPort_.contenteditable = false;

            term.onTerminalReady = function onTerminalReady() {
                if (props.device) {
                    const accessToken = localStorage.getItem('access_token') as string;
                    socket = new WebSocket(DEVICE_SHELL_ENDPOINT(props.device, accessToken));
                    let firstMessage = true;

                    const sendMessage = (str: string) => {
                        const encoder = new TextEncoder();
                        const raw = encoder.encode(str);
                        socket.send(raw);
                    };

                    socket.addEventListener('open', (event: Event) => {
                        term.io.print(`Connecting to device ${props.device}...\n\r`);
                        socket.send(`resize ${term.screenSize.height} ${term.screenSize.width}`);
                    });

                    socket.addEventListener('message', async (event: MessageEvent) => {
                        const blob = event.data as Blob;
                        const text = await blob.text();
                        term.io.print(text);

                        if (firstMessage) {
                            notifications.notifySuccess({
                                headline: `Device ${props.device} shell available`,
                            });
                            firstMessage = false;
                        }
                    });

                    socket.addEventListener('error', (error: Event) => {
                        term.io.print('An error occurred\n\r');
                        notifications.notifyError({
                            headline: 'Device shell connection failed',
                        });
                    });

                    socket.addEventListener('close', closeEventListener);

                    this.io.onVTKeystroke = (str: string) => sendMessage(str);

                    this.io.sendString = (str: string) => sendMessage(str);

                    this.io.onTerminalResize = () => {
                        this.focus();
                        if (socket === undefined) return;
                        if (socket.readyState !== WebSocket.OPEN) return;
                        socket.send(`resize ${term.screenSize.height} ${term.screenSize.width}`);
                    };

                    this.installKeyboard();
                } else {
                    term.io.print(`Unable to connect. Device is undefined.\n\r`);
                    notifications.notifyError({
                        headline: 'Unable to connect to device shell',
                        msg: 'Device is undefined',
                    });
                }
            };

            term.decorate(document.querySelector('#hterm-terminal'));
        });
    },
});
</script>

<style scoped>
#hterm-terminal {
    position: relative;
    width: 100%;
    height: 100%;
    background-color: var(--background-200);
}
</style>
