<template>
    <div class="drdn-wrapper">
        <button
            id="main-button"
            :class="[
                { 'action-button': !smallButton },
                { gray: !smallButton },
                { small: smallButton },
            ]"
        >
            <template v-if="smallButton">
                <Dots />
            </template>
            <template v-else>
                Download
                <span class="caret-down"> <CaretDown /> </span>
                <span class="caret-up"> <CaretUp /> </span>
            </template>
        </button>
        <div :class="['drdn', { 'inside-list': smallButton }]">
            <button class="action-button gray" @click="download">
                <svg width="20" height="20" viewBox="1 1 17 17" xmlns="http://www.w3.org/2000/svg">
                    <path
                        d="M10 13L6 9L7.0625 7.9375L9.25 10.125V3H10.75V10.125L12.9375 7.9375L14 9L10 13ZM5.49417 16C5.08139 16 4.72917 15.8531 4.4375 15.5594C4.14583 15.2656 4 14.9125 4 14.5V13H5.5V14.5H14.5V13H16V14.5C16 14.9125 15.8531 15.2656 15.5592 15.5594C15.2653 15.8531 14.9119 16 14.4992 16H5.49417Z"
                    />
                </svg>
                Direct download
            </button>
            <button class="action-button gray" @click="copyDownloadLink">
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
</template>

<style scoped>
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

    .inside-list {
        top: -200%;
        right: 100%;
    }

    #main-button {
        cursor: pointer;
    }

    .small {
        border: 0;
        border-radius: 8px;
        padding: 1em;
        background-color: transparent;

        display: flex;
        justify-content: center;
        align-items: center;

        svg {
            width: 15px;
            fill: var(--gray-900);
        }

        &:hover {
            background-color: var(--gray-500);
        }
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
</style>

<script lang="ts">
import { defineComponent, computed } from 'vue';
import { downloadPackageRequest } from './packages/packages';
import { useNotifications } from '../common/utils';
import CaretDown from '@/images/CaretDown.vue';
import CaretUp from '@/images/CaretUp.vue';
import Dots from './icons/Dots.vue';

export default defineComponent({
    components: {
        CaretDown,
        CaretUp,
        Dots,
    },
    props: {
        resource: {
            type: Number,
        },
        url: {
            type: String,
        },
        smallButton: {
            type: Boolean,
            default: false,
        },
    },
    setup(props) {
        const notifications = useNotifications();

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

        const download = (e: Event) => {
            if (props.resource) {
                getPackageDownloadUrl(props.resource).then((url) => window.open(url));
            } else if (props.url) {
                window.open(props.url);
            }
            (e.target as HTMLElement).blur();
        };

        const copyDownloadLink = async (e: Event) => {
            const link = props.url ? props.url : await getPackageDownloadUrl(props.resource!);
            navigator.clipboard.writeText(link);
            notifications.notifySuccess({ headline: 'Download link copied!' });
            (e.target as HTMLElement).blur();
        };

        return { download, copyDownloadLink };
    },
});
</script>
