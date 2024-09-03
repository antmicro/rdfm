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
} from '../../common/utils';

export type InitialGroupConfiguration = {
    id: number;
    priority: number;
    devices: number[];
    packages: number[];
};

export type GroupConfiguration = {
    id: number | null;
    priority: number | null;
    devices: string | null;
    packages: string | null;
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

export const patchDevicesRequest = async (
    groupId: number,
    addedDevices: number[],
    removedDevices: number[],
) => {
    const body = JSON.stringify({
        add: addedDevices,
        remove: removedDevices,
    });

    const [status] = await groupResources.fetchPATCH(
        PATCH_DEVICES_IN_GROUP_ENDPOINT(groupId),
        headers,
        body,
    );
    if (status) {
        await groupResources.fetchResources();
    } else {
        alert('Failed to configure group devices');
    }
};

export const updatePackagesRequest = async (groupId: number, packages: number[]) => {
    const body = JSON.stringify({
        packages,
    });

    const [status] = await groupResources.fetchPOST(
        ASSIGN_PACKAGE_IN_GROUP_ENDPOINT(groupId),
        headers,
        body,
    );
    if (status) {
        await groupResources.fetchResources();
    } else {
        alert('Failed to update group packages');
    }
};

export const updatePriorityRequest = async (groupId: number, priority: number) => {
    const body = JSON.stringify({
        priority: priority,
    });

    const [status] = await groupResources.fetchPOST(
        UPDATE_GROUP_PRIORITY_ENDPOINT(groupId),
        headers,
        body,
    );
    if (status) {
        await groupResources.fetchResources();
    } else {
        alert('Failed to update group priority');
    }
};

export const addGroupRequest = async (newGroup: NewGroupData) => {
    const body = JSON.stringify({
        // Keys are taken from the manager source code

        // TODO: Validate the input
        priority: newGroup.priority!,
        metadata: {
            'rdfm.group.name': newGroup.name!,
            'rdfm.group.description': newGroup.description!,
        },
    });

    const [status] = await groupResources.fetchPOST(GROUPS_ENDPOINT, headers, body);
    if (status) {
        await groupResources.fetchResources();
    } else {
        alert('Failed to create a new group');
    }
};

export const removeGroupRequest = async (groupId: number) => {
    const [status] = await groupResources.fetchDELETE(DELETE_GROUP_ENDPOINT(groupId));
    if (status) {
        await groupResources.fetchResources();
    } else {
        alert('Failed to delete group');
    }
};
