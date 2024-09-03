import {
    DEVICES_ENDPOINT,
    PENDING_ENDPOINT,
    REGISTER_DEVICE_ENDPOINT,
    resourcesGetter,
    type PendingDevice,
    type RegisteredDevice,
} from '../../common/utils';

export const pendingDevicesResources = resourcesGetter<PendingDevice[]>(PENDING_ENDPOINT);
export const registeredDevicesResources = resourcesGetter<RegisteredDevice[]>(DEVICES_ENDPOINT);

export const registerDeviceRequest = async (mac_address: string, public_key: string) => {
    const body = JSON.stringify({
        mac_address,
        public_key,
    });

    const headers = new Headers();
    headers.set('Content-type', 'application/json');
    headers.set('Accept', 'application/json, text/javascript');

    const [status] = await pendingDevicesResources.fetchPOST(
        REGISTER_DEVICE_ENDPOINT,
        headers,
        body,
    );
    if (status) {
        await pendingDevicesResources.fetchResources();
    } else {
        alert('Failed to register device');
    }
};
