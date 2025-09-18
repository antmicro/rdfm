/*
 * Copyright (c) 2024 Antmicro <www.antmicro.com>
 *
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * Module containing wrappers for sending requests related to packages,
 * that return an appropriate message based on documentation.
 */

import {
    DELETE_PACKAGE_ENDPOINT,
    DOWNLOAD_PACKAGE_ENDPOINT,
    GROUPS_ENDPOINT,
    PACKAGES_ENDPOINT,
    resourcesGetter,
    type Group,
    type Package,
    type RequestOutput,
    updatePermissions,
} from '../../common/utils';

import { StatusCodes } from 'http-status-codes';

export type NewPackageData = {
    version: string | null;
    deviceType: string | null;
};

export const packageResources = resourcesGetter<Package[]>(PACKAGES_ENDPOINT);
export const groupsResources = resourcesGetter<Group[]>(GROUPS_ENDPOINT);

/**
 * Request specified in
 * https://antmicro.github.io/rdfm/api.html#post--api-v1-packages
 */
export const uploadPackageRequest = async (
    uploadedPackageFile: HTMLInputElement,
    packageUploadData: NewPackageData,
): Promise<RequestOutput> => {
    const formData = new FormData();
    const errors = new Map();

    if ((uploadedPackageFile?.files ?? []).length <= 0) errors.set('file', 'No file provided');
    if (!packageUploadData.version) errors.set('version', 'No package version provided');
    if (!packageUploadData.deviceType) errors.set('deviceType', 'No device type provided');

    if (errors.size > 0) {
        return { success: false, errors };
    }

    const file = uploadedPackageFile.files![0];
    formData.append('file', file);
    formData.append('rdfm.software.version', packageUploadData.version!);
    formData.append('rdfm.hardware.devtype', packageUploadData.deviceType!);

    const headers = new Headers();

    const out = await packageResources.fetchPOST(PACKAGES_ENDPOINT, headers, formData);
    if (!out.success) {
        switch (out.code) {
            case StatusCodes.BAD_REQUEST:
                return {
                    success: false,
                    message:
                        'Provided metadata contains keys reserved by RDFM or a file was not provided.',
                };
            case StatusCodes.UNAUTHORIZED:
                return {
                    success: false,
                    message:
                        'User did not provide authorization data, or the authorization has expired',
                };
            case StatusCodes.FORBIDDEN:
                return {
                    success: false,
                    message: 'User was authorized, but did not have permission to upload packages',
                };
            default:
                return {
                    success: false,
                    message: 'Failed to upload a package. Got a response code of ' + out.code,
                };
        }
    }
    await packageResources.fetchResources();

    updatePermissions();

    return { success: true };
};

/**
 * Request specified in
 * https://antmicro.github.io/rdfm/api.html#delete--api-v1-packages-(int-identifier)
 */
export const removePackageRequest = async (packageId: number): Promise<RequestOutput> => {
    const out = await packageResources.fetchDELETE(DELETE_PACKAGE_ENDPOINT(packageId));
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
                    message: 'User was authorized, but did not have permission to delete packages',
                };
            case StatusCodes.NOT_FOUND:
                return {
                    success: false,
                    message: 'Specified package does not exist',
                };
            case StatusCodes.CONFLICT:
                return {
                    success: false,
                    message: 'Package is assigned to a group and cannot be deleted',
                };
            default:
                return {
                    success: false,
                    message: 'Failed to delete package. Got a response code of ' + out.code,
                };
        }
    }
    await packageResources.fetchResources();
    return { success: true };
};

/**
 * Request specified in
 * https://antmicro.github.io/rdfm/api.html#get--api-v1-packages-(int-identifier)-download
 */
export const downloadPackageRequest = async (packageId: number): Promise<RequestOutput> => {
    const out = await packageResources.fetchGET(DOWNLOAD_PACKAGE_ENDPOINT(packageId));
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
                    message:
                        'User was authorized, but did not have permission to download packages',
                };
            case StatusCodes.NOT_FOUND:
                return {
                    success: false,
                    message: 'Specified package does not exist',
                };
            default:
                return {
                    success: false,
                    message: 'Failed to download package. Got a response code of ' + out.code,
                };
        }
    }
    return { success: true, message: out.data.download_url };
};
