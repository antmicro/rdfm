from flask import (
    Flask,
    request,
    Response,
    abort,
    send_from_directory,
    Blueprint
)
from threading import Thread
from server import Server
import storage
from storage.local import LOCAL_STORAGE_PATH
import hashlib
import traceback
import datetime
import models.package
import tempfile
import server
from api.v1.common import api_error


packages_blueprint: Blueprint = Blueprint("rdfm-server-packages", __name__)


def metadata_contains_reserved_keys(metadata: dict[str, str]) -> bool:
    """Verify whether the user-provided metadata is legal, i.e does not
       contain any forbidden names.
    """
    return any([
        key.startswith("rdfm.storage.")
        for key in metadata
    ])


@packages_blueprint.route('/api/v1/packages')
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


    **Example Request**

    .. sourcecode:: http

        GET /api/v1/packages HTTP/1.1
        Accept: application/json, text/javascript


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "created": "Thu, 17 Aug 2023 10:41:08 GMT",
                "id": 1,
                "metadata": {
                    "rdfm.hardware.devtype": "dummydevice",
                    "rdfm.software.version": "v10",
                    "rdfm.storage.local.length": 4194304,
                    "rdfm.storage.local.uuid": "6f7483ac-5cde-467f-acf7-39e4b397e313"
                },
                "sha256": "4e415854e6d0cf9855b2290c02638e8651537989b8862ff9c9cb91b8d956ea06"
            }
        ]
    """  # noqa: E501
    try:
        packages = server.instance._packages_db.fetch_all()
        return [
            {
                "id": package.id,
                "created": package.created,
                "sha256": package.sha256,
                "metadata": package.info
            } for package in packages
        ]
    except Exception as e:
        traceback.print_exc()
        print("Exception during package fetch:", repr(e))
        return {}, 500


@packages_blueprint.route('/api/v1/packages', methods=['POST'])
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


    **Example Request**

    .. sourcecode:: http

        POST /api/v1/packages HTTP/1.1
        Accept: */*
        Content-Length: 4194738
        Content-Type: multipart/form-data; boundary=------------------------0f8f9642db3a513e

        --------------------------0f8f9642db3a513e
        Content-Disposition: form-data; name="rdfm.software.version"

        v10
        --------------------------0f8f9642db3a513e
        Content-Disposition: form-data; name="rdfm.hardware.devtype"

        dummydevice
        --------------------------0f8f9642db3a513e
        Content-Disposition: form-data; name="file"; filename="file.img"
        Content-Type: application/octet-stream

        <file contents>
        --------------------------0f8f9642db3a513e--


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json
    """  # noqa: E501
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
        package.info = meta
        package.driver = driver_name
        package.sha256 = sha256
        success = server.instance._packages_db.create(package)
        if not success:
            return api_error("could not create package", 500)

        return {}, 200

    except Exception as e:
        traceback.print_exc()
        print("Exception during package upload:", repr(e))
        return {}, 500


@packages_blueprint.route('/api/v1/packages/<int:identifier>', methods=['GET'])
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


    **Example Request**

    .. sourcecode:: http

        GET /api/v1/packages/1 HTTP/1.1
        Accept: application/json, text/javascript


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "created": "Thu, 17 Aug 2023 10:41:08 GMT",
            "id": 1,
            "metadata": {
                "rdfm.hardware.devtype": "dummydevice",
                "rdfm.software.version": "v10",
                "rdfm.storage.local.length": 4194304,
                "rdfm.storage.local.uuid": "6f7483ac-5cde-467f-acf7-39e4b397e313"
            },
            "sha256": "4e415854e6d0cf9855b2290c02638e8651537989b8862ff9c9cb91b8d956ea06"
        }
    """  # noqa: E501
    try:
        pkg = server.instance._packages_db.fetch_one(identifier)
        if pkg is None:
            return api_error("specified package does not exist", 404)

        return {
            "id": pkg.id,
            "created": pkg.created,
            "sha256": pkg.sha256,
            "driver": pkg.driver,
            "metadata": pkg.info
        }, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during package fetch:", repr(e))
        return {}, 500


@packages_blueprint.route('/api/v1/packages/<int:identifier>', methods=['DELETE'])
def delete_package(identifier: int):
    """ Delete the specified package

    :param identifier: package identifier
    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 403: user was authorized, but did not have permission
                 to delete packages
    :status 404: specified package does not exist


    **Example Request**

    .. sourcecode:: http

        DELETE /api/v1/packages/1 HTTP/1.1

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
    """
    try:
        package = server.instance._packages_db.fetch_one(identifier)
        if package is None:
            return api_error("specified package does not exist", 404)

        if not server.instance._packages_db.delete(identifier):
            return api_error("delete failed", 500)

        driver = storage.driver_by_name(package.driver)
        if driver is None:
            return api_error("delete failed", 500)
        driver.delete(package.info)

        return {}, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during package fetch:", repr(e))
        return api_error("delete failed", 500)


@packages_blueprint.route('/local_storage/<name>')
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