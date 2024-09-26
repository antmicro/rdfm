<template>
    <div class="dropdown-holder">
        <div class="dropdown">
            <div class="tags">
                <div v-for="tag in tags" :key="tag" class="t">
                    <p>#{{ tag.name }}</p>
                    <button @click="() => select(tag.id)"><img src="/src/images/x.svg" /></button>
                </div>
            </div>
            <button @click="() => (dropdownOpen = !dropdownOpen)" v-if="!tags.length" class="hint">
                Choose packages
            </button>
            <button @click="() => (dropdownOpen = !dropdownOpen)" class="dropdown-opener">
                <img :src="`/src/images/caret-${dropdownOpen ? 'up' : 'down'}.svg`" />
            </button>
        </div>
        <div v-if="dropdownOpen" class="table-holder">
            <table>
                <thead>
                    <tr>
                        <th></th>
                        <th v-for="col in columnNames" :key="col">{{ col }}</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(row, i) in packages" :key="row.id" @click="() => select(i)">
                        <td>
                            <div class="checkbox">
                                <div :class="selected[i] ? 'selected' : ''"></div>
                            </div>
                        </td>
                        <td>#{{ row.id }}</td>
                        <td>{{ row.version }}</td>
                        <td>{{ row.device }}</td>
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
    height: 44px;
    color: var(--gray-900);
    padding: 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
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
    position: absolute;
    margin-top: 4px;
    padding: 8px;
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
    width: 16px;
    height: 16px;
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
    padding: 8px;
}

.checkbox {
    border: 1px solid var(--gray-1000);
    border-radius: 4px;
    width: 16px;
    height: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.checkbox > div {
    width: 10px;
    height: 10px;
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
    padding: 4px 8px;
    gap: 4px;
    color: var(--gray-1000);
    border: 1px solid var(--gray-400);
    border-radius: 4px;
}

.t > p {
    margin: 0;
}

.t > button {
    width: 16px;
    height: 16px;
    background: transparent;
    border: none;
}
</style>

<script lang="ts">
import { ref, computed } from 'vue';

export default {
    props: ['columnNames', 'data', 'select', 'selected'],
    setup(props) {
        const dropdownOpen = ref(false);

        const packages = computed(() =>
            props.data.map((el) => ({
                id: el.id,
                version: el.metadata['rdfm.software.version'],
                device: el.metadata['rdfm.hardware.devtype'],
            })),
        );

        const tags = computed(() =>
            props.selected
                .map((v, i) => (v ? { name: packages.value[i].id, id: i } : null))
                .filter((v) => v),
        );

        return {
            dropdownOpen,
            packages,
            tags,
        };
    },
};
</script>
