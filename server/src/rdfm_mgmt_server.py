import os
import jwt
from flask import (
    Flask,
    request,
    Response,
    abort,
    send_from_directory
)
from threading import Thread
from server import Server
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
import storage
from storage.local import LocalStorage, LOCAL_STORAGE_PATH
import hashlib
import traceback
import datetime
import models.package
import json
import tempfile

app = Flask(__name__)
global server


@app.route('/upload', methods=['POST'])  # Device endpoint
def upload() -> str:
    try:
        decoded = jwt.decode(request.form['jwt'], server.jwt_secret,
                             algorithms=["HS256"])

        # Find matching file transfer
        filename: Optional[str] = None
        for k, v in server.file_transfers.items():
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
        transfer = server.file_transfers[filename]
        transfer.started = True

        if 'error' in request.form:
            print('Device sent error')
            transfer.error = True
            transfer.error_msg = request.form['error']
            del server.file_transfers[filename]
            return Alert(alert={  # type: ignore
                'message': 'File upload cancelled'
            }).model_dump_json()

        res: Optional[Alert] = upload_file(request, filename,
                                           app.config['UPLOAD_FOLDER'],
                                           server.file_transfers)
        if res:
            return res.model_dump_json()

        server.file_transfers[filename].uploaded = True
        print(filename, 'uploaded!')
        del server.file_transfers[filename]
        return Alert(alert={  # type: ignore
            'message': 'Uploaded file'
        }).model_dump_json()
    except Exception as e:
        error_msg = f'Error uploading file: {str(e)}'
        print(error_msg)
        try:
            assert filename is not None
            del server.file_transfers[filename]
        except Exception:
            pass
        return Alert(alert={  # type: ignore
            'error': error_msg
        }).model_dump_json()


@app.route('/download/<filename>', methods=['GET'])  # Device endpoint
def download(filename):
    res = download_file(filename, app.config['UPLOAD_FOLDER'],
                        server.file_transfers)
    if isinstance(res, Request):
        return res.model_dump_json()
    return res


@app.route('/device/<device_name>/upload', methods=['POST'])  # User endpoint
def upload_device(device_name) -> str:
    # Check that device is connected
    if device_name not in server.connected_devices:
        return Alert(alert={  # type: ignore
            'error': 'Device not found'
        })
    device = server.connected_devices[device_name]
    res: Alert = new_file_transfer(device_name, device,
                                   request.form['file_path'],
                                   server.file_transfers)
    if 'error' in res.alert:
        return res.model_dump_json()

    filename: str = res.alert['filename']
    if not filename:
        return Alert(alert={  # type: ignore
            'error': 'File upload failed'
        }).model_dump_json()

    device = server.connected_devices[device_name]
    # Check that device has capabilities to handle file transfer
    if not device.can_handle_request('download'):
        del server.file_transfers[filename]
        return Alert(alert={  # type: ignore
            'error': (f"Requested device doesn't provide necessary"
                      "capabilities:"),
            "requested_capabilities":
                device.required_capabilities['download']}
        ).model_dump_json()

    upload_res: Optional[Alert] = upload_file(request, filename,
                                              app.config['UPLOAD_FOLDER'],
                                              server.file_transfers)
    if upload_res:
        return upload_res.model_dump_json()
    server.file_transfers[filename].started = True

    # Send request to device so it downloads this file
    device.send(DownloadRequest(  # type: ignore
        file_path=request.form['file_path'],
        url=(request.url_root + 'download/' + filename))
    )

    return Alert(alert={  # type: ignore
        'message': 'Uploaded file to device'
    }).model_dump_json()


@app.route('/device/<device_name>/download',  # User endpoint
           methods=['GET'])
def download_device(device_name) -> str | Response:
    # Check that device is connected
    if device_name not in server.connected_devices:
        return Alert(alert={  # type: ignore
            'error': 'Device not found'
        })
    device = server.connected_devices[device_name]
    res: Alert = new_file_transfer(device_name, device,
                                   request.form['file_path'],
                                   server.file_transfers)
    if 'error' in res.alert:
        return res.model_dump_json()

    filename: str = res.alert['filename']
    if not filename:
        return Alert(alert={  # type: ignore
            'error': 'File download failed'
        }).model_dump_json()

    device = server.connected_devices[device_name]
    # Check that device has capabilities to handle file transfer
    if not device.can_handle_request('upload'):
        del server.file_transfers[filename]
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

    download_res = download_file(filename, app.config['UPLOAD_FOLDER'],
                                 server.file_transfers)
    if isinstance(download_res, Request):
        return download_res.model_dump_json()
    return download_res


def api_error(error_str: str, code: int):
    return {
        "error": error_str
    }, code


def metadata_contains_reserved_keys(metadata: dict[str, str]) -> bool:
    """Verify whether the user-provided metadata is legal, i.e does not
       contain any forbidden names.
    """
    return any([
        key.startswith("rdfm.storage.")
        for key in metadata
    ])


@app.route('/')
def index():
    response = server.handle_request(ListRequest())
    assert response is not None
    return response.model_dump_json()


@app.route('/device/<device_name>', methods=['GET'])
def device_metadata(device_name: str):
    response = server.handle_request(
        InfoDeviceRequest(device_name=device_name)  # type: ignore
    )
    assert response is not None
    return response.model_dump_json()


@app.route('/device/<device_name>/update')
def device_update(device_name: str):
    response = server.handle_request(
        UpdateDeviceRequest(device_name=device_name)  # type: ignore
    )
    assert response is not None
    return response.model_dump_json()


@app.route('/device/<device_name>/proxy')
def device_proxy(device_name: str):
    response = server.handle_request(
        ProxyDeviceRequest(device_name=device_name)  # type: ignore
    )
    assert response is not None
    return response.model_dump_json()


@app.route('/api/v1/packages')
def fetch_packages():
    """ Fetch a list of packages uploaded to the server

    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired

    :>jsonarr integer id: package identifier
    :>jsonarr string created: creation date
    :>jsonarr string sha256: sha256 of the uploaded package
    :>jsonarr string driver: storage driver used to store the package
    :>jsonarr dict[str, str] metadata: package metadata (key/value pairs)
    """
    try:
        packages = server._packages_db.fetch_all()
        return [
            {
                "id": package.id,
                "created": package.created,
                "sha256": package.sha256,
                "metadata": json.loads(package.info)
            } for package in packages
        ]
    except Exception as e:
        traceback.print_exc()
        print("Exception during package fetch:", repr(e))
        return {}, 500


@app.route('/api/v1/packages', methods=['POST'])
def upload_package():
    """ Upload an update package.

    Uploads an update package to the server.
    Remaining key/value pairs in the form request are used as
    metadata for the artifact.

    :form file: binary contents of the package
    :form rdfm.software.version: required: software version of the package
    :form rdfm.hardware.devtype: required: compatible device type
    :form `...`: remaining package metadata

    :status 200: no error, package was uploaded
    :status 400: provided metadata contains keys reserved by RDFM
                 or a file was not provided
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 403: user was authorized, but did not have permission
                 to upload packages
    """
    try:
        # TODO: Allow changing this from the configuration
        driver_name = "local"

        meta = request.form.to_dict()
        if metadata_contains_reserved_keys(meta):
            return api_error("provided metadata contains reserved key", 400)

        if "file" not in request.files:
            return api_error("missing package file", 400)

        driver = storage.driver_by_name(driver_name)
        if driver is None:
            return api_error("invalid storage driver", 500)

        sha256 = ""
        with tempfile.NamedTemporaryFile('wb+') as f:
            request.files["file"].save(f.name)
            success = driver.upsert(meta, f.name)
            if not success:
                return api_error("could not store artifact", 500)
            sha256 = hashlib.file_digest(f, 'sha256').hexdigest()

        package = models.package.Package()
        package.created = datetime.datetime.now()
        package.info = json.dumps(meta)
        package.driver = driver_name
        package.sha256 = sha256
        success = server._packages_db.create(package)
        if not success:
            return api_error("could not create package", 500)

        return {}, 200

    except Exception as e:
        traceback.print_exc()
        print("Exception during package upload:", repr(e))
        return {}, 500


@app.route('/api/v1/packages/<identifier>', methods=['GET'])
def fetch_package(identifier: int):
    """ Fetch information about a single package given by the specified ID

    :param identifier: package identifier
    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 404: specified package does not exist

    :>json integer id: package identifier
    :>json string created: creation date
    :>json string sha256: sha256 of the uploaded package
    :>json string driver: storage driver used to store the package
    :>json dict[str, str] metadata: package metadata (simple key/value pairs)
    """
    try:
        pkg = server._packages_db.fetch_one(identifier)
        if pkg is None:
            return api_error("specified package does not exist", 404)

        return {
            "id": pkg.id,
            "created": pkg.created,
            "sha256": pkg.sha256,
            "driver": pkg.driver,
            "metadata": json.loads(pkg.info)
        }, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during package fetch:", repr(e))
        return {}, 500


@app.route('/api/v1/packages/<identifier>', methods=['DELETE'])
def delete_package(identifier: int):
    """ Delete the specified package

    :param identifier: package identifier
    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 403: user was authorized, but did not have permission
                 to delete packages
    :status 404: specified package does not exist
    """
    try:
        package = server._packages_db.fetch_one(identifier)
        if package is None:
            return api_error("specified package does not exist", 404)

        if not server._packages_db.delete(identifier):
            return api_error("delete failed", 500)

        metadata = json.loads(package.info)
        driver = storage.driver_by_name(package.driver)
        if driver is None:
            return api_error("delete failed", 500)
        driver.delete(metadata)

        return {}, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during package fetch:", repr(e))
        return api_error("delete failed", 500)


KEY_SOFTVER = "rdfm.software.version"
KEY_DEVTYPE = "rdfm.hardware.devtype"


@app.route('/api/v1/update/check', methods=['POST'])
def check_for_update():
    """ Testing endpoint for update checks for devices.

    Request must contain the device's metadata - at minimum, the
    `rdfm.software.version` and `rdfm.hardware.devtype` pairs must be
    present. Based on this metadata, a matching package is picked
    from the available ones (most recent compatible one).

    TODO: This will be rewritten once we have the infrastructure
    for assigning artifacts to devices.

    :status 200: no updates are available
    :status 204: an update is available
    :status 400: device metadata is missing device type and/or software version
    :status 401: device did not provide authorization data,
                 or the authorization has expired

    :>jsonarr string rdfm.software.version: required: running software version
    :>jsonarr string rdfm.hardware.devtype: required: device type
    :>jsonarr string `...`: other device metadata
    """

    device_meta = request.json
    print("Device metadata:", device_meta)
    if KEY_DEVTYPE not in device_meta:
        return api_error("metadata is missing a device type", 400)
    if KEY_SOFTVER not in device_meta:
        return api_error("metadata is missing a software version", 400)

    try:
        packages = [
            {
                "id": pkg.id,
                "created": pkg.created,
                "sha256": pkg.sha256,
                "driver": pkg.driver,
                "metadata": json.loads(pkg.info)
            } for pkg in server._packages_db.fetch_all()
        ]
        # Check most recent packages first
        # This would probably be better done in the DB..
        packages.sort(key=lambda x: x["created"], reverse=True)

        for pkg in packages:
            # Only packages for matching device type may be used
            if pkg["metadata"][KEY_DEVTYPE] != device_meta[KEY_DEVTYPE]:
                continue
            # Skip over already installed package
            if pkg["metadata"][KEY_SOFTVER] == device_meta[KEY_SOFTVER]:
                # FIXME: Packages will be manually assigned in the future
                # For now, we automatically try to assign a package to a device
                # This break is just so we don't try to reassign older packages
                break
            # A candidate package was found
            # Here, we could also check extra requirements
            # For example, the package depends on some certain metadata
            # values other than the device type or package version

            print("Matching package for device type:", pkg)

            driver = storage.driver_by_name(pkg["driver"])
            if driver is None:
                return api_error("invalid storage driver", 500)

            link = driver.generate_link(pkg["metadata"], 60 * 60)
            print("Link:", link)

            return {
                "id": pkg["id"],
                "created": pkg["created"],
                "sha256": pkg["sha256"],
                "uri": link
            }, 200
        return {}, 204
    except Exception as e:
        traceback.print_exc()
        print("Exception during update check:", repr(e))
        return {}, 500


@app.route('/local_storage/<name>')
def fetch_local_package(name: str):
    """ Endpoint for exposing local package storage.

    **WARNING: Local storage should not be used in production deployment,
    only for local testing!**
    This will be disabled in the future for non-prod configurations.

    :param name: identifier (UUID) of the package object in local storage
    :status 200: no error
    :status 404: specified package does not exist
    """
    return send_from_directory(LOCAL_STORAGE_PATH, name)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='rdfm-mgmt-shell server instance.')
    parser.add_argument('-hostname', type=str, default='127.0.0.1',
                        help='ip addr or domain name of the host')
    parser.add_argument('-port', metavar='p', type=int, default=1234,
                        help='listening port')
    parser.add_argument('-http_port', metavar='hp', type=int, default=5000,
                        help='listening port')
    parser.add_argument('-no_ssl', action='store_false', dest='encrypted',
                        help='turn off encryption')
    parser.add_argument('-cert', type=str, default='./certs/SERVER.crt',
                        help='server cert file')
    parser.add_argument('-key', type=str, default='./certs/SERVER.key',
                        help="""server cert key file""")
    parser.add_argument('-database', metavar='db', type=str,
                        default='devices.db',
                        help='filepath to store device database')
    parser.add_argument('-cache_dir', type=str, default='server_file_cache',
                        help='file transfer cache directory')
    parser.add_argument('-jwt_secret', type=str,
                        default=os.environ['JWT_SECRET'],
                        help="""JWT secret key, if not provided it will
                            be read from $JWT_SECRET env var""")
    args = parser.parse_args()

    server = Server(args.hostname, args.port,
                    args.encrypted, args.cert, args.key,
                    args.database, args.jwt_secret)
    t = Thread(target=server.run, daemon=True)
    t.start()

    if args.encrypted:
        app.config['UPLOAD_FOLDER'] = args.cache_dir
        app.run(host=args.hostname, port=args.http_port,
                debug=True, use_reloader=False,
                ssl_context=(args.cert, args.key))
    else:
        app.run(host=args.hostname, port=args.http_port,
                debug=True, use_reloader=False)
