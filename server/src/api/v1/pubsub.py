from flask import Blueprint, current_app
from auth.device import DeviceToken
from device_mgmt.pubsub import RdfmKafkaAdminClient
from api.v1.common import api_error
from api.v1.middleware import (
    device_api,
    check_device_permission,
)
from rdfm.permissions import (
        READ_PERMISSION,
        UPDATE_PERMISSION,
)
import server
import configuration
import models.device
import traceback


pubsub_blueprint: Blueprint = Blueprint("rdfm-server-pubsub", __name__)


@pubsub_blueprint.route("/api/v1/pubsub/request_topic", methods=["POST"])
@device_api
def lease_topic(device_token: DeviceToken):
    """Ask a management server to lease a topic from a Kafka cluster.

    The management server creates and/or sets ACLs on a topic so that the requesting device
    is able to produce to it. The topic name is derived from the MAC address of a device.

    :status 200: no error, responded with a leased topic
    :status 401: device did not provide authorization data,
                 or the authorization has expired

    :>json string bootstrap_servers: Address(es) for a client to bootstrap a connection with brokers
    :>json string topic: The derived topic name for the devie to produce to


    **Example Request**

    .. sourcecode:: http

        POST /api/v1/pubsub/request_topic HTTP/1.1
        Accept: application/json
        Authorization: Bearer token=placeholder.device.token

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Server: Werkzeug/3.0.4 Python/3.11.4
        Date: Mon, 08 Dec 2025 12:06:31 GMT
        Content-Type: application/json
        Content-Length: 64
        Connection: close

        {"bootstrap_servers":"192.168.230.44:9093","topic":"02-42-ac-13-00-05"}
    """
    try:
        conf: configuration.ServerConfig = current_app.config["RDFM_CONFIG"]

        return {
            "bootstrap_servers": conf.dev_bootstrap_servers,
            "topic": admin.lease_topic_for_device(device_token.device_id)
        }, 200

    except Exception as e:
        traceback.print_exc()
        print("Exception during lease topic", repr(e))
        return api_error("topic leasing failed", 500)


@pubsub_blueprint.route("/api/v1/pubsub/device/<int:identifier>")
@check_device_permission(READ_PERMISSION)
def check_topic(identifier: int):
    """Ask a management server to check if a device is able to produce to its topic.

    :param identifier: device identifier
    :status 200: no error, responded with a leased topic
    :status 204: device exists but it does not have an asssociated topic
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 404: device with the specified identifier does not exist

    :>json string topic: The derived topic name from the device MAC
    :>json boolean write: Denotes whether the device can write to the topic
    :>json boolean idempotent_write: Denotes whether the device can idempotently write to the topic


    **Example Request**

    .. sourcecode:: http

        GET /api/v1/pubsub/device/1 HTTP/1.1
        Accept: */*

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Server: Werkzeug/3.0.4 Python/3.11.4
        Date: Mon, 08 Dec 2025 11:53:22 GMT
        Content-Type: application/json
        Content-Length: 67
        Connection: close

        {"idempotent_write":true,"topic":"02-42-ac-13-00-05","write":true}
    """
    try:
        conf: configuration.ServerConfig = current_app.config["RDFM_CONFIG"]

        dev: Optional[
                models.device.Device
        ] = server.instance._devices_db.fetch_one(identifier)
        if dev is None:
            return api_error("device does not exist", 404)

        admin = RdfmKafkaAdminClient.quick_create()
        status = admin.device_topic_status(dev.mac_address)
        if status:
            return {"topic_name": status.topic_name,
                    "write": status.can_write(),
                    "idempotent_write": status.can_idempotent_write()}, 200
        else:
            return {}, 204  # device exists, but doesn't have a topic
    except Exception as e:
        traceback.print_exc()
        print("Exception during check topic", repr(e))
        return api_error("topic checking failed", 500)


@pubsub_blueprint.route("/api/v1/pubsub/device/<int:identifier>", methods=["DELETE"])
@check_device_permission(UPDATE_PERMISSION)  # As this isn't really deleting anything
def confiscate_topic(identifier: int):
    """Ask a management server to confiscate a topic from a device.

    :param identifier: device identifier
    :status 200: no error, confiscated the topic
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 404: device with the specified identifier does not exist

    **Example Request**

    .. sourcecode:: http

        DELETE /api/v1/pubsub/device/1 HTTP/1.1
        Accept: */*

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Server: Werkzeug/3.0.4 Python/3.11.4
        Date: Mon, 08 Dec 2025 12:00:55 GMT
        Content-Type: application/json
        Content-Length: 3
        Connection: close

        {}
    """
    try:
        conf: configuration.ServerConfig = current_app.config["RDFM_CONFIG"]

        dev: Optional[
                models.device.Device
        ] = server.instance._devices_db.fetch_one(identifier)
        if dev is None:
            return api_error("device does not exist", 404)

        admin = RdfmKafkaAdminClient.quick_create()
        admin.confiscate_topic_from_device(dev.mac_address)
        return {}, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during confiscate topic", repr(e))
        return api_error("topic confiscating failed", 500)
