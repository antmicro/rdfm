import jwt
from flask import (
    Flask,
    request,
    Response,
    abort,
    send_from_directory,
    current_app,
    Blueprint
)
from request_models import (
    ListRequest,
    InfoDeviceRequest,
    UpdateDeviceRequest,
    ProxyDeviceRequest,
    Alert,
    DownloadRequest,
    UploadRequest,
    Request
)
from file_transfer import (
    new_file_transfer,
    upload_file,
    download_file,
)
from typing import Optional
import server


devices_blueprint: Blueprint = Blueprint("rdfm-server-devices", __name__)


@devices_blueprint.route('/')
def index():
    response = server.instance.handle_request(ListRequest())
    assert response is not None
    return response.model_dump_json()


@devices_blueprint.route('/device/<device_name>', methods=['GET'])
def device_metadata(device_name: str):
    response = server.instance.handle_request(
        InfoDeviceRequest(device_name=device_name)  # type: ignore
    )
    assert response is not None
    return response.model_dump_json()


@devices_blueprint.route('/device/<device_name>/update')
def device_update(device_name: str):
    response = server.instance.handle_request(
        UpdateDeviceRequest(device_name=device_name)  # type: ignore
    )
    assert response is not None
    return response.model_dump_json()


@devices_blueprint.route('/device/<device_name>/proxy')
def device_proxy(device_name: str):
    response = server.instance.handle_request(
        ProxyDeviceRequest(device_name=device_name)  # type: ignore
    )
    assert response is not None
    return response.model_dump_json()


@devices_blueprint.route('/upload', methods=['POST'])  # Device endpoint
def upload() -> str:
    try:
        decoded = jwt.decode(request.form['jwt'], server.instance.jwt_secret,
                             algorithms=["HS256"])

        # Find matching file transfer
        filename: Optional[str] = None
        for k, v in server.instance.file_transfers.items():
            if (v.device.name == decoded['name'] and
                    v.device_filepath == request.form['file_path']):
                filename = k
                break

        if not filename:
            error_msg = 'Error, no matching transfer found'
            print(error_msg)
            return Alert(alert={  # type: ignore
                'error': error_msg
            }).model_dump_json()
        transfer = server.instance.file_transfers[filename]
        transfer.started = True

        if 'error' in request.form:
            print('Device sent error')
            transfer.error = True
            transfer.error_msg = request.form['error']
            del server.instance.file_transfers[filename]
            return Alert(alert={  # type: ignore
                'message': 'File upload cancelled'
            }).model_dump_json()

        res: Optional[Alert] = upload_file(request, filename,
                                           current_app.config['UPLOAD_FOLDER'],
                                           server.instance.file_transfers)
        if res:
            return res.model_dump_json()

        server.instance.file_transfers[filename].uploaded = True
        print(filename, 'uploaded!')
        del server.instance.file_transfers[filename]
        return Alert(alert={  # type: ignore
            'message': 'Uploaded file'
        }).model_dump_json()
    except Exception as e:
        error_msg = f'Error uploading file: {str(e)}'
        print(error_msg)
        try:
            assert filename is not None
            del server.instance.file_transfers[filename]
        except Exception:
            pass
        return Alert(alert={  # type: ignore
            'error': error_msg
        }).model_dump_json()


@devices_blueprint.route('/download/<filename>', methods=['GET'])  # Device endpoint
def download(filename):
    res = download_file(filename, current_app.config['UPLOAD_FOLDER'],
                        server.instance.file_transfers)
    if isinstance(res, Request):
        return res.model_dump_json()
    return res


@devices_blueprint.route('/device/<device_name>/upload', methods=['POST'])  # User endpoint
def upload_device(device_name) -> str:
    # Check that device is connected
    if device_name not in server.instance.connected_devices:
        return Alert(alert={  # type: ignore
            'error': 'Device not found'
        })
    device = server.instance.connected_devices[device_name]
    res: Alert = new_file_transfer(device_name, device,
                                   request.form['file_path'],
                                   server.instance.file_transfers)
    if 'error' in res.alert:
        return res.model_dump_json()

    filename: str = res.alert['filename']
    if not filename:
        return Alert(alert={  # type: ignore
            'error': 'File upload failed'
        }).model_dump_json()

    device = server.instance.connected_devices[device_name]
    # Check that device has capabilities to handle file transfer
    if not device.can_handle_request('download'):
        del server.instance.file_transfers[filename]
        return Alert(alert={  # type: ignore
            'error': (f"Requested device doesn't provide necessary"
                      "capabilities:"),
            "requested_capabilities":
                device.required_capabilities['download']}
        ).model_dump_json()

    upload_res: Optional[Alert] = upload_file(request, filename,
                                              current_app.config['UPLOAD_FOLDER'],
                                              server.instance.file_transfers)
    if upload_res:
        return upload_res.model_dump_json()
    server.instance.file_transfers[filename].started = True

    # Send request to device so it downloads this file
    device.send(DownloadRequest(  # type: ignore
        file_path=request.form['file_path'],
        url=(request.url_root + 'download/' + filename))
    )

    return Alert(alert={  # type: ignore
        'message': 'Uploaded file to device'
    }).model_dump_json()


@devices_blueprint.route('/device/<device_name>/download',  # User endpoint
           methods=['GET'])
def download_device(device_name) -> str | Response:
    # Check that device is connected
    if device_name not in server.instance.connected_devices:
        return Alert(alert={  # type: ignore
            'error': 'Device not found'
        })
    device = server.instance.connected_devices[device_name]
    res: Alert = new_file_transfer(device_name, device,
                                   request.form['file_path'],
                                   server.instance.file_transfers)
    if 'error' in res.alert:
        return res.model_dump_json()

    filename: str = res.alert['filename']
    if not filename:
        return Alert(alert={  # type: ignore
            'error': 'File download failed'
        }).model_dump_json()

    device = server.instance.connected_devices[device_name]
    # Check that device has capabilities to handle file transfer
    if not device.can_handle_request('upload'):
        del server.instance.file_transfers[filename]
        return Alert(alert={  # type: ignore
            'error': (f"Requested device doesn't provide necessary"
                      "capabilities:"),
            "requested_capabilities":
                device.required_capabilities['upload']}
        ).model_dump_json()

    # Send request to device so it uploads this file
    device.send(UploadRequest(  # type: ignore
        file_path=request.form['file_path']
    ))

    download_res = download_file(filename, current_app.config['UPLOAD_FOLDER'],
                                 server.instance.file_transfers)
    if isinstance(download_res, Request):
        return download_res.model_dump_json()
    return download_res
