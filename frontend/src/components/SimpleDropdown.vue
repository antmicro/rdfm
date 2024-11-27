<template>
    <div
        tabindex="1"
        :style="{ border: expanded ? '1px solid var(--gray-800)' : '' }"
        class="simple-dropdown"
        v-on:blur="() => (expanded = false)"
        v-on:click="() => (expanded = !expanded)"
    >
        <div style="width: 100%" v-on:click="() => (expanded = false)">
            {{ selected?.display || 'No value' }}
            <CaretDown v-if="!expanded" />
            <CaretUp v-if="expanded" />
        </div>

        <div class="dropdown-options" v-if="expanded">
            <div
                v-on:click="
                    () => {
                        select?.(opt.id);
                        selected = opt;
                    }
                "
                v-for="opt in options"
                :key="opt.id"
                class="option"
            >
                {{ opt.display }}
            </div>
        </div>
    </div>
</template>

<style>
.dropdown-options {
    position: absolute;
    top: 39px;
    left: -1px;
    right: 17px;
    z-index: 14;
    height: fit-content;
    border: 1px solid var(--gray-400);
    border-radius: 5px;
}

.simple-dropdown {
    cursor: pointer;
    position: relative;
    color: white;

    svg {
        float: right;
        padding: 4px;
    }
}

.option {
    width: 100%;
    height: fit-content;
    padding: 0.5em;
    background: var(--gray-100);
    &:hover {
        background: var(--gray-500);
    }
}

.simple-dropdown {
    height: fit-content;
    padding: 0.5em;
    background: var(--gray-100);
    border: 1px solid var(--gray-400);
    border-radius: 4px;
}
</style>

<script lang="ts">
import CaretDown from '@/images/CaretDown.vue';
import CaretUp from '@/images/CaretUp.vue';
import { computed, defineComponent, ref, type PropType } from 'vue';

export default defineComponent({
    props: {
        options: {
            type: Object as PropType<{ id: string; display: string }[]>,
            required: true,
        },
        initial: {
            type: Object as PropType<string | null>,
            required: true,
        },
        select: {
            type: Function as PropType<(selected: string) => void>,
            required: true,
        },
    },
    setup(props) {
        const options = computed(() => props.options);
        return {
            expanded: ref(false),
            selected: ref(options.value.find((o) => o.id == props.initial)),
            options,
            select: props.select,
        };
    },
    components: { CaretDown, CaretUp },
});
</script>
