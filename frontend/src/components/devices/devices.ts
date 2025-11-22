/*
 * Copyright (c) 2024-2025 Antmicro <www.antmicro.com>
 *
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * Module containing wrappers for sending requests related to devices,
 * that return an appropriate message based on documentation.
 */

import {
    DEVICE_ACTIONS_ENDPOINT,
    DEVICE_ACTIONS_EXEC_ENDPOINT,
    DEVICE_ACTION_LOG_ENDPOINT,
    DEVICES_ENDPOINT,
    GROUPS_ENDPOINT,
    PENDING_ENDPOINT,
    REGISTER_DEVICE_ENDPOINT,
    DELETE_DEVICE_ENDPOINT,
    DEVICE_TAGS_ENDPOINT,
    DEVICE_ADD_TAG_ENDPOINT,
    TAGS_ENDPOINT,
    DEVICE_DOWNLOAD_FILE_ENDPOINT,
    resourcesGetter,
    fetchWrapper,
    type Group,
    type PendingDevice,
    type RegisteredDevice,
    type RequestOutput,
} from '../../common/utils';

import { StatusCodes } from 'http-status-codes';
import { reactive } from 'vue';

export const pendingDevicesResources = resourcesGetter<PendingDevice[]>(PENDING_ENDPOINT);
export const registeredDevicesResources = resourcesGetter<RegisteredDevice[]>(DEVICES_ENDPOINT);
export const groupResources = resourcesGetter<Group[]>(GROUPS_ENDPOINT);

export const filteredDevicesResources = (tag: string) =>
    resourcesGetter<RegisteredDevice[]>(TAGS_ENDPOINT(tag));

export const deviceUpdates = reactive(new Map<string, number>());
export const deviceVersions = reactive(new Map<string, string>());

export type Action = {
    action_id: string;
    action_name: string;
    command: string[];
    description: string;
};

/**
 * Request specified in
 * https://antmicro.github.io/rdfm/api.html#post--api-v1-auth-register
 */
export const registerDeviceRequest = async (
    mac_address: string,
    public_key: string,
): Promise<RequestOutput> => {
    const body = JSON.stringify({
        mac_address,
        public_key,
    });

    const headers = new Headers();
    headers.set('Content-type', 'application/json');
    headers.set('Accept', 'application/json, text/javascript');

    const out = await pendingDevicesResources.fetchPOST(REGISTER_DEVICE_ENDPOINT, headers, body);

    if (!out.success) {
        switch (out.code) {
            case StatusCodes.UNAUTHORIZED:
                return {
                    success: false,
                    message:
                        'User did not provide authorization data, or the authorization has expired.',
                };
            case StatusCodes.FORBIDDEN:
                return {
                    success: false,
                    message:
                        'User was authorized, but did not have permission to change device registration status',
                };
            case StatusCodes.NOT_FOUND:
                return {
                    success: false,
                    message: 'The specified registration request does not exist',
                };
            default:
                return {
                    success: false,
                    message: 'Failed to register device. Got a response code of ' + out.code,
                };
        }
    }
    await pendingDevicesResources.fetchResources();
    await registeredDevicesResources.fetchResources();
    return { success: true };
};

export const removePendingDeviceRequest = async (
    mac_address: string,
    public_key: string,
): Promise<RequestOutput> => {
    const body = JSON.stringify({
        mac_address,
        public_key,
    });

    const headers = new Headers();
    headers.set('Content-type', 'application/json');
    headers.set('Accept', 'application/json, text/javascript');

    const out = await fetchWrapper(PENDING_ENDPOINT, 'DELETE', headers, body);

    if (!out.success) {
        return {
            success: false,
            message: 'Failed to execute action. Got a response code of ' + out.code,
        };
    }

    await pendingDevicesResources.fetchResources();
    await registeredDevicesResources.fetchResources();
    return { success: true };
};

export const removeDeviceRequest = async (identifier: number): Promise<RequestOutput> => {
    const body = JSON.stringify({});

    const headers = new Headers();
    headers.set('Content-type', 'application/json');
    headers.set('Accept', 'application/json, text/javascript');

    const out = await fetchWrapper(DELETE_DEVICE_ENDPOINT(identifier), 'DELETE', headers, body);

    if (!out.success) {
        return {
            success: false,
            message: 'Failed to execute action. Got a response code of ' + out.code,
        };
    }

    await pendingDevicesResources.fetchResources();
    await registeredDevicesResources.fetchResources();
    return { success: true };
};

export const execAction = async (macAddress: string, actionId: string) => {
    const out = await registeredDevicesResources.fetchGET(
        DEVICE_ACTIONS_EXEC_ENDPOINT(macAddress, actionId),
    );

    if (!out.success) {
        return {
            success: false,
            message: 'Failed to execute action. Got a response code of ' + out.code,
        };
    }

    return {
        success: true,
        data: out.data,
    };
};

export const getDeviceActions = async (macAddress: string) => {
    const out = await registeredDevicesResources.fetchGET(DEVICE_ACTIONS_ENDPOINT(macAddress));

    if (!out.success) {
        return {
            success: false,
            message: 'Failed to obtain device actions. Got a response code of ' + out.code,
        };
    }

    return {
        success: true,
        data: out.data as Action[],
    };
};

export const getDeviceTags = async (identifier: number) => {
    const out = await registeredDevicesResources.fetchGET(DEVICE_TAGS_ENDPOINT(identifier));

    if (!out.success) {
        return {
            success: false,
            message: 'Failed to obtain device tags. Got a response code of ' + out.code,
        };
    }

    return {
        success: true,
        data: out.data as string[],
    };
};

export const getDeviceActionLog = async (macAddress: string) => {
    const out = await registeredDevicesResources.fetchGET(DEVICE_ACTION_LOG_ENDPOINT(macAddress));

    if (!out.success) {
        return {
            success: false,
            message: 'Failed to obtain device action log. Got a response code of ' + out.code,
        };
    }

    return {
        success: true,
        data: out.data as Action[],
    };
};

export const clearDeviceActionLog = async (macAddress: string) => {
    const body = JSON.stringify({});

    const headers = new Headers();
    headers.set('Content-type', 'application/json');
    headers.set('Accept', 'application/json, text/javascript');

    const out = await fetchWrapper(DEVICE_ACTION_LOG_ENDPOINT(macAddress), 'DELETE', headers, body);

    if (!out.success) {
        return {
            success: false,
            message: 'Failed to clear device action log. Got a response code of ' + out.code,
        };
    }

    return { success: true };
};

export const downloadDeviceFile = async (identifier: number, file: string) => {
    const body = JSON.stringify({ file });

    const headers = new Headers();
    headers.set('Content-type', 'application/json');
    headers.set('Accept', 'application/json, text/javascript');

    const out = await fetchWrapper(
        DEVICE_DOWNLOAD_FILE_ENDPOINT(identifier),
        'POST',
        headers,
        body,
    );

    if (!out.success) {
        return {
            success: false,
            message: 'Failed to download file. Got a response code of ' + out.code,
        };
    }

    if (out.data.status !== 0) {
        return {
            success: false,
            message: 'Failed to download file. It does not exist.',
        };
    }

    window.open(out.data.url);
    return { success: true };
};
