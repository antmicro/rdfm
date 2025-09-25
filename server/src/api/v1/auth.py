import json
import traceback
from api.v1.middleware import (
    deserialize_schema,
    public_api,
    management_read_only_api,
    management_read_write_api,
)
import auth.device
import models.device
import models.registration
from api.v1.common import api_error
from rdfm.schema.v1.devices import AuthRegisterRequest, RemovePendingRequest
from auth.device import DeviceToken
from flask import Blueprint, request
import server


auth_blueprint: Blueprint = Blueprint("rdfm-server-auth", __name__)
DEVICE_SIGNATURE_HEADER = "X-RDFM-Device-Signature"


@auth_blueprint.route("/api/v1/auth/device", methods=["POST"])
@public_api
@deserialize_schema(
    schema_dataclass=AuthRegisterRequest, key="register_request"
)
def check_in(register_request: AuthRegisterRequest):
    """Device authorization endpoint

    All device clients must first authorize with the RDFM server via this endpoint.

    :status 200: no error
    :status 400: invalid schema, or provided signature is invalid
    :status 401: device was not authorized by an administrator yet

    :<json dict[str, str|list] metadata: device metadata
    :<json str public_key: the device's RSA public key, in PEM format, with
                           newline characters escaped
    :<json int timestamp: POSIX timestamp at the time of making the request


    **Example Request**

    .. sourcecode:: http

        POST /api/v1/auth/device HTTP/1.1
        Accept: application/json, text/javascript
        Content-Type: application/json
        X-RDFM-Device-Signature: FGACvvZ4CFC0np9Z8QNeuF8jnaE7y8v532FNtwMjkWKyT6sHj0hTIgggxfgaC1mOmY/9xmnwv2aQLgUxbzCJs0yf1/PyxG3Gyf8Mt47+aXbT4/Mj8j++8EB2QxbB9TKwZiCGa+lkevXsZwOrD6l4WNWUeQFA/jgWzTLoYxsIdz0=

        {
            "metadata": {
                "rdfm.software.version": "v0",
                "rdfm.hardware.devtype": "dummy",
                "rdfm.hardware.macaddr": "00:00:00:00:00:00"
            },
            "public_key": "-----BEGIN PUBLIC KEY-----\\nMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCVqdgCAfyXUqLfOpHYwHFv4OQL\\n2p3LwHm5ag9XMY2ylvqU2r9eGNWkdXTtEnL81S6u+4CDFNmbUuimoeDMazqSKYED\\n3FtOU4+FrqaHf7T3oMkng5mNHcAqbyq6WAXs/HrXfvj7lR38qLJXgslgR3Js3M0k\\nB91oGfFwUa7I67BZYwIDAQAB\\n-----END PUBLIC KEY-----",
            "timestamp": 1694414456
        }


    **Example Response**

    Unauthorized device:

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized
        Content-Type: application/json

    Authorized device:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "expires": 300,
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkZXZpY2VfaWQiOiIwMDowMDowMDowMDowMDowMCIsImNyZWF0ZWQiOjE2OTQ0MTQ0NTYsImV4cGlyZXMiOjMwMH0.cG37RTA1niB8NhokqI0ryvDKZj_0eRpWWEeqawu4IYE"
        }
    """  # noqa: E501
    try:
        if DEVICE_SIGNATURE_HEADER not in request.headers:
            return api_error(
                "request is missing device signature header "
                f"({DEVICE_SIGNATURE_HEADER})",
                400,
            )

        signature = request.headers[DEVICE_SIGNATURE_HEADER]
        if not auth.device.verify_signature(
            request.get_data(), register_request.public_key, signature
        ):
            return api_error("signature verification failed", 400)

        # The above steps verify that the requester owns the private key
        # associated with the given public key.

        try:
            token: str
            data: DeviceToken
            token, data = auth.device.try_acquire_token(
                register_request.public_key, register_request.metadata
            )

            # Update the device's metadata on the server
            try:
                server.instance._devices_db.update_metadata(
                    data.device_id, register_request.metadata
                )
            except Exception as e:
                print(
                    f"Failed to update metadata for device {data.device_id}, "
                    f"exception: {e}",
                    flush=True,
                )

            return {"token": token, "expires": data.expires}
        except:     # noqa: E722
            return api_error("device unauthorized", 401)
    except Exception as e:
        traceback.print_exc()
        print("Exception during registration:", repr(e))
        return api_error("registration failed", 500)


@auth_blueprint.route("/api/v1/auth/pending")
@management_read_only_api
def fetch_registrations():
    """Fetch all pending registrations

    This endpoint returns device registrations requests that have not been accepted
    by an administrator yet.

    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired

    :>jsonarr dict[str, str] metadata: device metadata
    :>jsonarr str public_key: the device's RSA public key, in PEM format, with
                              newline characters escaped
    :>jsonarr str mac_address: the device's MAC address
    :>jsonarr str last_appeared: datetime (RFC822) of the last registration
                                 request made by the device


    **Example Request**

    .. sourcecode:: http

        GET /api/v1/auth/registrations HTTP/1.1
        Accept: application/json, text/javascript


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
          {
            "last_appeared": "Wed, 13 Sep 2023 10:40:49 GMT",
            "mac_address": "00:00:00:00:00:00",
            "metadata": {
              "rdfm.hardware.devtype": "dummy",
              "rdfm.hardware.macaddr": "00:00:00:00:00:00",
              "rdfm.software.version": "v0"
            },
            "public_key": "-----BEGIN PUBLIC KEY-----\\nMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCdBgmI/FGkb17Bcxr99lEF1Nof\\njwQaPcipnBWW+S3N6c937rGkINH0vkHMjcS3HRF2ku6/Knjj4uXrZtbwUbPoP4bP\\nbK+HrYVw9Di6hTHr042W7FxIzU3howCF68QQnUMG/5XmqwdsucH1gMRv8cuU21Vz\\nQazvf08UWZCUeQjw5QIDAQAB\\n-----END PUBLIC KEY-----"
          }
        ]
    """  # noqa: E501
    try:
        registrations = server.instance._registrations_db.fetch_all()
        return [
            {
                "mac_address": reg.mac_address,
                "public_key": reg.public_key,
                "last_appeared": reg.last_appeared,
                "metadata": reg.info,
            }
            for reg in registrations
        ]
    except Exception as e:
        traceback.print_exc()
        print("Exception during registrations fetch:", repr(e))
        return api_error("fetching registrations failed", 500)


# TODO: add a mechanism (via roles/permissions) which would allow non-admins to register devices
@auth_blueprint.route("/api/v1/auth/register", methods=["POST"])
@management_read_write_api
def set_registration():
    """Accept registration request

    Accepts an incoming device registration request. As a result, the device
    will be allowed access to the RDFM server on next registration attempt.

    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 403: user was authorized, but did not have permission
                 to change device registration status
    :status 404: the specified registration request does not exist

    :<json str public_key: RSA public key used in the registration request
    :<json str mac_address: MAC address used in the registration request


    **Example Request**

    .. sourcecode:: http

        POST /api/v1/auth/registrations HTTP/1.1
        Accept: application/json, text/javascript
        Content-Type: application/json

        {
            "mac_address": "00:00:00:00:00:00",
            "public_key": "-----BEGIN PUBLIC KEY-----\\nMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCdBgmI/FGkb17Bcxr99lEF1Nof\\njwQaPcipnBWW+S3N6c937rGkINH0vkHMjcS3HRF2ku6/Knjj4uXrZtbwUbPoP4bP\\nbK+HrYVw9Di6hTHr042W7FxIzU3howCF68QQnUMG/5XmqwdsucH1gMRv8cuU21Vz\\nQazvf08UWZCUeQjw5QIDAQAB\\n-----END PUBLIC KEY-----"
        }


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK

    """  # noqa: E501
    try:
        payload = request.json
        mac = payload["mac_address"]
        public_key = payload["public_key"]

        registration = server.instance._registrations_db.fetch_one(
            mac, public_key
        )
        if registration is None:
            return api_error("specified registration does not exist", 404)

        # There is a registration for the specified device.
        # We have to handle two cases:
        #   - A completely new device has appeared
        #   - A device has changed it's key
        dev = server.instance._devices_db.get_device_data(mac)
        if dev is not None:
            if dev.public_key != public_key:
                # Key change
                print(
                    "Device with identifier:",
                    mac,
                    "is changing key",
                    flush=True,
                )
                server.instance._devices_db.update_key(mac, public_key)
                server.instance._devices_db.update_metadata(
                    mac, registration.info
                )
                server.instance._devices_db.update_timestamp(
                    mac, registration.last_appeared
                )
            else:
                # Shouldn't happen
                print(
                    "Registration for identical public key - should never \
                    happen",
                    flush=True,
                )
        else:
            # Create a device and insert it into the database.
            device = models.device.Device()
            device.name = registration.mac_address
            device.mac_address = registration.mac_address
            device.public_key = registration.public_key
            device.device_metadata = json.dumps(registration.info)
            device.capabilities = json.dumps({"shell": False})
            device.last_access = registration.last_appeared
            server.instance._devices_db.insert(device)

        # We also need to delete the registration, as it's already
        # been processed.
        server.instance._registrations_db.delete_registration(mac, public_key)

        return {}, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during registrations fetch:", repr(e))
        return api_error("fetching registrations failed", 500)


@auth_blueprint.route("/api/v1/auth/pending", methods=['DELETE'])
@management_read_write_api
@deserialize_schema(
    schema_dataclass=RemovePendingRequest, key="remove_pending_request"
)
def remove_pending(remove_pending_request: RemovePendingRequest):
    """ Delete an unregistered device

    This endpoint allows deleting an unregistered device.
    As a result, the device will be removed from the list of pending devices.

    :param identifier: device identifier
    :status 200: no error
    :status 404: the specified device does not exist

    :<json str public_key: RSA public key used in the registration request
    :<json str mac_address: MAC address used in the registration request


    **Example Request**

    .. sourcecode:: http

        DELETE /api/v1/auth/pending HTTP/1.1
        Accept: application/json, text/javascript
        Content-Type: application/json

        {
            "mac_address": "00:00:00:00:00:00",
            "public_key": "-----BEGIN PUBLIC KEY-----
                MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCdBgmI/FGkb17Bcxr99lEF1Nof
                jwQaPcipnBWW+S3N6c937rGkINH0vkHMjcS3HRF2ku6/Knjj4uXrZtbwUbPoP4bP
                bK+HrYVw9Di6hTHr042W7FxIzU3howCF68QQnUMG/5XmqwdsucH1gMRv8cuU21Vz
                Qazvf08UWZCUeQjw5QIDAQAB
                -----END PUBLIC KEY-----"
        }


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json
    """
    try:
        dev: Optional[models.device.Device] = server.instance._registrations_db.fetch_one(
            remove_pending_request.mac_address, remove_pending_request.public_key)
        if dev is None:
            return api_error("device does not exist", 404)

        server.instance._registrations_db.delete_registration(
            remove_pending_request.mac_address, remove_pending_request.public_key)
        return {}, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during removal of pending device:", repr(e))
        return api_error("removal failed", 500)
