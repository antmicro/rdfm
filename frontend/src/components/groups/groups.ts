/*
 * Copyright (c) 2024 Antmicro <www.antmicro.com>
 *
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * Module containing wrappers for sending requests related to groups,
 * that return an appropriate message based on documentation.
 */

import {
    ASSIGN_PACKAGE_IN_GROUP_ENDPOINT,
    DELETE_GROUP_ENDPOINT,
    DEVICES_ENDPOINT,
    GROUPS_ENDPOINT,
    PACKAGES_ENDPOINT,
    PATCH_DEVICES_IN_GROUP_ENDPOINT,
    resourcesGetter,
    UPDATE_GROUP_PRIORITY_ENDPOINT,
    type Group,
    type Package,
    type RegisteredDevice,
    type RequestOutput,
} from '../../common/utils';

import { StatusCodes } from 'http-status-codes';

export type InitialGroupConfiguration = {
    id: number;
    priority: number;
    devices: number[];
    packages: number[];
};

export type GroupConfiguration = {
    id: number | null;
    priority: number | null;
    devices: number[] | null;
    packages: number[] | null;
};

export type NewGroupData = {
    name: string | null;
    description: string | null;
    priority: number | null;
};

const headers = (() => {
    const headers = new Headers();
    headers.set('Content-type', 'application/json');
    headers.set('Accept', 'application/json, text/javascript');
    return headers;
})();

export const groupResources = resourcesGetter<Group[]>(GROUPS_ENDPOINT);
export const packagesResources = resourcesGetter<Package[]>(PACKAGES_ENDPOINT);
export const devicesResources = resourcesGetter<RegisteredDevice[]>(DEVICES_ENDPOINT);

export const findPackage = (packageId: number) => {
    if (packagesResources.resources.value === undefined) return 'NOT FOUND';

    const pckg = packagesResources.resources.value.find((pckg) => pckg.id === packageId);
    return pckg!.id;
};

export const findDevice = (deviceId: number) => {
    if (devicesResources.resources.value === undefined) return 'NOT FOUND';

    const device = devicesResources.resources.value.find((device) => device.id === deviceId);
    return device!.mac_address;
};

/**
 * Request specified in
 * https://antmicro.github.io/rdfm/api.html#patch--api-v2-groups-(int-identifier)-devices
 */
export const patchDevicesRequest = async (
    groupId: number,
    addedDevices: number[],
    removedDevices: number[],
): Promise<RequestOutput> => {
    const body = JSON.stringify({
        add: addedDevices,
        remove: removedDevices,
    });

    const out = await groupResources.fetchPATCH(
        PATCH_DEVICES_IN_GROUP_ENDPOINT(groupId),
        headers,
        body,
    );
    if (!out.success) {
        switch (out.code) {
            case StatusCodes.UNAUTHORIZED:
                return {
                    success: false,
                    message:
                        'User did not provide authorization data, or the authorization has expired',
                };
            case StatusCodes.FORBIDDEN:
                return {
                    success: false,
                    message: 'User was authorized, but did not have permission to delete groups',
                };
            case StatusCodes.NOT_FOUND:
                return { success: false, message: 'Group does not exist' };
            case StatusCodes.CONFLICT:
                return {
                    success: false,
                    message:
                        '<p>One of the conflict described below has occurred</p><ul>' +
                        '<li> Any device identifier which does not match a registered device</li>' +
                        '<li> Any device identifier in additions which already has an assigned group which has the same priority as the group specified by identifier (even if the group is the same as specified by identifier</li>' +
                        '<li> Any device identifier in removals which is not currently assigned to the specified group</li></ul>',
                };
            default:
                return {
                    success: false,
                    message: 'Failed to update group devices. Got a response code of ' + out.code,
                };
        }
    }
    await groupResources.fetchResources();
    return { success: true };
};

/**
 * Request specified in
 * https://antmicro.github.io/rdfm/api.html#post--api-v2-groups-(int-identifier)-package
 */
export const updatePackagesRequest = async (
    groupId: number,
    packages: number[],
): Promise<RequestOutput> => {
    const body = JSON.stringify({
        packages,
    });

    const out = await groupResources.fetchPOST(
        ASSIGN_PACKAGE_IN_GROUP_ENDPOINT(groupId),
        headers,
        body,
    );
    if (!out.success) {
        switch (out.code) {
            case StatusCodes.BAD_REQUEST:
                return { success: false, message: 'Invalid request schema' };
            case StatusCodes.UNAUTHORIZED:
                return {
                    success: false,
                    message:
                        'User did not provide authorization data, or the authorization has expired',
                };
            case StatusCodes.FORBIDDEN:
                return {
                    success: false,
                    message: 'User was authorized, but did not have permission to assign packages',
                };
            case StatusCodes.CONFLICT:
                return {
                    success: false,
                    message: 'The package/group was modified or deleted during the operation',
                };
            case StatusCodes.NOT_FOUND:
                return { success: false, message: 'The specified package or group does not exist' };
            default:
                return {
                    success: false,
                    message: 'Failed to update group packages. Got a response code of ' + out.code,
                };
        }
    }
    await groupResources.fetchResources();
    return { success: true };
};

/**
 * Request specified in
 * https://antmicro.github.io/rdfm/api.html#post--api-v2-groups-(int-identifier)-priority
 */
export const updatePriorityRequest = async (
    groupId: number,
    priority: number,
): Promise<RequestOutput> => {
    const body = JSON.stringify({
        priority: priority,
    });

    const out = await groupResources.fetchPOST(
        UPDATE_GROUP_PRIORITY_ENDPOINT(groupId),
        headers,
        body,
    );
    if (!out.success) {
        switch (out.code) {
            case StatusCodes.UNAUTHORIZED:
                return {
                    success: false,
                    message:
                        'User did not provide authorization data, or the authorization has expired',
                };
            case StatusCodes.FORBIDDEN:
                return {
                    success: false,
                    message: 'User was authorized, but did not have permission to modify groups',
                };
            case StatusCodes.CONFLICT:
                return {
                    success: false,
                    message:
                        'At least one device which is assigned to this group is also assigned to another group with the requested priority',
                };
            case StatusCodes.NOT_FOUND:
                return { success: false, message: 'The specified group does not exist' };
            default:
                return {
                    success: false,
                    message: 'Failed to update group priority. Got a response code of ' + out.code,
                };
        }
    }
    await groupResources.fetchResources();
    return { success: true };
};

/**
 * Request specified in
 * https://antmicro.github.io/rdfm/api.html#post--api-v2-groups
 */
export const addGroupRequest = async (newGroup: NewGroupData): Promise<RequestOutput> => {
    const errors = new Map();

    if (!newGroup.name) errors.set('name', 'No group name provided');
    if (!newGroup.description) errors.set('description', 'No group description provided');
    if (!newGroup.priority) errors.set('priority', 'No group priority provided');

    if (errors.size > 0) {
        return { success: false, errors };
    }

    const body = JSON.stringify({
        priority: newGroup.priority!,
        metadata: {
            'rdfm.group.name': newGroup.name!,
            'rdfm.group.description': newGroup.description!,
        },
    });

    const out = await groupResources.fetchPOST(GROUPS_ENDPOINT, headers, body);
    if (!out.success) {
        switch (out.code) {
            case StatusCodes.UNAUTHORIZED:
                return {
                    success: false,
                    message:
                        'User did not provide authorization data, or the authorization has expired',
                    errors,
                };
            case StatusCodes.FORBIDDEN:
                return {
                    success: false,
                    message: 'User was authorized, but did not have permission to create groups',
                    errors,
                };
            case StatusCodes.NOT_FOUND:
                return { success: false, message: 'The specified group does not exist' };
            default:
                return {
                    success: false,
                    message: 'Failed to create a group. Got a response code of ' + out.code,
                    errors,
                };
        }
    }
    await groupResources.fetchResources();
    return { success: true, errors };
};

/**
 * Request specified in
 * https://antmicro.github.io/rdfm/api.html#delete--api-v2-groups-(int-identifier)
 */
export const removeGroupRequest = async (groupId: number): Promise<RequestOutput> => {
    const out = await groupResources.fetchDELETE(DELETE_GROUP_ENDPOINT(groupId));
    if (!out.success) {
        switch (out.code) {
            case StatusCodes.UNAUTHORIZED:
                return {
                    success: false,
                    message:
                        'User did not provide authorization data, or the authorization has expired',
                };
            case StatusCodes.FORBIDDEN:
                return {
                    success: false,
                    message: 'User was authorized, but did not have permission to delete groups',
                };
            case StatusCodes.CONFLICT:
                return {
                    success: false,
                    message: 'At least one device is still assigned to the group',
                };
            case StatusCodes.NOT_FOUND:
                return { success: false, message: 'The specified group does not exist' };
            default:
                return {
                    success: false,
                    message: 'Failed to remove a group. Got a response code of ' + out.code,
                };
        }
    }
    await groupResources.fetchResources();
    return { success: true };
};
