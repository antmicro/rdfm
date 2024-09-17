<!--
Copyright (c) 2024 Antmicro <www.antmicro.com>

SPDX-License-Identifier: Apache-2.0
-->

<!--
Component wraps functionality for displaying and working with rdfm packages.
-->

<template>
    <RemovePopup
        @click.self="closeRemovePackagePopup"
        title="Are you absolutely sure?"
        :enabled="popupOpen == 1"
        :description="`This action cannot be undone. It will permanently delete #${packageToRemove} package.`"
        :cancelCallback="closeRemovePackagePopup"
        :removeCallback="removePackage"
    />

    <Transition>
        <BlurPanel v-if="popupOpen == 0" @click.self="closeAddPackagePopup">
            <div class="popup">
                <div class="header">
                    <p class="title">Upload a new package</p>
                    <p class="description">
                        Configure the package by choosing an appropriate file and filling in the
                        required fields
                    </p>
                </div>
                <div class="body">
                    <div class="entry">
                        <p>Version</p>
                        <input type="text" v-model="packageUploadData.version" placeholder="1.0" />
                    </div>
                    <div class="entry">
                        <p>Device type</p>
                        <input
                            type="text"
                            v-model="packageUploadData.deviceType"
                            placeholder="Robot"
                        />
                    </div>
                    <div class="entry">
                        <p>File</p>
                        <input type="file" ref="uploadedPackageFile" />
                    </div>

                    <div class="buttons">
                        <button class="action-button gray" @click="closeAddPackagePopup">
                            Cancel
                        </button>
                        <button class="action-button blue white" @click="uploadPackage">
                            Upload
                        </button>
                    </div>
                </div>
            </div>
        </BlurPanel>
    </Transition>

    <TitleBar
        title="Packages"
        subtitle="manage your packages"
        actionButtonName="Create new package"
        :buttonCallback="openAddPackagePopup"
    />

    <div class="container">
        <p>Overview</p>
        <div class="resources-table-wrapper">
            <table class="resources-table">
                <tbody>
                    <tr class="resources-table-row">
                        <td class="entry">
                            <div class="value">Total packages</div>
                        </td>
                        <td class="entry">
                            <div class="value">{{ packagesCount }}</div>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        <template v-if="(packages?.length ?? 0) > 0">
            <p>Packages</p>
            <div class="resources-table-wrapper">
                <table class="resources-table">
                    <tbody>
                        <tr v-for="pckg in packages" :key="pckg.id" class="resources-table-row">
                            <td class="entry">
                                <div class="title">ID</div>
                                <div class="value">#{{ pckg.id }}</div>
                            </td>
                            <td class="entry">
                                <div class="title">Version</div>
                                <div class="value">
                                    {{ pckg.metadata['rdfm.software.version'] }}
                                </div>
                            </td>
                            <td class="entry">
                                <div class="title">Device type</div>
                                <div class="value">
                                    {{ pckg.metadata['rdfm.hardware.devtype'] }}
                                </div>
                            </td>
                            <td class="entry">
                                <div class="title">Uploaded on</div>
                                <div class="value">{{ pckg.created }}</div>
                            </td>
                            <td class="entry">
                                <div class="title">SHA256</div>
                                <div class="value">{{ pckg.sha256 }}</div>
                            </td>
                            <td class="entry">
                                <div class="title">Storage Driver</div>
                                <div class="value">{{ pckg.driver }}</div>
                            </td>
                            <!-- TODO: Display metadata of the package -->
                            <td class="entry">
                                <button
                                    class="action-button red"
                                    @click="openRemovePackagePopup(pckg.id)"
                                >
                                    Remove
                                </button>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </template>
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
import { computed, onMounted, onUnmounted, ref, type Ref, reactive, type Reactive } from 'vue';

import { POLL_INTERVAL } from '../../common/utils';
import BlurPanel from '../BlurPanel.vue';
import RemovePopup from '../RemovePopup.vue';
import TitleBar from '../TitleBar.vue';
import {
    packageResources,
    removePackageRequest,
    uploadPackageRequest,
    type NewPackageData,
} from './packages';

enum PopupOpen {
    AddPackage,
    RemovePackage,
    None,
}

export default {
    components: {
        BlurPanel,
        RemovePopup,
        TitleBar,
    },
    setup() {
        let intervalID: undefined | number = undefined;

        const popupOpen = ref(PopupOpen.None);

        // =======================
        // Add package functionality
        // =======================
        const uploadedPackageFile: Ref<HTMLInputElement | null> = ref(null);
        const packageUploadData: Reactive<NewPackageData> = reactive({
            version: null,
            deviceType: null,
        });

        const openAddPackagePopup = () => {
            popupOpen.value = PopupOpen.AddPackage;
        };

        const closeAddPackagePopup = () => {
            packageUploadData.version = null;
            packageUploadData.deviceType = null;
            popupOpen.value = PopupOpen.None;
        };

        const uploadPackage = async () => {
            const { success, message } = await uploadPackageRequest(
                uploadedPackageFile.value!,
                packageUploadData,
            );
            if (!success) {
                alert(message);
            } else {
                closeAddPackagePopup();
            }
        };

        // =======================
        // Remove package functionality
        // =======================
        const packageToRemove: Ref<number | null> = ref(null);

        const openRemovePackagePopup = async (packageId: number) => {
            packageToRemove.value = packageId;
            popupOpen.value = PopupOpen.RemovePackage;
        };

        const closeRemovePackagePopup = () => {
            packageToRemove.value = null;
            popupOpen.value = PopupOpen.None;
        };

        const removePackage = async () => {
            const { success, message } = await removePackageRequest(packageToRemove.value!);
            if (!success) {
                alert(message);
            } else {
                closeRemovePackagePopup();
            }
        };

        // =======================

        onMounted(async () => {
            await packageResources.fetchResources();

            if (intervalID === undefined) {
                intervalID = setInterval(packageResources.fetchResources, POLL_INTERVAL);
            }
        });

        onUnmounted(() => {
            if (intervalID !== undefined) {
                clearInterval(intervalID);
            }
        });

        const packagesCount = computed(() => packageResources.resources.value?.length ?? 0);

        return {
            openRemovePackagePopup,
            removePackage,
            uploadPackage,
            pollingStatus: packageResources.pollingStatus,
            packageUploadData,
            packages: packageResources.resources,
            uploadedPackageFile,
            packagesCount,
            popupOpen,
            packageToRemove,
            closeAddPackagePopup,
            closeRemovePackagePopup,
            openAddPackagePopup,
        };
    },
};
</script>
