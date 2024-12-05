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
        <div id="titlebar">
            <div id="title">{{ title }}</div>
            <div id="subtitle">{{ subtitle }}</div>
        </div>
        <div v-if="displayButton" id="actionbar">
            <button id="action-button" @click="buttonCallback">{{ actionButtonName }}</button>
        </div>
    </div>
</template>

<style scoped>
#wrapper {
    border: 1px solid var(--gray-400);
    display: flex;
    flex-direction: row;
    justify-content: space-between;
    padding: 2em;

    & > #titlebar {
        display: flex;
        flex-direction: column;
        font-family: 'Mona Sans', sans-serif;

        & > #title {
            color: var(--gray-1000);
            font-weight: 700;
            font-size: 3em;
        }

        & > #subtitle {
            color: var(--gray-900);
            font-size: 1.3em;
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
}
</style>

<script lang="ts">
import { computed, defineComponent } from 'vue';
import { type PropType } from 'vue';

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
    },
    setup(props) {
        const displayButton = computed(() => props.actionButtonName && props.buttonCallback);

        return { displayButton };
    },
});
</script>
