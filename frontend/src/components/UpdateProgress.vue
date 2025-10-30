<!--
Copyright (c) 2025 Antmicro <www.antmicro.com>

SPDX-License-Identifier: Apache-2.0
-->

<!--
Component representing a progress bar.
Shown when a device is being updated.
-->

<template>
    <div id="progress-bar-wrapper">
        <div id="header">
            <p id="version">Updating to {{ version }}...</p>
            <p id="percentage">{{ progress }}%</p>
        </div>
        <div id="container">
            <div id="progress-bar" :style="{ width: progress + '%' }"></div>
        </div>
    </div>
</template>

<style scoped>
#progress-bar-wrapper {
    display: flex;
    flex-direction: column;
    width: 300px;

    & > #header {
        position: relative;
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        width: 100%;

        & > p {
            font-size: 1em;
            margin: 0;
            padding-bottom: 0.5em;
        }
        & > #version {
            color: var(--gray-900);
        }
        & > #percentage {
            color: var(--accent-900);
        }
    }

    & > #container {
        position: relative;
        border: 1px solid var(--accent-400);
        border-radius: 5px;
        background-color: var(--accent-100);
        height: 10px;
        width: 100%;

        & > #progress-bar {
            height: 100%;
            border-radius: 5px;
            background-color: var(--accent-500);
            transition: width 0.3s ease;
        }
    }
}
</style>

<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({
    props: {
        progress: {
            type: Number,
            required: true,
        },
        version: {
            type: String,
            required: true,
        },
    },
});
</script>
