/*
 * Copyright (c) 2024 Antmicro <www.antmicro.com>
 *
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * Module containing rdfm-server ENDPOINTS, interfaces of resources and
 * utility functions for obtaining the resources.
 */

import { StatusCodes } from 'http-status-codes';
import { ref } from 'vue';
import { type Ref } from 'vue';

const SERVER_URL =
    import.meta.env.VITE_SERVER_URL || `${window.location.protocol}//${window.location.host}`;
const OIDC_LOGIN_URL = import.meta.env.VITE_LOGIN_URL;
const OIDC_LOGOUT_URL = import.meta.env.VITE_LOGOUT_URL;
const OAUTH2_CLIENT = import.meta.env.VITE_OAUTH2_CLIENT;

const FRONTEND_URL =
    `${window.location.protocol}//${window.location.host}` +
    (import.meta.env.VITE_RDFM_BACKEND === 'true' ? '/api/static/frontend' : '');

/**
 * Endpoints for rdfm-server API
 * Specification in https://antmicro.github.io/rdfm/api.html
 */

export const PACKAGES_ENDPOINT = `${SERVER_URL}/api/v1/packages`;
export const DELETE_PACKAGE_ENDPOINT = (id: number) => `${PACKAGES_ENDPOINT}/${id}`;

export const DEVICES_ENDPOINT = `${SERVER_URL}/api/v2/devices`;
export const PENDING_ENDPOINT = `${SERVER_URL}/api/v1/auth/pending`;
export const REGISTER_DEVICE_ENDPOINT = `${SERVER_URL}/api/v1/auth/register`;

export const GROUPS_ENDPOINT = `${SERVER_URL}/api/v2/groups`;
export const DELETE_GROUP_ENDPOINT = (id: number) => `${GROUPS_ENDPOINT}/${id}`;
export const UPDATE_GROUP_PRIORITY_ENDPOINT = (id: number) => `${GROUPS_ENDPOINT}/${id}/priority`;
export const PATCH_DEVICES_IN_GROUP_ENDPOINT = (id: number) => `${GROUPS_ENDPOINT}/${id}/devices`;
export const ASSIGN_PACKAGE_IN_GROUP_ENDPOINT = (id: number) => `${GROUPS_ENDPOINT}/${id}/package`;

export const LOGIN_PATH = `${OIDC_LOGIN_URL}?response_type=token&client_id=${OAUTH2_CLIENT}&redirect_uri=${FRONTEND_URL}/auth_data`;
export const LOGOUT_PATH = `${OIDC_LOGOUT_URL}?client_id=${OAUTH2_CLIENT}&post_logout_redirect_uri=${FRONTEND_URL}/logout`;

export const POLL_INTERVAL = 2500;

/**
 * Package interface specified in
 * https://antmicro.github.io/rdfm/api.html#get--api-v1-packages-response-json-array-of-objects
 */
export interface Package {
    id: number;
    created: string;
    sha256: string;
    driver: string;
    metadata: Record<string, string>;
}

/**
 * Pending device interface specified in
 * https://antmicro.github.io/rdfm/api.html#get--api-v1-auth-pending-response-json-array-of-objects
 */
export interface PendingDevice {
    public_key: string;
    mac_address: string;
    last_appeared: string;
    metadata: Record<string, string>;
}

/**
 * Registered device interface specified in
 * https://antmicro.github.io/rdfm/api.html#get--api-v2-devices-response-json-array-of-objects
 */
export interface RegisteredDevice {
    id: number;
    last_access: string;
    name: string;
    mac_address: string;
    groups?: number[];
    metadata: Record<string, string>;
    capabilities: Record<string, boolean>;
    public_key: string;
}

/**
 * Group interface specified in
 * https://antmicro.github.io/rdfm/api.html#get--api-v2-groups-response-json-array-of-objects
 */
export interface Group {
    id: number;
    created: string;
    packages: number[];
    devices: number[];
    metadata: Record<string, string>;
    policy: string;
    priority: number;
}

/** Interface for wrapping request output. */
export interface RequestOutput {
    /** Boolean value indicating if request was successful */
    success: boolean;
    /**
     * Optional message with additional information.
     * If the `success` field is set to `true`, the message should be omitted.
     * Otherwise, the message should contain error information.
     */
    message?: string;
    /** Mapping from field names to error descriptions */
    errors?: Map<string, string>;
}

/** Enum that describes resource state */
export enum PollingStatus {
    /** The getter did not try to fetch resources yet. The status is set to this value initially. */
    InitialPoll,
    /** the getter could not communicate with the server. */
    UnreachableURL,
    /** the getter successfully fetched resources. */
    ActivePolling,
}

export const resourcesGetter = <T>(resources_url: string) => {
    const resources: Ref<T | undefined> = ref(undefined);
    const pollingStatus: Ref<PollingStatus> = ref(PollingStatus.InitialPoll);

    const fetchWrapper = async (
        url: string,
        method: string,
        headers: Headers = new Headers(),
        body?: BodyInit,
    ) => {
        let response;
        try {
            const accessToken = localStorage.getItem('access_token');

            if (accessToken) {
                headers.append('Authorization', `Bearer token=${accessToken}`);
            }
            response = await fetch(url, { method, body, headers: headers });
            if (!response.ok) {
                throw new Error(`Fetch returned status ${response.status}`);
            }
            const data = await response.json();
            return { success: true, code: response.status, data };
        } catch (e) {
            console.error(`Failed to fetch ${url} - ${e}`);
            return { success: false, code: response?.status, data: undefined };
        }
    };

    const fetchGET = (url: string) => fetchWrapper(url, 'GET');

    const fetchPOST = (url: string, headers: Headers, body: BodyInit) =>
        fetchWrapper(url, 'POST', headers, body);

    const fetchDELETE = (url: string) => fetchWrapper(url, 'DELETE');

    const fetchPATCH = (url: string, headers: Headers, body: BodyInit) =>
        fetchWrapper(url, 'PATCH', headers, body);

    const fetchResources = async () => {
        const out = await fetchGET(resources_url);
        if (out.success) {
            resources.value = out.data as T;
            pollingStatus.value = PollingStatus.ActivePolling;
        } else if (out.code == StatusCodes.UNAUTHORIZED) {
            window.location.href = LOGIN_PATH;
        } else {
            resources.value = undefined;
            pollingStatus.value = PollingStatus.UnreachableURL;
        }
    };

    return {
        resources,
        pollingStatus,
        fetchResources,
        fetchGET,
        fetchPOST,
        fetchPATCH,
        fetchDELETE,
    };
};
