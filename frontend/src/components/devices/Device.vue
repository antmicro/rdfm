<!--
Copyright (c) 2025 Antmicro <www.antmicro.com>

SPDX-License-Identifier: Apache-2.0
-->

<!--
Component wraps functionality for displaying and working with a single rdfm device.
-->

<template>
    <div v-if="devicesLoaded">
        <TitleBar v-if="device" :title="'Device ' + device.mac_address" :subtitle="device.name" />
        <TitleBar
            v-if="!device"
            :title="`Device with ${pattern} '${id}' was not found`"
            :subtitle="''"
        />

        <div class="device-container" v-if="device">
            <div class="block">
                <p class="title">MAC Address</p>
                <pre class="small"><code>{{ device.mac_address }}</code></pre>
            </div>
            <div class="block">
                <p class="title">Device Type</p>
                <pre class="small"><code>{{ device.metadata['rdfm.hardware.devtype'] }}</code></pre>
            </div>
            <div class="block">
                <p class="title">Software Version</p>
                <pre class="small"><code>{{ device.metadata['rdfm.software.version'] }}</code></pre>
            </div>
            <div class="block">
                <p class="title">Groups</p>
                <p class="value">
                    <span
                        class="groupname"
                        v-if="(device.groups || []).length > 0"
                        v-for="group in device.groups"
                        >{{ group }}
                    </span>
                    <span v-if="(device.groups || []).length == 0"
                        >This device is not assigned to any group</span
                    >
                </p>
            </div>
            <div class="block">
                <p class="title">Last Access</p>
                <p class="value">{{ device.last_access }}</p>
            </div>
            <div class="block">
                <p class="title">capabilities</p>
                <pre class="large"><code >{{ device.capabilities }}</code></pre>
            </div>
            <div class="block">
                <p class="title">Metadata</p>
                <pre><code >{{ device.metadata }}</code></pre>
            </div>
        </div>
    </div>
</template>

<style scoped>
.device-container {
    background-color: var(--background-200);

    border: 2px solid var(--gray-400);
    border-radius: 5px;

    margin: 2em;
    padding: 12px;

    .block {
        padding: 10px;
        border-bottom: 2px solid var(--gray-400);
        &:last-child {
            border-bottom: none;
        }

        pre {
            border: 1px solid var(--gray-400);
            border-radius: 5px;
            padding: 10px;
        }

        pre.small {
            width: fit-content;
        }

        pre,
        code {
            font-family: monospace;
            font-size: 13px;
            background-color: var(--background-100);
        }

        p.title,
        p.value {
            margin: 5px;
        }

        p.title {
            text-transform: capitalize;
            padding: 0px;
            color: var(--gray-900);
            text-wrap: nowrap;
        }

        .groupname {
            border: 1px solid var(--gray-400);
            border-radius: 5px;
            background-color: var(--gray-100);
            margin: 0.25em;
            padding: 0.25em 0.5em;
            display: inline-block;
        }
    }
}
</style>

<script lang="ts">
import { computed, effect, ref } from 'vue';

import { POLL_INTERVAL, type RegisteredDevice } from '../../common/utils';
import TitleBar from '../TitleBar.vue';
import { registeredDevicesResources } from './devices';
import { useRoute } from 'vue-router';

const MAC_ADDR_REGEX = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/;

export default {
    components: {
        TitleBar,
    },
    unmounted() {
        if (this.interval !== null) clearInterval(this.interval);
    },
    setup() {
        const route = useRoute();
        const interval = ref<number | null>(null);

        registeredDevicesResources.fetchResources();
        interval.value = setInterval(
            () => registeredDevicesResources.fetchResources(),
            POLL_INTERVAL,
        );

        // Parse the route and find the relavant device. The id can be one of:
        //   * MAC address
        //   * URL-encoded device name
        //   * Device id from the RDFM Management Server
        // If there are 2 matches then the order above applies (e.g. MAC Address is prioritized over device name)
        const routeId = route.params.id.toString();
        const device = ref<RegisteredDevice>();
        const pattern = ref<string>();
        effect(() => {
            if (!registeredDevicesResources.resources.value) return;

            let foundDevice: RegisteredDevice | undefined;
            let foundPattern;

            if (routeId.match(MAC_ADDR_REGEX)) {
                foundDevice = registeredDevicesResources.resources.value.find(
                    (d) => d.mac_address == routeId,
                );
                foundPattern = 'MAC address';
            } else {
                foundDevice = registeredDevicesResources.resources.value.find(
                    (d) => d.name == decodeURIComponent(routeId),
                );
                foundPattern = 'name';
            }

            if (!foundDevice) {
                foundDevice = registeredDevicesResources.resources.value.find(
                    (d) => d.id == Number(routeId),
                );
                foundPattern = 'id';
            }

            device.value = foundDevice;
            pattern.value = foundPattern;
        });

        const devicesLoaded = computed(() => !!registeredDevicesResources.resources.value);

        return {
            id: route.params.id,
            interval,
            devicesLoaded,
            device,
            pattern,
        };
    },
};
</script>
