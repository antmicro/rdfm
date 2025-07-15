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
import { defineComponent, computed, onMounted, watch, nextTick } from 'vue';

// @ts-ignore
import { hterm, lib } from '../third-party/hterm';

export default defineComponent({
    props: {
        device: {
            type: String,
        },
    },
    setup(props) {
        let term: any;
        const htermSettings: Record<string, string | boolean> = {
            'background-color': '#000000',
            'cursor-color': 'white',
            'mouse-right-click-paste': false,
            'pass-meta-v': false,
            'mouse-paste-button': 'no-button',
            'pass-on-drop': false,
            'shift-insert-paste': false,
        };

        const setHTermPreferences = () => {
            Object.keys(htermSettings).forEach((key) => {
                localStorage.setItem(
                    `/hterm/profiles/default/${key}`,
                    JSON.stringify(htermSettings[key]),
                );
            });
        };

        onMounted(async () => {
            await lib.init();
            setHTermPreferences();
            term = new hterm.Terminal();
            term.scrollPort_.contenteditable = false;

            term.onTerminalReady = function onTerminalReady() {
                this.io.onTerminalResize = () => {
                    this.focus();
                };

                if (props.device) {
                    const accessToken = localStorage.getItem('access_token');
                    const socket = new WebSocket(
                        `wss://${window.location.host}/api/v1/devices/${props.device}/shell@token=${accessToken}`,
                    );
                    socket.addEventListener('open', (event: Event) => {
                        term.io.print(`Connecting to device ${props.device}...\n\r`);
                    });

                    socket.addEventListener('message', async (event: MessageEvent) => {
                        const blob = event.data as Blob;
                        const text = await blob.text();
                        term.io.print(text);
                    });

                    socket.addEventListener('error', (error: Event) => {
                        term.io.print('An error occurred\n\r');
                        console.error('Device shell error', error);
                    });

                    socket.addEventListener('close', (event: CloseEvent) => {
                        term.io.print('Console unavailable');
                        if (event.reason) {
                            term.io.print(`: ${event.reason}`);
                        }
                        term.io.print('\n\r');
                    });

                    this.io.onVTKeystroke = (str: string) => {
                        const encoder = new TextEncoder();
                        const raw = encoder.encode(str);
                        socket.send(raw);
                    };

                    this.installKeyboard();
                } else {
                    term.io.print(`Unable to connect. Device is undefined.\n\r`);
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
