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
from typing import Optional, List
import server
import configuration
import traceback
import models.device
import json
from api.v1.common import api_error


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

        conf: configuration.ServerConfig = current_app.config['RDFM_CONFIG']
        res: Optional[Alert] = upload_file(request, filename,
                                           conf.cache_dir,
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
    conf: configuration.ServerConfig = current_app.config['RDFM_CONFIG']
    res = download_file(filename, conf.cache_dir,
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

    conf: configuration.ServerConfig = current_app.config['RDFM_CONFIG']
    upload_res: Optional[Alert] = upload_file(request, filename,
                                              conf.cache_dir,
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

    conf: configuration.ServerConfig = current_app.config['RDFM_CONFIG']
    download_res = download_file(filename, conf.cache_dir,
                                 server.instance.file_transfers)
    if isinstance(download_res, Request):
        return download_res.model_dump_json()
    return download_res


@devices_blueprint.route('/api/v1/devices')
def fetch_all():
    """ Fetch a list of devices registered on the server

    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired

    :>jsonarr integer id: device identifier
    :>jsonarr string last_access: datetime of last access to the server (RFC822)
    :>jsonarr string name: device-reported user friendly name
    :>jsonarr string mac_addr: device-reported MAC address
    :>jsonarr optional[integer] group: group identifier of assigned group
    :>jsonarr dict[str, str] metadata: device metadata (key/value pairs)
    :>jsonarr dict[str, bool] capabilities: device RDFM client capabilities


    **Example Request**

    .. sourcecode:: http

        GET /api/v1/devices HTTP/1.1
        Accept: application/json, text/javascript


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
          {
            "capabilities": {
              "exec_cmds": false,
              "file_transfer": true,
              "shell_connect": true
            },
            "group": 1,
            "id": 1,
            "last_access": null,
            "mac_address": "loopback",
            "metadata": {},
            "name": "dummy_device"
          }
        ]
    """  # noqa: E501
    try:
        devices: List[models.device.Device] = server.instance._devices_db.fetch_all()
        return [
            {
                "id": dev.id,
                "last_access": dev.last_access,
                "name": dev.name,
                "mac_address": dev.mac_address,
                "capabilities": json.loads(dev.capabilities),
                "metadata": json.loads(dev.device_metadata),
                "public_key": dev.public_key,
                "group": dev.group
            } for dev in devices
        ]
    except Exception as e:
        traceback.print_exc()
        print("Exception during device fetch:", repr(e))
        return api_error("device fetching failed", 500)


@devices_blueprint.route('/api/v1/devices/<int:identifier>')
def fetch_one(identifier: int):
    """ Fetch information about a single device given by the identifier

    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 404: device with the specified identifier does not exist

    :>json integer id: device identifier
    :>json string last_access: datetime of last access to the server (RFC822)
    :>json string name: device-reported user friendly name
    :>json string mac_addr: device-reported MAC address
    :>json optional[integer] group: group identifier of assigned group
    :>json dict[str, str] metadata: device metadata (key/value pairs)
    :>json dict[str, bool] capabilities: device RDFM client capabilities


    **Example Request**

    .. sourcecode:: http

        GET /api/v1/devices/1 HTTP/1.1
        Accept: application/json, text/javascript


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
          "capabilities": {
            "exec_cmds": false,
            "file_transfer": true,
            "shell_connect": true
          },
          "group": 1,
          "id": 1,
          "last_access": null,
          "mac_address": "loopback",
          "metadata": {},
          "name": "dummy_device"
        }
    """  # noqa: E501
    try:
        dev: Optional[models.device.Device] = server.instance._devices_db.fetch_one(identifier)
        if dev is None:
            return api_error("device does not exist", 404)

        return {
                "id": dev.id,
                "last_access": dev.last_access,
                "name": dev.name,
                "mac_address": dev.mac_address,
                "capabilities": json.loads(dev.capabilities),
                "metadata": json.loads(dev.device_metadata),
                "group": dev.group,
                "public_key": dev.public_key,
        }
    except Exception as e:
        traceback.print_exc()
        print("Exception during device fetch:", repr(e))
        return api_error("device fetching failed", 500)
