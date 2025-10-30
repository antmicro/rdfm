<!--
Copyright (c) 2025 Antmicro <www.antmicro.com>

SPDX-License-Identifier: Apache-2.0
-->

<!--
Component representing device connection status.
-->

<template>
    <div v-if="detailed" id="status-indicator">
        <div :class="['dot', 'detailed', connected ? 'connected' : 'disconnected']"></div>
        <div class="tooltip">{{ text }}</div>
    </div>
    <div v-else :class="['dot', 'basic', connected ? 'connected' : 'disconnected']"></div>
</template>

<style scoped>
#status-indicator {
    position: relative;
    display: inline-block;
}

.dot {
    margin: auto;
    border-radius: 50%;
}

.connected {
    background-color: #27a316;
}

.disconnected {
    background-color: var(--gray-800);
}

.detailed {
    width: 1.25em;
    height: 1.25em;
}

.basic {
    width: 0.75em;
    height: 0.75em;
}

.tooltip {
    visibility: hidden;
    opacity: 0;

    position: absolute;
    top: 140%;

    color: var(--gray-1000);
    background-color: var(--gray-100);
    border: 2px solid var(--gray-400);

    padding: 6px 8px;
    border-radius: 4px;

    transition: opacity 0.2s ease-in-out;
    z-index: 10;
}

#status-indicator:hover .tooltip {
    visibility: visible;
    opacity: 1;
}
</style>
<script lang="ts">
import { defineComponent, computed } from 'vue';

export default defineComponent({
    props: {
        connected: {
            type: Boolean,
            required: true,
        },
        detailed: {
            type: Boolean,
            required: true,
        },
    },
    setup(props) {
        const text = computed(() => (props.connected ? 'Connected' : 'Disconnected'));
        return { text };
    },
});
</script>
