<!--
Copyright (c) 2025 Antmicro <www.antmicro.com>

SPDX-License-Identifier: Apache-2.0
-->

<!--
Component representing device connection status.
-->

<template>
    <img :src="logo" :alt="vendor" />
</template>

<style scoped>
img {
    width: 100%;
    object-fit: contain;
}
</style>

<script lang="ts">
import { defineComponent, computed } from 'vue';
import type { PropType } from 'vue';

export default defineComponent({
    props: {
        deviceType: {
            type: [String, Array] as PropType<string | string[]>,
            required: true,
        },
    },
    setup(props) {
        const path = '/assets/';
        const rules = [
            { pattern: /(agx|jetson|nvidia|orin)/gi, logo: 'nvidia.svg', vendor: 'NVIDIA' },
            { pattern: /(renode)/gi, logo: 'renode.svg', vendor: 'Renode' },
        ];
        const generic = { logo: 'tux.svg', vendor: 'Linux' };
        const match = computed(() =>
            rules.find(({ pattern }) => pattern.test(props.deviceType as string)),
        );
        const found = match.value ?? generic;
        return { logo: path + found.logo, vendor: found.vendor };
    },
});
</script>
