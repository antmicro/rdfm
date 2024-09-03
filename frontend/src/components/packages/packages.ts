import {
    DELETE_PACKAGE_ENDPOINT,
    HTTPStatus,
    PACKAGES_ENDPOINT,
    resourcesGetter,
    type Package,
} from '../../common/utils';

export type NewPackageData = {
    version: string | null;
    deviceType: string | null;
};

export const packageResources = resourcesGetter<Package[]>(PACKAGES_ENDPOINT);

export const uploadPackageRequest = async (
    uploadedPackageFile: HTMLInputElement,
    packageUploadData: NewPackageData,
) => {
    const formData = new FormData();
    if (uploadedPackageFile === null || uploadedPackageFile.files === null) {
        return;
    }

    // TODO validate the input
    const file = uploadedPackageFile.files[0];
    formData.append('file', file);
    formData.append('rdfm.software.version', packageUploadData.version!);
    formData.append('rdfm.hardware.devtype', packageUploadData.deviceType!);

    const headers = new Headers();

    const [status] = await packageResources.fetchPOST(PACKAGES_ENDPOINT, headers, formData);
    if (status) {
        await packageResources.fetchResources();
    } else {
        alert('Failed to upload package');
    }
};

export const removePackageRequest = async (packageId: number) => {
    const [success, status] = await packageResources.fetchDELETE(
        DELETE_PACKAGE_ENDPOINT(packageId),
    );
    if (success) {
        await packageResources.fetchResources();
    } else {
        if (status === HTTPStatus.Conflict) {
            alert('The package you are trying to remove is in a group and cannot be removed');
        } else {
            alert('Failed to delete package');
        }
    }
};
