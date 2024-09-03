import { ref } from 'vue';
import { type Ref } from 'vue';

const SERVER_URL =
    import.meta.env.VITE_SERVER_URL || `${window.location.protocol}//${window.location.host}`;

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

export const POLL_INTERVAL = 2500;

export interface Package {
    id: number;
    created: string;
    sha256: string;
    driver: string;
    metadata: Record<string, string>;
}

export interface PendingDevice {
    public_key: string;
    mac_address: string;
    last_appeared: string;
    metadata: Record<string, string>;
}

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

export interface Group {
    id: number;
    created: string;
    packages: number[];
    devices: number[];
    metadata: Record<string, string>;
    policy: string;
    priority: number;
}

export interface RequestOutput {
    success: boolean;
    message?: string;
}

export interface FetchOutput {
    success: boolean;
    code?: number;
    data?: any;
}

export const resourcesGetter = <T>(resources_url: string) => {
    const resources: Ref<T | undefined> = ref(undefined);
    const pollingStatus: Ref<PollingStatus> = ref(PollingStatus.InitialPoll);

    const fetchWrapper = async (
        url: string,
        method: string,
        headers: Headers = new Headers(),
        body?: BodyInit,
    ): Promise<FetchOutput> => {
        let response;
        try {
            response = await fetch(url, { method, body, headers: headers });
            if (!response.ok) {
                throw new Error(`Failed to fetch ${url}`);
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

export enum PollingStatus {
    InitialPoll,
    UnreachableURL,
    ActivePolling,
}
