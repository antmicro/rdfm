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
import { useToast, type ToastPluginApi } from 'vue-toast-notification';

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
export const DOWNLOAD_PACKAGE_ENDPOINT = (id: number) => `${PACKAGES_ENDPOINT}/${id}/download`;

export const DEVICES_ENDPOINT = `${SERVER_URL}/api/v2/devices`;
export const PENDING_ENDPOINT = `${SERVER_URL}/api/v1/auth/pending`;
export const PERMISSIONS_ENDPOINT = `${SERVER_URL}/api/v1/permissions`;
export const REGISTER_DEVICE_ENDPOINT = `${SERVER_URL}/api/v1/auth/register`;
export const DELETE_DEVICE_ENDPOINT = (id: number) => `${DEVICES_ENDPOINT}/${id}`;

export const DEVICE_ACTIONS_ENDPOINT = (mac: string) =>
    `${SERVER_URL}/api/v2/devices/${mac}/action/list`;
export const DEVICE_ACTIONS_EXEC_ENDPOINT = (mac: string, actionId: string) =>
    `/api/v2/devices/${mac}/action/exec/${actionId}`;
export const DEVICE_ACTION_LOG_ENDPOINT = (mac: string) => `/api/v2/devices/${mac}/action_log`;
export const DEVICE_SHELL_ENDPOINT = (mac: string, token: string) =>
    `/api/v1/devices/${mac}/shell?token=${token}`;

export const DEVICE_TAGS_ENDPOINT = (id: number) => `${SERVER_URL}/api/v2/devices/${id}/tags`;
export const DEVICE_ADD_TAG_ENDPOINT = (id: number, tag: string) =>
    `${SERVER_URL}/api/v2/devices/${id}/tag/${tag}`;
export const TAGS_ENDPOINT = (tag: string) => `${SERVER_URL}/api/v2/tags/${tag}`;

export const GROUPS_ENDPOINT = `${SERVER_URL}/api/v2/groups`;
export const DELETE_GROUP_ENDPOINT = (id: number) => `${GROUPS_ENDPOINT}/${id}`;
export const UPDATE_GROUP_PRIORITY_ENDPOINT = (id: number) => `${GROUPS_ENDPOINT}/${id}/priority`;
export const UPDATE_GROUP_POLICY_ENDPOINT = (id: number) => `${GROUPS_ENDPOINT}/${id}/policy`;
export const PATCH_DEVICES_IN_GROUP_ENDPOINT = (id: number) => `${GROUPS_ENDPOINT}/${id}/devices`;
export const ASSIGN_PACKAGE_IN_GROUP_ENDPOINT = (id: number) => `${GROUPS_ENDPOINT}/${id}/package`;

export const LOGIN_PATH = `${OIDC_LOGIN_URL}?response_type=token&client_id=${OAUTH2_CLIENT}&redirect_uri=${FRONTEND_URL}/auth_data`;
export const LOGOUT_PATH = `${OIDC_LOGOUT_URL}?client_id=${OAUTH2_CLIENT}&post_logout_redirect_uri=${FRONTEND_URL}/logout`;

export const POLL_INTERVAL = 2500;

/**
 * RDFM roles specified in
 * https://antmicro.github.io/rdfm/rdfm_mgmt_server.html#basic-configuration
 */
export enum AdminRole {
    RW = 'rdfm_admin_rw',
    RO = 'rdfm_admin_ro',
    UPLOAD_ROOTFS_IMAGE = 'rdfm_upload_rootfs_image',
    UPLOAD_SINGLE_FILE = 'rdfm_upload_single_file',
    UPLOAD_NONSTANDARD_ARTIFACT = 'rdfm_upload_nonstandard_artifact',
    CREATE_GROUP = 'rdfm_create_group',
}

/**
 * RDFM permissions specified in
 * https://antmicro.github.io/rdfm/rdfm_mgmt_server.html#permissions
 */
export type Permission = {
    permission: 'read' | 'update' | 'delete' | 'shell';
    resource: 'package' | 'group' | 'device';
    resource_id: number;
    user_id: string;
};

export const adminRoles = ref<AdminRole[]>([]);
export const permissions = ref<Permission[]>([]);

export const updatePermissions = () => {
    const accessToken = localStorage.getItem('access_token');
    const parsedToken = JSON.parse(atob(accessToken!.split('.')[1]));
    fetchWrapper(PERMISSIONS_ENDPOINT, 'GET').then(
        (response) =>
            (permissions.value = response.data.filter(
                (p: Permission) => p.user_id == parsedToken.sub,
            )),
    );
};

export const hasPermission = (
    permission: Permission['permission'],
    resource: Permission['resource'],
    resource_id?: number,
) =>
    permissions.value.some(
        (p) => p.resource == resource && resource_id == p.resource_id && permission == p.permission,
    );

export const hasAdminRole = (r: AdminRole) => adminRoles.value.includes(r);

export const hasUploadAccess = () =>
    [
        AdminRole.RW,
        AdminRole.UPLOAD_ROOTFS_IMAGE,
        AdminRole.UPLOAD_SINGLE_FILE,
        AdminRole.UPLOAD_NONSTANDARD_ARTIFACT,
    ].some((r: AdminRole) => adminRoles.value.includes(r));

export const allowedTo = (
    permission: Permission['permission'],
    resource: Permission['resource'],
    id?: number,
    groups?: Group[],
) => {
    if (hasAdminRole(AdminRole.RW) || (hasAdminRole(AdminRole.RO) && permission == 'read')) {
        return true;
    }

    if (hasPermission(permission, resource, id)) {
        return true;
    }

    if (id != null && groups) {
        const hasGroupPermission = groups
            .filter(
                (g) =>
                    (resource == 'package' && g.packages.includes(id)) ||
                    (resource == 'device' && g.devices.includes(id)),
            )
            .some((g) => allowedTo(permission, 'group', g.id));

        return hasGroupPermission;
    }

    return false;
};

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
    metadata: Record<string, string | string[]>;
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
    metadata: Record<string, string | string[]>;
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

export const fetchWrapper = async (
    url: string,
    method: string,
    headers: Headers = new Headers(),
    body?: BodyInit,
) => {
    let response;
    try {
        const accessToken = localStorage.getItem('access_token');

        if (accessToken) {
            headers.set('Authorization', `Bearer token=${accessToken}`);
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

export const resourcesGetter = <T>(resources_url: string) => {
    const resources: Ref<T | undefined> = ref(undefined);
    const pollingStatus: Ref<PollingStatus> = ref(PollingStatus.InitialPoll);

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

/**
 * Notification system
 */

export type ToastPluginApiExtended = ToastPluginApi & {
    notifySuccess: (opts: { headline: string; msg?: string }) => void;
    notifyError: (opts: { headline: string; msg?: string }) => void;
};

const N_MAX_NOTIF = 6;

const enqueued: (() => void)[] = [];

const countNotifications = () => document.querySelectorAll('.v-toast__item').length;

/**
 * Will call the provided function if the number of notifications is smaller than `N_MAX_NOTIF`.
 * Otherwise the function will be added to a queue and called when the mentioned condition is satisfied.
 *
 * @param fn Function to call/enqueue
 */
const enqueue = (fn: () => void) => {
    if (enqueued.length == 0 && countNotifications() < N_MAX_NOTIF) {
        fn();
    } else {
        enqueued.push(fn);
    }
};

setInterval(() => {
    if (countNotifications() < N_MAX_NOTIF) {
        const event = enqueued.shift();
        if (event) event();
    }
}, 200);

export function useNotifications(): ToastPluginApiExtended {
    const $toast = useToast({ duration: 8_000 }) as ToastPluginApiExtended;
    const buildHTML = (prefix: string, msg?: string) => {
        let html = `<p>${prefix}</p>`;
        if (msg) {
            html += `<p>${msg}</p>`;
        }
        return html;
    };
    $toast.notifySuccess = ({ headline, msg }) =>
        enqueue(() => $toast.success(buildHTML(headline, msg)));
    $toast.notifyError = ({ headline, msg }) =>
        enqueue(() => $toast.error(buildHTML(headline, msg)));
    return $toast;
}
