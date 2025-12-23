<!--
Copyright (c) 2024 Antmicro <www.antmicro.com>

SPDX-License-Identifier: Apache-2.0
-->

<!--
Component representing a top bar of each view,
with a title, subtitle and an optional action button.
-->

<template>
    <div id="wrapper">
        <div v-if="device" id="status">
            <Status :connected="connected" :detailed="true" />
        </div>
        <div id="content-wrapper">
            <div id="titlebar">
                <div v-if="smallButtonName" id="title-container">
                    <div id="title">{{ title }}</div>
                    <button id="small-button" @click="buttonCallback">{{ smallButtonName }}</button>
                </div>
                <div v-else id="title">{{ title }}</div>
                <div id="subtitle">{{ subtitle }}</div>
            </div>
            <div v-if="displayButton" id="actionbar">
                <button id="action-button" @click="buttonCallback">{{ actionButtonName }}</button>
            </div>
            <div
                id="update"
                v-if="device && deviceUpdates.has(device) && deviceVersions.has(device)"
            >
                <UpdateProgress
                    :progress="deviceUpdates.get(device)!"
                    :version="deviceVersions.get(device)!"
                />
            </div>
            <div id="no-update" v-else-if="device">
                <p>No updates available</p>
            </div>
        </div>
    </div>
</template>

<style scoped>
#wrapper {
    border: 1px solid var(--gray-400);
    display: flex;
    flex-direction: row;
    justify-content: start;
    padding: 2em;

    & > #status {
        align-content: top;
        padding-top: 1.5em;
        padding-right: 1.5em;
    }

    & > #content-wrapper {
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        flex-wrap: wrap;
        width: 100%;

        & > #titlebar {
            display: flex;
            flex-direction: column;
            font-family: 'Mona Sans', sans-serif;
            word-break: break-word;

            #title {
                color: var(--gray-1000);
                font-weight: 700;
                font-size: 3em;
            }

            & > #subtitle {
                color: var(--gray-900);
                font-size: 1.3em;
            }

            & > #title-container {
                display: flex;
                flex-direction: row;
                align-items: center;
                gap: 2em;

                #small-button {
                    border: 1px solid var(--gray-400);
                    border-radius: 8px;
                    padding: 0.5em;
                    color: var(--gray-900);
                    background-color: var(--background-100);
                    font-size: 1em;
                    height: fit-content;
                    text-wrap: nowrap;
                    word-break: none;

                    &:hover {
                        background-color: var(--gray-200);
                        color: var(--gray-1000);
                    }
                }
            }
        }

        & > #actionbar {
            display: flex;
            align-items: center;

            & > #action-button {
                color: var(--accent-900);
                background-color: var(--accent-100);
                border: 2px solid var(--accent-400);
                border-radius: 5px;
                font-size: 1em;
                padding: 0.75em;
                cursor: pointer;

                &:hover {
                    background-color: var(--accent-200);
                }
            }
        }

        & > #no-update {
            & > p {
                color: var(--gray-900);
            }
        }
    }
}

@media screen and (max-width: 500px) {
    #content-wrapper {
        flex-direction: column;

        & > #actionbar {
            padding-top: 2em;
        }
    }
}
</style>

<script lang="ts">
import { computed, defineComponent } from 'vue';
import { type PropType } from 'vue';
import Status from './Status.vue';
import UpdateProgress from './UpdateProgress.vue';
import { deviceUpdates, deviceVersions } from './devices/devices';

export default defineComponent({
    props: {
        title: {
            type: String,
            required: true,
        },
        subtitle: {
            type: String,
            required: true,
        },
        actionButtonName: {
            type: String,
        },
        buttonCallback: {
            type: Function as PropType<(payload: MouseEvent) => void>,
        },
        device: {
            type: String,
        },
        connected: {
            type: Boolean,
        },
        smallButtonName: {
            type: String,
        },
    },
    components: {
        Status,
        UpdateProgress,
    },
    setup(props) {
        const displayButton = computed(() => props.actionButtonName && props.buttonCallback);

        return { displayButton, deviceUpdates, deviceVersions };
    },
});
</script>
