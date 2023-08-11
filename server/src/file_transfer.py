import os
import uuid
import time
from typing import Optional
from request_models import Alert
from rdfm_mgmt_communication import Device, wait_at_most
from request_models import Request
from flask import Response, send_file


class FileTransfer():
    def __init__(self, device: Device,
                 device_filepath: str,
                 server_filepath: str):
        # Device that should upload/download file
        self.device: Device = device
        # Filepath on device
        self.device_filepath: str = device_filepath
        # Filepath in server cache
        self.server_filepath: str = server_filepath

        self.started: bool = False
        self.uploaded: bool = False

        self.error: bool = False
        self.error_msg: str = ''


def get_device_file_dir(upload_dir: str,
                        device_name: str) -> Optional[str]:
    """Checks where files that are uploaded/downloaded from device are
    in server transferred files cache directory.
    If it doesn't exist, it is created along with parent dirs.

    Args:
        upload_dir: Server file cache directory
        device_name: Device name

    Returns:
        path to device directory in server transferred files cache
    """
    assert device_name is not None
    device_file_dir = os.path.join(
        os.path.abspath(upload_dir),
        device_name)
    if not os.path.exists(device_file_dir):
        os.makedirs(device_file_dir)
    return device_file_dir


def new_file_transfer(upload_dir: str, device: Device,
                      device_filepath: str,
                      transfers: dict[str, FileTransfer]) -> Alert:
    """Creates new file transfer for device if it is possible

    Args:
        upload_dir: Server file cache directory
        device: Device to upload/download files
        device_filepath: Path on device where file will
            be downloaded/uploaded from
        transfers: Ongoing transfers tracker

    Returns:
        Response about result of creating new transfer
    """
    # Create file transfer with random cache filename
    cache_filename = str(uuid.uuid4())
    cache_device_dir: Optional[str] = get_device_file_dir(upload_dir,
                                                          device.name)
    assert cache_device_dir is not None
    transfers[cache_filename] = FileTransfer(device, device_filepath,
                                             os.path.join(
                                                 cache_device_dir,
                                                 cache_filename
                                             ))
    return Alert(alert={  # type: ignore
        'message': 'New file transfer',
        'filename': cache_filename
    })


def upload_file(request, filename: str, upload_dir: str,
                transfers: dict[str, FileTransfer]) -> Optional[Alert]:
    """Wrapper to avoid boilerplate code while uploading file as user and
    as a device client

    Args:
        request: HTTP request that was sent
        filename: Server cache filename
        upload_dir: Server cache directory
        transfers: Ongoing transfers tracker

    Returns:
        Alert if upload failed
    """
    print('Uploading', request.files['file'])
    file = request.files['file']
    if file.filename == '':
        print('Error: empty filename')
        return None
    if file:
        try:
            # Find/create device's directory in server cache
            cache_device_dir = get_device_file_dir(
                                            upload_dir,
                                            transfers[filename].device.name)
            print('Saving file in', cache_device_dir)
            if not cache_device_dir:
                print(cache_device_dir, "doesn't exist")
                return None
            assert cache_device_dir is not None
            device_file_dir = os.path.abspath(cache_device_dir)
            if not os.path.exists(device_file_dir):
                print("Device dir in cache does't exist, creating it")
                os.makedirs(device_file_dir)
                print('Created directory', device_file_dir)

            # Generate tmp filename
            file.save(os.path.join(device_file_dir, filename))
            print('File uploaded at',
                  os.path.join(device_file_dir, filename)
                  )
            transfers[filename].uploaded = True

        except Exception as e:
            error_msg = f'Error saving file, {str(e)}'
            print(error_msg)
            return Alert(alert={  # type: ignore
                'error': error_msg
            })
    return None


def download_file(filename: str, upload_dir: str,
                  transfers: dict[str, FileTransfer]) -> Request | Response:
    """Wrapper to avoid boilerplate code while downloading file as user and
    as a device client

    Args:
        filename: UUID of file in the server cache
        upload_dir: Server file cache directory
        transfers: Ongoing transfers tracker

    Returns:
        reply to request or sends a file
    """

    transfer = transfers[filename]
    print('Waiting for file', filename, 'to be uploaded...')

    # Wait for device to start upload
    if not wait_at_most(30, 0.5, lambda: transfer.started):
        return Alert(alert={  # type: ignore
            'error': 'Device timeout'
        })

    # Wait until file uploads
    while not transfer.uploaded and not transfer.error:
        time.sleep(1)
    if transfer.error:
        print('Device sent back an error')
        return Alert(alert={  # type: ignore
            'error': transfer.error_msg
        })

    device_file_dir = get_device_file_dir(upload_dir, transfer.device.name)
    if not device_file_dir:
        return Alert(alert={  # type: ignore
            'error': f'No file to download'
        })

    filepath = os.path.join(device_file_dir, filename)
    print('Sending', filepath)
    return send_file(filepath)
