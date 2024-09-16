/*
 * Copyright (c) 2024 Antmicro <www.antmicro.com>
 *
 * SPDX-License-Identifier: Apache-2.0
 */

import {
    DEVICES_ENDPOINT,
    PENDING_ENDPOINT,
    REGISTER_DEVICE_ENDPOINT,
    resourcesGetter,
    type PendingDevice,
    type RegisteredDevice,
    type RequestOutput,
} from '../../common/utils';

import { StatusCodes } from 'http-status-codes';

export const pendingDevicesResources = resourcesGetter<PendingDevice[]>(PENDING_ENDPOINT);
export const registeredDevicesResources = resourcesGetter<RegisteredDevice[]>(DEVICES_ENDPOINT);

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
                    message:
                        'The specified registration request does not exist'
                }
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
