from typing import Optional
from flask import (
    request,
    Blueprint,
    current_app
)
import storage
import traceback
import models.package
import server
from api.v1.common import api_error
import models.device
import models.group
import configuration
from api.v1.schemas import DeviceMetaSchema

update_blueprint: Blueprint = Blueprint("rdfm-server-updates", __name__)

""" Expiration time for generated package URLs, in seconds """
LINK_EXPIRY_TIME = 3600


@update_blueprint.route('/api/v1/update/check', methods=['POST'])
def check_for_update():
    """ Check for available updates

    Device clients must call this endpoint with their associated metadata.
    At minimum, the `rdfm.software.version`, `rdfm.hardware.devtype` and
    `rdfm.hardware.macaddr` pairs must be present. Based on this metadata,
    the device's currently assigned group (if any) and package, an
    update package is picked from the available ones.

    :status 200: an update is available
    :status 204: no updates are available
    :status 400: device metadata is missing device type, software version,
                 and/or MAC address
    :status 401: device did not provide authorization data,
                 or the authorization has expired

    :<jsonarr string rdfm.software.version: required: running software version
    :<jsonarr string rdfm.hardware.devtype: required: device type
    :<jsonarr string rdfm.hardware.macaddr: required: MAC address (used as ID)
    :<jsonarr string `...`: other device metadata

    :>json integer id: package identifier
    :>json string created: creation date
    :>json string sha256: sha256 of the uploaded package
    :>json string uri: generated URI for downloading the package


    **Example Request**

    .. sourcecode:: http

        POST /api/v1/update/check HTTP/1.1
        Accept: application/json, text/javascript
        Content-Type: application/json

        {
            "rdfm.software.version": "v0.0.1",
            "rdfm.hardware.macaddr": "00:11:22:33:44:55",
            "rdfm.hardware.devtype": "example"
        }


    **Example Responses**

    .. sourcecode:: http

        HTTP/1.1 204 No Content


    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
          "created": "Mon, 14 Aug 2023 13:03:27 GMT",
          "id": 1,
          "sha256": "4e415854e6d0cf9855b2290c02638e8651537989b8862ff9c9cb91b8d956ea06",
          "uri": "http://127.0.0.1:5000/local_storage/12a83ff3-2de2-4a95-8f3f-c7a884e426e5"
        }
    """
    try:
        errors = DeviceMetaSchema().validate({
            "metadata": request.json
        })
        if len(errors) > 0:
            return api_error(f"schema validation failed: {errors}", 400)

        device_meta = request.json
        print("Device metadata:", device_meta)
        softver = device_meta[models.package.META_SOFT_VER]
        devtype = device_meta[models.package.META_DEVICE_TYPE]
        hwmac = device_meta[models.package.META_MAC_ADDRESS]

        device: Optional[models.device.Device] = server.instance._devices_db.get_device_data(hwmac)
        if device is None:
            return api_error("provided MAC address does not match any device", 500)

        # If the device is not assigned to any group, there's no updates
        # to hand out to it
        if device.group is None:
            return {}, 204

        group: Optional[models.group.Group] = server.instance._groups_db.fetch_one(device.group)
        if group is None:
            # Because of DB constraints, this should never happen
            return api_error("device-assigned group does not exist", 500)

        # Device is in a group, but no package was assigned
        if group.package_id is None:
            return {}, 204

        package: Optional[models.package.Package] = server.instance._packages_db.fetch_one(group.package_id)
        if package is None:
            # Because of DB constraints, this should never happen
            return api_error("group-assigned package does not exist", 500)

        # Check if the package is actually compatible with the device
        # Note: watch out, package.metadata is an SQLAlchemy field, our meta is
        #       stored in `package.info`
        if package.info[models.package.META_DEVICE_TYPE] != devtype:
            return {}, 204
        # Currently installed version is the latest assigned
        if package.info[models.package.META_SOFT_VER] == softver:
            return {}, 204

        # A candidate package was found
        # Here, we could also check extra requirements
        # For example, the package depends on some certain metadata
        # values other than the device type or package version

        print("Found new matching package:", package)
        conf: configuration.ServerConfig = current_app.config['RDFM_CONFIG']
        driver = storage.driver_by_name(package.driver, conf)
        if driver is None:
            return api_error("invalid storage driver", 500)

        link = driver.generate_link(package.info, LINK_EXPIRY_TIME)
        print("Link:", link)

        return {
            "id": package.id,
            "created": package.created,
            "sha256": package.sha256,
            "uri": link
        }, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during update check:", repr(e))
        return api_error("update check failed", 500)
