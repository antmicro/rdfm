<template>
    <TitleBar
        title="Packages"
        subtitle="manage your packages"
        actionButtonName="Create new package"
        :buttonCallback="createPackage"
    />

    <div class="container">
        <p>Overview</p>
        <table cellspacing="0" cellpadding="0" class="resources-table">
            <tr class="resources-table-row">
                <td class="entry">
                    <div class="value">Total packages</div>
                </td>
                <td class="entry">
                    <div class="value">{{ packagesCount }}</div>
                </td>
            </tr>
        </table>
        <p>Packages</p>
        <table cellspacing="0" cellpadding="0" class="resources-table">
            <tr v-for="pckg in packages" :key="pckg.ID" class="resources-table-row">
                <td v-for="[name, value] in Object.entries(pckg)" class="entry" :key="name">
                    <div class="title">{{ name }}</div>
                    <div class="value">{{ value }}</div>
                </td>
                <td class="entry">
                    <button class="action-button red" @click="deletePackage(parseInt(pckg.ID))">
                        Delete
                    </button>
                </td>
            </tr>
        </table>
    </div>
</template>

<style scoped>
.container {
    padding: 2em;

    & > p {
        color: var(--gray-1000);
        font-size: 1.5em;
    }
}
</style>

<script lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue';
import { type Ref } from 'vue';

import {
    PACKAGES_ENDPOINT,
    POLL_INTERVAL,
    DELETE_PACKAGE_ENDPOINT,
    resourcesGetter,
    HTTPStatus,
} from '../common/utils';
import { type Package } from '../common/utils';
import TitleBar from './TitleBar.vue';

export default {
    components: {
        TitleBar,
    },
    setup() {
        const packageResources = resourcesGetter<Package[]>(PACKAGES_ENDPOINT);
        const packageUploadData = reactive({
            packageVersion: '',
            deviceType: '',
        });
        let intervalID: undefined | number = undefined;

        const uploadedPackageFile: Ref<HTMLInputElement | null> = ref(null);

        const deletePackage = async (packageId: number) => {
            console.log(packageId);
            const [success, status] = await packageResources.fetchDELETE(
                DELETE_PACKAGE_ENDPOINT(packageId),
            );
            if (success) {
                await packageResources.fetchResources();
            } else {
                if (status === HTTPStatus.Conflict) {
                    alert(
                        'The package you are trying to remove is in a group and cannot be removed',
                    );
                } else {
                    console.error('Failed to delete package');
                }
            }
        };

        onMounted(async () => {
            await packageResources.fetchResources();

            if (intervalID === undefined) {
                intervalID = setInterval(async () => {
                    await packageResources.fetchResources();
                }, POLL_INTERVAL);
            }
        });

        onUnmounted(() => {
            if (intervalID !== undefined) {
                clearInterval(intervalID);
            }
        });

        const uploadPackage = async () => {
            const formData = new FormData();
            if (uploadedPackageFile.value === null || uploadedPackageFile.value.files === null) {
                return;
            }

            const file = uploadedPackageFile.value.files[0];
            // TODO: Validation for inputs should be performed
            formData.append('file', file);
            formData.append('rdfm.software.version', packageUploadData.packageVersion);
            formData.append('rdfm.hardware.devtype', packageUploadData.deviceType);

            const headers = new Headers();

            const [status] = await packageResources.fetchPOST(PACKAGES_ENDPOINT, headers, formData);
            if (status) {
                await packageResources.fetchResources();
            } else {
                console.error('Failed to upload package');
            }
        };

        const parsedPackages = computed(() => {
            const parsedState: Record<string, string>[] = [];
            packageResources.resources.value?.forEach((pckg) => {
                const newEntry: Record<string, string> = {
                    ID: pckg.id.toString(),
                    'Uploaded on': pckg.created,
                    SHA256: pckg.sha256,
                    'Storage driver': pckg.driver,
                };
                parsedState.push(newEntry);
            });
            return parsedState;
        });

        const packagesCount = computed(() => packageResources.resources.value?.length ?? 0);

        const createPackage = () => alert('TODO!');

        return {
            createPackage,
            deletePackage,
            uploadPackage,
            pollingStatus: packageResources.pollingStatus,
            packageUploadData,
            packages: parsedPackages,
            uploadedPackageFile,
            packagesCount,
        };
    },
};
</script>
