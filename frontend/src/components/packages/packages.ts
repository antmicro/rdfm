import {
    DELETE_PACKAGE_ENDPOINT,
    PACKAGES_ENDPOINT,
    resourcesGetter,
    type Package,
    type RequestOutput,
} from '../../common/utils';

import { StatusCodes } from 'http-status-codes';

export type NewPackageData = {
    version: string | null;
    deviceType: string | null;
};

export const packageResources = resourcesGetter<Package[]>(PACKAGES_ENDPOINT);

export const uploadPackageRequest = async (
    uploadedPackageFile: HTMLInputElement,
    packageUploadData: NewPackageData,
): Promise<RequestOutput> => {
    const formData = new FormData();
    if ((uploadedPackageFile?.files ?? []).length > 0) {
        return { success: false, message: 'No file provided' };
    }
    if (packageUploadData.version === null)
        return { success: false, message: 'No package version provided' };

    if (packageUploadData.deviceType === null)
        return { success: false, message: 'No device type provided' };

    const file = uploadedPackageFile.files![0];
    formData.append('file', file);
    formData.append('rdfm.software.version', packageUploadData.version!);
    formData.append('rdfm.hardware.devtype', packageUploadData.deviceType!);

    const headers = new Headers();

    const out = await packageResources.fetchPOST(PACKAGES_ENDPOINT, headers, formData);
    if (!out.success) {
        return {
            success: false,
            message: 'Failed to upload a package. Got a response code of ' + out.code,
        };
    }
    await packageResources.fetchResources();
    return { success: true };
};

export const removePackageRequest = async (packageId: number): Promise<RequestOutput> => {
    const out = await packageResources.fetchDELETE(DELETE_PACKAGE_ENDPOINT(packageId));
    if (!out.success) {
        if (out.code === StatusCodes.CONFLICT) {
            return {
                success: false,
                message: 'The package you are trying to remove is in a group and cannot be removed',
            };
        } else {
            return {
                success: false,
                message: 'Failed to delete package. Got a response code of ' + out.code,
            };
        }
    }
    await packageResources.fetchResources();
    return { success: true };
};
