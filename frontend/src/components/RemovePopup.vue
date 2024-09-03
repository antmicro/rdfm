<template>
    <Transition>
        <BlurPanel v-if="enabled">
            <div class="popup">
                <div class="header">
                    <p class="title">{{ title }}</p>
                    <p class="description">
                        {{ description }}
                    </p>
                </div>
                <div class="body">
                    <div class="buttons">
                        <button class="action-button gray" @click="cancelCallback">Cancel</button>
                        <button class="action-button red-fill" @click="removeCallback">
                            Remove
                        </button>
                    </div>
                </div>
            </div>
        </BlurPanel>
    </Transition>
</template>

<script lang="ts">
import { defineComponent, type PropType } from 'vue';
import BlurPanel from './BlurPanel.vue';

export default defineComponent({
    components: {
        BlurPanel,
    },
    props: {
        enabled: {
            type: Boolean,
            required: true,
        },
        title: {
            type: String,
            required: true,
        },
        description: {
            type: String,
            required: true,
        },
        cancelCallback: {
            type: Function as PropType<(payload: MouseEvent) => void>,
            required: true,
        },
        removeCallback: {
            type: Function as PropType<(payload: MouseEvent) => void>,
            required: true,
        },
    },
});
</script>
