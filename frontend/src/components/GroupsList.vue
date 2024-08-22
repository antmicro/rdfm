<template>
    <TitleBar
        title="Groups"
        subtitle="manage your groups"
        actionButtonName="Create new group"
        :buttonCallback="createGroup"
    />

    <div class="container">
        <p>Groups</p>
        <div v-for="group in groups" :key="group.id" class="group">
            <div class="group-row">
                <div class="entry">
                    <div class="title">ID</div>
                    <div class="value">{{ group.id }}</div>
                </div>
                <div class="entry">
                    <div class="title">Created</div>
                    <div class="value">{{ group.created }}</div>
                </div>
                <div class="entry">
                    <div class="title">Policy</div>
                    <div class="value">{{ group.policy }}</div>
                </div>
                <div class="entry">
                    <div class="title">Priority</div>
                    <div class="value">{{ group.priority }}</div>
                </div>
            </div>
            <div class="group-row">
                <div class="entry">
                    <div class="title">{{ group.packages.length }} Packages</div>
                    <div class="value">{{ group.packages }}</div>
                </div>
            </div>
            <div class="group-row">
                <div class="entry">
                    <div class="title">{{ group.devices.length }} Devices</div>
                    <div class="value">{{ group.devices }}</div>
                </div>
            </div>
        </div>
    </div>

    <!-- <div>
        <h2>Create a new group:</h2>
        <form @submit.prevent="addGroup">
            <input type="text" v-model="newGroupData.name" placeholder="Name" />
            <br />
            <input type="text" v-model="newGroupData.description" placeholder="Description" />
            <br />
            <input type="text" v-model="newGroupData.priority" placeholder="Priority" />
            <br />
            <input type="submit" />
        </form>
    </div> -->

    <!-- <ListWrapper :pollingStatus="pollingStatus">
        <div v-if="groups!.length === 0">
            <h2>No groups defined</h2>
        </div>
        <div v-else>
            <h2>Groups:</h2>
            <div v-for="group in groups" :key="group.id" class="group-entry">
                ID: {{ group.id }} <br />
                Created: {{ group.created }} <br />
                Packages: {{ group.packages }} <br />
                Devices: {{ group.devices }} <br />
                Metadata:
                <ul>
                    <li v-for="[key, data] in Object.entries(group.metadata)" :key="key">
                        {{ key }}: {{ data }}
                    </li>
                </ul>
                Policy: {{ group.policy }} <br />
                <input
                    @change="updatePriority(group.id, group.priority)"
                    type="number"
                    v-model="group.priority"
                /><br />
                <br />
                <button @click="deleteGroup(group.id)">Delete</button>
            </div>
        </div>
    </ListWrapper> -->
</template>

<style scoped>
.container {
    padding: 2em;

    & > p {
        color: var(--gray-1000);
        font-size: 1.5em;
    }

    & > .group {
        display: flex;
        flex-direction: column;

        border: 2px solid var(--gray-400);
        border-radius: 5px;
        margin-bottom: 2em;

        & > .group-row {
            display: flex;
            flex-direction: row;
            border-bottom: 2px solid var(--gray-400);

            &:last-child {
                border: none;
            }

            & > .entry {
                padding: 0.5em 1em;

                & > .title {
                    color: var(--gray-900);
                    text-wrap: nowrap;
                }

                & > .value {
                    color: var(--gray-1000);
                    text-wrap: nowrap;
                }
            }
        }

        color: var(--gray-1000);
    }
}
</style>

<script lang="ts">
import { onMounted, onUnmounted, reactive } from 'vue';

import {
    GROUPS_ENDPOINT,
    POLL_INTERVAL,
    DELETE_GROUP_ENDPOINT,
    UPDATE_GROUP_PRIORITY_ENDPOINT,
    resourcesGetter,
} from '../common/utils';
import { type Group } from '../common/utils';
import TitleBar from './TitleBar.vue';

export default {
    components: {
        TitleBar,
    },
    setup() {
        const groupResources = resourcesGetter<Group[]>(GROUPS_ENDPOINT);
        const newGroupData = reactive({
            name: '',
            description: '',
            priority: '',
        });

        const POSTHeaders = new Headers();
        POSTHeaders.set('Content-type', 'application/json');
        POSTHeaders.set('Accept', 'application/json, text/javascript');

        let intervalID: undefined | number = undefined;

        const deleteGroup = async (packageId: number) => {
            const [status] = await groupResources.fetchDELETE(DELETE_GROUP_ENDPOINT(packageId));
            if (status) {
                await groupResources.fetchResources();
            } else {
                console.error('Failed to delete group');
            }
        };

        const startPolling = () => {
            if (intervalID === undefined) {
                intervalID = setInterval(async () => {
                    await groupResources.fetchResources();
                }, POLL_INTERVAL);
            }
        };

        const stopPolling = () => {
            if (intervalID !== undefined) {
                clearInterval(intervalID);
            }
        };

        onMounted(async () => {
            await groupResources.fetchResources();
            startPolling();
        });

        onUnmounted(() => {
            stopPolling();
        });

        const addGroup = async () => {
            const body = JSON.stringify({
                // Keys are taken from the manager source code
                priority: newGroupData.priority,
                metadata: {
                    'rdfm.group.name': newGroupData.name,
                    'rdfm.group.description': newGroupData.description,
                },
            });

            const [status] = await groupResources.fetchPOST(GROUPS_ENDPOINT, POSTHeaders, body);
            if (status) {
                await groupResources.fetchResources();
            } else {
                console.error('Failed to create a new group');
            }
        };

        const updatePriority = async (groupId: number, priority: number) => {
            // Polling is paused when handling update requests
            // TODO: This does not fix the issue fully, I guess some form of submit button is needed
            stopPolling();

            const body = JSON.stringify({
                priority: priority,
            });

            const [status] = await groupResources.fetchPOST(
                UPDATE_GROUP_PRIORITY_ENDPOINT(groupId),
                POSTHeaders,
                body,
            );
            if (status) {
                await groupResources.fetchResources();
            } else {
                console.error('Failed to update group priority');
            }
            // Polling is restored after update handling is finished
            startPolling();
        };

        const createGroup = () => alert('TODO!');

        return {
            addGroup,
            createGroup,
            deleteGroup,
            groups: groupResources.resources,
            newGroupData,
            pollingStatus: groupResources.pollingStatus,
            updatePriority,
        };
    },
};
</script>
