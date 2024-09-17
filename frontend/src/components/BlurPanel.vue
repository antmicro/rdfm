<!--
Copyright (c) 2024 Antmicro <www.antmicro.com>

SPDX-License-Identifier: Apache-2.0
-->

<!--
Component representing a panel with a blurred background that occupies the whole screen.
-->

<template>
    <div class="blur-panel">
        <slot />
    </div>
</template>

<style>
.blur-panel {
    background-color: var(--background-200-05);

    position: fixed;
    z-index: 10;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    user-select: none;
}
</style>
