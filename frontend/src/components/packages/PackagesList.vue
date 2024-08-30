<template>
    <Transition>
        <BlurPanel v-if="removalPopupOpen" @click.self="resetPopups">
            <div class="popup">
                <div class="header">
                    <p class="title">Are you absolutely sure?</p>
                    <p class="description">
                        This action cannot be undone. It will permanently delete package #{{ packageToRemove }} from RDFM application
                    </p>
                </div>
                <div class="body">
                    <div class="buttons">
                        <button class="action-button gray" @click="removalPopupOpen = false">Cancel</button>
                        <button class="action-button red-fill" @click="removePackage">Remove</button>
                    </div>
                </div>
            </div>
        </BlurPanel>
    </Transition>

    <Transition>
        <BlurPanel v-if="additionPopupOpen" @click.self="resetPopups">
            <div class="popup">
                <div class="header">
                    <p class="title">Upload a new package</p>
                    <p class="description">
                        Configure the package by choosing an appropriate file and filling in the required fields
                    </p>
                </div>
                <div class="body">
                    <div class="entry">
                        <p>Version</p>
                        <input type="text" v-model="packageUploadData.packageVersion" placeholder="1.0" />
                    </div>
                    <div class="entry">
                        <p>Device type</p>
                        <input type="text" v-model="packageUploadData.deviceType" placeholder="Robot" />
                    </div>
                    <div class="entry">
                        <p>File</p>
                        <input type="file" ref="uploadedPackageFile" />
                    </div>

                    <div class="buttons">
                        <button class="action-button gray" @click="additionPopupOpen = false">Cancel</button>
                        <button class="action-button blue white" @click="uploadPackage">Upload</button>
                    </div>
                </div>
            </div>
        </BlurPanel>
    </Transition>

    <TitleBar
        title="Packages"
        subtitle="manage your packages"
        actionButtonName="Create new package"
        :buttonCallback="() => additionPopupOpen = true"
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
                    <button class="action-button red" @click="clickRemovePackage(parseInt(pckg.ID))">
                        Remove
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

.popup {
    z-index: 10;
    position: absolute;
    background-color: var(--background-200);
    border: 2px solid var(--gray-400);
    border-radius: 10px;
    color: var(--gray-1000);

    left: 50vw;
    top: 50vh;
    transform: translate(-50%, -50%);
    padding: 2em;
    width: 40vh;

    & > .header {
        font-family: 'Inter', sans-serif;

        & > .title {
            font-size: 1.5em;
            margin: 0;
        }

        & > .description {
            color: var(--gray-900);
            font-family: 'Inter', sans-serif;
            font-size: 1em;
        }
    }

    & > .body {
        display: flex;
        flex-direction: column;
        gap: 1em;

        & > .entry {
            & > p {
                margin: 0 0 0.2em 0;
                font-size: 0.75em;
            }

            & > input {
                background-color: var(--gray-100);
                border: 1px solid var(--gray-400);
                border-radius: 5px;

                box-sizing: border-box;
                padding: 0.75em;
                width: 100%;
                color: var(--gray-1000);

                &::file-selector-button {
                    border: none;
                    border-right: 1px solid var(--gray-400);
                    margin-right: 0.5em;
                    cursor: pointer;

                    background-color: var(--gray-100);
                    color: var(--accent-900);
                }
            }
        }

        & > .buttons {
            display: flex;
            flex-direction: row;
            justify-content: space-between;
        }
    }
}


.v-enter-active,
.v-leave-active {
  transition: opacity 0.25s ease;
}

.v-enter-from,
.v-leave-to {
  opacity: 0;
}

</style>

<script lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue';
import { type Ref } from 'vue';
import BlurPanel from '../BlurPanel.vue';

import {
    PACKAGES_ENDPOINT,
    POLL_INTERVAL,
    DELETE_PACKAGE_ENDPOINT,
    resourcesGetter,
    HTTPStatus,
} from '../../common/utils';
import { type Package } from '../../common/utils';
import TitleBar from '../TitleBar.vue';

export default {
    components: {
        TitleBar,
        BlurPanel,
    },
    setup() {
        const packageResources = resourcesGetter<Package[]>(PACKAGES_ENDPOINT);
        const packageUploadData = reactive({
            packageVersion: '',
            deviceType: '',
        });
        let intervalID: undefined | number = undefined;
        const packageToRemove: Ref<number | null> = ref(null);

        const removalPopupOpen: Ref<boolean> = ref(false);
        const additionPopupOpen: Ref<boolean> = ref(false);
        const resetPopups = () => {
            removalPopupOpen.value = false;
            additionPopupOpen.value = false;
        }

        const uploadedPackageFile: Ref<HTMLInputElement | null> = ref(null);

        const clickRemovePackage = async (packageId: number) => {
            packageToRemove.value = packageId;
            removalPopupOpen.value = true;
        };

        const removePackage = async () => {
            const [success, status] = await packageResources.fetchDELETE(
                DELETE_PACKAGE_ENDPOINT(packageToRemove.value!),
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

            packageToRemove.value = null;
            removalPopupOpen.value = false;
        }

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

            additionPopupOpen.value = false;
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


        return {
            clickRemovePackage,
            removePackage,
            uploadPackage,
            pollingStatus: packageResources.pollingStatus,
            packageUploadData,
            packages: parsedPackages,
            uploadedPackageFile,
            packagesCount,
            removalPopupOpen,
            packageToRemove,
            additionPopupOpen,
            resetPopups,
        };
    },
};
</script>
