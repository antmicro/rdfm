<!--
Copyright (c) 2024 Antmicro <www.antmicro.com>

SPDX-License-Identifier: Apache-2.0
-->

<template>
    <p>Logging out...</p>
</template>

<script lang="ts">
import router from '../router/index';

export default {
    setup() {
        localStorage.removeItem('access_token');
        router.push('/');
        return {};
    },
};
</script>
