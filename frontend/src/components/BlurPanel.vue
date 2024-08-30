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
