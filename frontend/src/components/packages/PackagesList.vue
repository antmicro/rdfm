<!--
Copyright (c) 2024-2025 Antmicro <www.antmicro.com>

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
                        <div v-if="validationErrors.get('version')" class="errors">
                            <p>{{ validationErrors.get('version') }}</p>
                        </div>
                    </div>
                    <div class="entry">
                        <p>Device type</p>
                        <input
                            type="text"
                            v-model="packageUploadData.deviceType"
                            placeholder="Robot"
                        />
                        <div v-if="validationErrors.get('deviceType')" class="errors">
                            <p>{{ validationErrors.get('deviceType') }}</p>
                        </div>
                    </div>
                    <div class="entry">
                        <p>File</p>
                        <input type="file" ref="uploadedPackageFile" />
                        <div v-if="validationErrors.get('file')" class="errors">
                            <p>{{ validationErrors.get('file') }}</p>
                        </div>
                    </div>

                    <div class="buttons">
                        <button
                            :disabled="uploadInProgress"
                            class="action-button gray"
                            @click="closeAddPackagePopup"
                        >
                            Cancel
                        </button>
                        <button
                            :disabled="uploadInProgress"
                            class="action-button blue white"
                            @click="uploadPackage"
                        >
                            Upload
                        </button>
                    </div>

                    <div v-if="uploadInProgress" class="progress-bar">
                        <span></span>
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
        <div class="resources-table-wrapper checked">
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
                <table class="resources-table packages">
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
                                <div class="buttons">
                                    <div class="drdn-wrapper" style="position: relative">
                                        <button id="main-button" class="action-button gray">
                                            Download
                                            <span class="caret-down"> <CaretDown /> </span>
                                            <span class="caret-up"> <CaretUp /> </span>
                                        </button>
                                        <div class="drdn">
                                            <button
                                                class="action-button gray"
                                                @click="
                                                    (e) =>
                                                        download(pckg.id).then(() =>
                                                            (e.target as HTMLElement).blur(),
                                                        )
                                                "
                                            >
                                                <svg
                                                    width="20"
                                                    height="20"
                                                    viewBox="1 1 17 17"
                                                    xmlns="http://www.w3.org/2000/svg"
                                                >
                                                    <path
                                                        d="M10 13L6 9L7.0625 7.9375L9.25 10.125V3H10.75V10.125L12.9375 7.9375L14 9L10 13ZM5.49417 16C5.08139 16 4.72917 15.8531 4.4375 15.5594C4.14583 15.2656 4 14.9125 4 14.5V13H5.5V14.5H14.5V13H16V14.5C16 14.9125 15.8531 15.2656 15.5592 15.5594C15.2653 15.8531 14.9119 16 14.4992 16H5.49417Z"
                                                    />
                                                </svg>
                                                Direct download
                                            </button>
                                            <button
                                                class="action-button gray"
                                                @click="
                                                    (e) =>
                                                        copyDownloadLink(pckg.id).then(() =>
                                                            (e.target as HTMLElement).blur(),
                                                        )
                                                "
                                            >
                                                <svg
                                                    width="20"
                                                    height="20"
                                                    viewBox="1 1 17 17"
                                                    fill="none"
                                                    xmlns="http://www.w3.org/2000/svg"
                                                >
                                                    <path
                                                        d="M9 14H6C4.89333 14 3.95 13.6095 3.17 12.8285C2.39 12.0477 2 11.1033 2 9.99521C2 8.88729 2.39 7.94444 3.17 7.16667C3.95 6.38889 4.89333 6 6 6H9V7.5H6C5.30556 7.5 4.71528 7.74306 4.22917 8.22917C3.74306 8.71528 3.5 9.30556 3.5 10C3.5 10.6944 3.74306 11.2847 4.22917 11.7708C4.71528 12.2569 5.30556 12.5 6 12.5H9V14ZM7 10.75V9.25H13V10.75H7ZM11 14V12.5H14C14.6944 12.5 15.2847 12.2569 15.7708 11.7708C16.2569 11.2847 16.5 10.6944 16.5 10C16.5 9.30556 16.2569 8.71528 15.7708 8.22917C15.2847 7.74306 14.6944 7.5 14 7.5H11V6H14C15.1067 6 16.05 6.39049 16.83 7.17146C17.61 7.95229 18 8.89674 18 10.0048C18 11.1127 17.61 12.0556 16.83 12.8333C16.05 13.6111 15.1067 14 14 14H11Z"
                                                    />
                                                </svg>
                                                Copy link
                                            </button>
                                        </div>
                                    </div>
                                    <button
                                        class="action-button red"
                                        @click="openRemovePackagePopup(pckg.id)"
                                    >
                                        Remove
                                    </button>
                                </div>
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
    padding-top: 0em;

    & > p {
        color: var(--gray-1000);
        font-size: 1.5em;
    }
}

@supports (-moz-box-align: unset) {
    table.resources-table.packages .entry:has(.buttons) {
        width: 100vw;
    }
}

table.resources-table.packages {
    width: fit-content;
    overflow-x: unset;

    &:has(.resources-table-row:nth-last-child(2) .buttons:focus-within) {
        margin-bottom: 30px;
    }

    &:has(.resources-table-row:last-child .buttons:focus-within) {
        margin-bottom: 130px;
    }
}

/* Default state */
.drdn-wrapper {
    user-select: none;
    position: relative;
    display: inline-block;

    .caret-up,
    .caret-down {
        display: inline-block;
    }

    .caret-up {
        display: none;
    }

    .drdn {
        display: none;

        color: var(--gray-1000);
        background-color: var(--gray-100);
        border: 2px solid var(--gray-400);
        border-radius: 5px;

        position: absolute;
        top: 100%;
        right: 5px;
        width: max-content;
        z-index: 100;

        padding: 0px;
        padding-top: 10px;
        padding-bottom: 10px;

        .action-button {
            margin: 0px !important;
            width: 100%;
            border: 0px;
            display: flex;
            align-items: center;
            text-align: left;
            color: var(--gray-900);

            &:hover {
                color: var(--gray-1000);

                svg {
                    fill: var(--gray-1000);
                }
            }

            svg {
                margin-right: 10px;
                fill: var(--gray-900);
            }
        }
    }

    #main-button {
        cursor: pointer;
    }
}

/* Focused state */
.drdn-wrapper:focus-within {
    .caret-up {
        display: inline-block;
    }

    .caret-down {
        display: none;
    }

    #main-button {
        pointer-events: none;
        cursor: pointer;
        color: var(--gray-900);
    }

    .drdn {
        display: block;
    }
}

.buttons {
    button {
        margin: 5px !important;
        width: 130px;
    }
}
</style>

<script lang="ts">
import { computed, onMounted, onUnmounted, ref, type Ref, reactive, type Reactive } from 'vue';

import { POLL_INTERVAL, useNotifications } from '../../common/utils';
import BlurPanel from '../BlurPanel.vue';
import RemovePopup from '../RemovePopup.vue';
import TitleBar from '../TitleBar.vue';
import {
    packageResources,
    removePackageRequest,
    uploadPackageRequest,
    downloadPackageRequest,
    type NewPackageData,
} from './packages';
import CaretDown from '@/images/CaretDown.vue';
import CaretUp from '@/images/CaretUp.vue';

export enum PackagePopupOpen {
    AddPackage,
    RemovePackage,
    None,
}

export default {
    components: {
        BlurPanel,
        RemovePopup,
        TitleBar,
        CaretDown,
        CaretUp,
    },
    setup() {
        let intervalID: undefined | number = undefined;

        const notifications = useNotifications();

        const popupOpen = ref(PackagePopupOpen.None);

        // =======================
        // Add package functionality
        // =======================
        const uploadInProgress = ref(false);
        const uploadedPackageFile: Ref<HTMLInputElement | null> = ref(null);
        const packageUploadData: Reactive<NewPackageData> = reactive({
            version: null,
            deviceType: null,
        });

        const validationErrors = reactive<Map<string, string>>(new Map());

        const openAddPackagePopup = () => {
            popupOpen.value = PackagePopupOpen.AddPackage;
        };

        const closeAddPackagePopup = () => {
            packageUploadData.version = null;
            packageUploadData.deviceType = null;
            popupOpen.value = PackagePopupOpen.None;
            uploadInProgress.value = false;
            validationErrors.clear();
        };

        const uploadPackage = async () => {
            uploadInProgress.value = true;

            try {
                validationErrors.clear();

                const { success, message, errors } = await uploadPackageRequest(
                    uploadedPackageFile.value!,
                    packageUploadData,
                );

                if (errors) {
                    for (let [field, error] of errors) {
                        validationErrors.set(field, error);
                    }
                }

                if (!success) {
                    notifications.notifyError({
                        headline: 'Error when uploading package',
                        msg: message || 'Uploading package failed',
                    });
                } else {
                    notifications.notifySuccess({ headline: `Package was uploaded` });
                    closeAddPackagePopup();
                }
            } finally {
                uploadInProgress.value = false;
            }
        };

        // =======================
        // Remove package functionality
        // =======================
        const packageToRemove: Ref<number | null> = ref(null);

        const openRemovePackagePopup = async (packageId: number) => {
            packageToRemove.value = packageId;
            popupOpen.value = PackagePopupOpen.RemovePackage;
        };

        const closeRemovePackagePopup = () => {
            packageToRemove.value = null;
            popupOpen.value = PackagePopupOpen.None;
        };

        const removePackage = async () => {
            const { success, message } = await removePackageRequest(packageToRemove.value!);
            if (!success) {
                notifications.notifyError({
                    headline: 'Error when removing package:',
                    msg: message || 'Removing package failed',
                });
            } else {
                notifications.notifySuccess({ headline: 'Package was removed' });
            }
            closeRemovePackagePopup();
        };

        // =======================
        // Download package functionality
        // =======================

        const getPackageDownloadUrl = async (packageId: number) => {
            const { success, message } = await downloadPackageRequest(packageId);
            if (!success || !message) {
                notifications.notifyError({
                    headline: 'Error when downloading the package:',
                    msg: message || 'Could not get the download link',
                });
                throw new Error('Error when downloading the package');
            }
            return message;
        };

        const download = (packageId: number) =>
            getPackageDownloadUrl(packageId).then((url) => window.open(url));

        const copyDownloadLink = async (packageId: number) => {
            const downloadUrl = await getPackageDownloadUrl(packageId);
            navigator.clipboard.writeText(downloadUrl);
            notifications.notifySuccess({ headline: 'Download link copied!' });
        };

        // =======================

        onMounted(async () => {
            await packageResources.fetchResources();

            if (intervalID === undefined) {
                intervalID = setInterval(packageResources.fetchResources, POLL_INTERVAL);
            }
        });

        onUnmounted(() => {
            uploadInProgress.value = false;

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
            validationErrors,
            packages: packageResources.resources,
            uploadedPackageFile,
            packagesCount,
            popupOpen,
            uploadInProgress,
            packageToRemove,
            closeAddPackagePopup,
            closeRemovePackagePopup,
            openAddPackagePopup,
            copyDownloadLink,
            download,
        };
    },
};
</script>
