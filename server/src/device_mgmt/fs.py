from rdfm.ws import RDFM_WS_INVALID_REQUEST, WebSocketException
from device_mgmt.models.filesystem_operation import FilesystemOperation
from request_models import FsFileDownload, FsFileProbe
from device_mgmt.models.remote_device import RemoteDevice
import server
from flask import current_app
import storage
import configuration
import uuid
from pathlib import Path

LINK_EXPIRY = 3600
DOWNLOAD_BUCKET_SUBDIR = "rdfm.downloads"


def get_file_size(remote_device: RemoteDevice, file: str) -> int | None:
    """Return size of given file or None if does not exist"""
    operation = FilesystemOperation()
    server.instance.filesystem_operations.add(operation)

    remote_device.send_message(FsFileProbe(id=operation.id, file=file))

    operation.completed.wait()
    server.instance.filesystem_operations.remove(operation)

    return operation.response.size if operation.response.status == 0 else None


def prepare_download(mac_address: str, file: str) -> tuple[int, str]:
    """Upload file to the bucket and return status along with the download link"""
    if not (remote_device := server.instance.remote_devices.get(mac_address)):
        msg = f"Device '{mac_address}' not connected to the management WS."
        raise WebSocketException(msg, RDFM_WS_INVALID_REQUEST)

    # First we need to determine file size in order to determine amount of needed
    # upload urls. This check also allows us to terminate early if the file does
    # not exist
    file_size = get_file_size(remote_device, file)
    if not file_size:
        return 1, ""

    conf: configuration.ServerConfig = current_app.config["RDFM_CONFIG"]
    driver = storage.driver_by_name(conf.storage_driver, conf)

    object_name = str(uuid.uuid4())
    mpu = driver.create_multipart_downloader(f"{DOWNLOAD_BUCKET_SUBDIR}/{object_name}")

    try:
        # Here we generate upload urls for the remote device based on the file size
        # obtained earlier
        upload_urls, part_size = mpu.generate_urls(file_size, LINK_EXPIRY)

        operation = FilesystemOperation()
        server.instance.filesystem_operations.add(operation)

        # We send upload urls to the remote device along with the file path and
        # upload part size
        remote_device.send_message(FsFileDownload(
            id=operation.id, file=file, upload_urls=upload_urls, part_size=part_size)
        )

        operation.completed.wait()
        server.instance.filesystem_operations.remove(operation)

        # After receiving answer from the device we can complete the upload and
        # generate download url if the upload succeeded or terminate the upload
        # in case it failed
        if operation.response.status == 0:
            mpu.complete_upload(operation.response.etags)
            filename = str(Path(file).name)
            download_url = driver.generate_fs_download_url(
                f"{DOWNLOAD_BUCKET_SUBDIR}/{object_name}",
                LINK_EXPIRY,
                filename
            )
        else:
            mpu.abort_upload()
            download_url = ""

        return operation.response.status, download_url
    except Exception as e:
        # In case of failure we have to terminate the upload
        mpu.abort_upload()
        raise e
