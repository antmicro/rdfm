<template>
    <div class="dropdown-holder">
        <div class="dropdown">
            <div class="tags">
                <div v-for="tag in tags" :key="tag.id" class="t">
                    <p>#{{ tag.name }}</p>
                    <button @click="() => select(tag.id)"><Cross /></button>
                </div>
            </div>
            <button @click="toggleDropdown" v-if="!tags.length" class="hint">
                {{ placeholder }}
            </button>
            <button @click="toggleDropdown" class="dropdown-opener">
                <CaretUp v-if="dropdownOpen" />
                <CaretDown v-else />
            </button>
        </div>
        <div v-if="dropdownOpen" class="table-holder" ref="tableRef" :style="tableStyles">
            <table>
                <thead>
                    <tr>
                        <th></th>
                        <th v-for="col in columns" :key="col.name">{{ col.name }}</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(row, i) in data" :key="row.id" @click="() => select(i)">
                        <td>
                            <div class="checkbox">
                                <div :class="row.selected ? 'selected' : ''"></div>
                            </div>
                        </td>
                        <td v-for="col in columns" :key="col.name">
                            {{
                                row[col.id].toString().length > 18
                                    ? row[col.id].toString().substring(0, 14) + '...'
                                    : row[col.id].toString()
                            }}
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>

<style>
.dropdown-holder,
.dropdown-holder * {
    box-sizing: border-box;
}

.dropdown-holder {
    position: relative;
}

.dropdown {
    height: fit-content;
    color: var(--gray-900);
    padding: 0.5em;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5em;
    background: none;
    border: none;
}

.dropdown,
.table-holder {
    background: var(--gray-100);
    border: 1px solid var(--gray-400);
    border-radius: 4px;
    width: 100%;
}

.dropdown-opener {
    background: transparent;
    border: none;
}

.table-holder {
    overflow: auto;
    position: absolute;
    margin-top: 0.25em;
    padding: 0.5em;
    z-index: 10;
}

input,
.hint {
    background: transparent;
    border: none;
}

.hint {
    font-size: 14px;
    font-weight: 600;
    text-align: start;
    width: 100%;
    margin: 0;
    color: var(--gray-600);
    padding: 0;
}

input[type='checkbox'] {
    appearance: none;
    border: 1px solid var(--gray-400);
    border-radius: 4px;
    color: var(--gray-400);
    background: var(--gray-100);
    margin: 0;
    width: 4em;
    height: 4em;
}

button:hover {
    cursor: pointer;
}

table {
    border-collapse: collapse;
    border: 0;
    width: 100%;
}

th {
    text-align: start;
}

th,
td {
    padding: 0.5em;
}

.checkbox {
    border: 1px solid var(--gray-1000);
    border-radius: 4px;
    width: 1em;
    height: 1em;
    display: flex;
    align-items: center;
    justify-content: center;
}

.checkbox > div {
    width: 0.5em;
    height: 0.5em;
    border-radius: 2px;
    transform: scale(0);
    transition: transform 0.25s ease;
    background: var(--gray-1000);
}

.checkbox > div.selected {
    transform: scale(1);
}

tbody tr:hover {
    background: var(--gray-400);
    cursor: pointer;
}

tbody tr:active {
    background: var(--gray-500);
}

.t {
    display: flex;
    align-items: center;
    padding: 4px 0.5em;
    gap: 4px;
    color: var(--gray-1000);
    border: 1px solid var(--gray-400);
    border-radius: 4px;
}

.t > p {
    margin: 0;
}

.t > button {
    background: transparent;
    border: none;

    display: flex;
    justify-content: center;
    align-items: center;
    padding: 0;
}
</style>

<script lang="ts">
import { computed, defineComponent, ref } from 'vue';
import type { PropType, Ref } from 'vue';
import Cross from '../images/Cross.vue';
import CaretUp from '../images/CaretUp.vue';
import CaretDown from '../images/CaretDown.vue';

export interface DataEntry {
    id: number;
    selected: boolean;
    [key: string]: string | number | boolean;
}

export interface Column {
    id: string;
    name: string;
}

export default defineComponent({
    components: {
        CaretUp,
        CaretDown,
        Cross,
    },
    props: {
        placeholder: {
            type: String,
            required: true,
        },
        columns: {
            type: Object as PropType<Column[]>,
            required: true,
        },
        select: {
            type: Function as PropType<(id: number) => void>,
            required: true,
        },
        data: {
            type: Array as PropType<DataEntry[]>,
            required: true,
        },
        toggleDropdown: {
            type: Function as PropType<() => void>,
            required: true,
        },
        dropdownOpen: {
            type: Boolean,
            required: true,
        },
    },
    setup(props) {
        // Height of the dropdown has to be set dynamically
        const tableRef = ref<HTMLDivElement | null>(null);

        const tags = computed(() => {
            const tags_ = [];
            for (let i = 0; i < props.data.length; i++) {
                if (props.data[i].selected) {
                    tags_.push({ name: props.data[i].id, id: i });
                }
            }
            return tags_;
        });

        const tableStyles = computed(() => {
            if (!tableRef.value) {
                return {};
            }

            const bottomOffset = 16;
            return {
                'max-height': `${window.innerHeight - tableRef.value?.getBoundingClientRect().top - bottomOffset}px`,
            };
        });

        return {
            tags,
            tableStyles,
            tableRef,
        };
    },
});
</script>
