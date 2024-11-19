<!--
Copyright (c) 2024 Antmicro <www.antmicro.com>

SPDX-License-Identifier: Apache-2.0
-->

<template>
    <img :src="logoUrl" width="112" height="26" />
</template>

<script lang="ts">
import defaultLogo from '../../../common/images/rdfm-logo.svg';

const logoUrl = import.meta.env.VITE_CUSTOM_LOGO || defaultLogo;

export default {
    setup() {
        return {
            logoUrl,
        };
    },
};
</script>
