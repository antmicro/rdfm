import time
import os
import json
import requests
import subprocess
import pytest
import base64
from typing import Any, Optional
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Signature.pkcs1_15 import PKCS115_SigScheme
from common import UPDATES_ENDPOINT


SERVER = "http://127.0.0.1:5000/"
AUTH = f"{SERVER}/api/v1/auth/device"
DUMMY_DEVICE_ID = 1
DBPATH = "test-db.db"

METADATA = {
    "rdfm.software.version": "v0",
    "rdfm.hardware.devtype": "dummy",
    "rdfm.hardware.macaddr": "00:00:00:00:00:00"
}
TEST_METADATA_CACHING_KEY="rdfm.software.version"
TEST_METADATA_CACHING_EXPECTED_VALUE="this_was_modified"


def make_signature(key_pair, payload_bytes):
    """ Generates the signature that will be placed in the signature header
    """
    h = SHA256.new(payload_bytes)
    s = PKCS115_SigScheme(key_pair)
    signature = s.sign(h)
    return base64.b64encode(signature)


def make_authentication_request(metadata, key_pair):
    """ Creates the authentication request structure
    """
    return {
        "metadata": metadata,
        "public_key": key_pair.public_key().export_key("PEM").decode("utf-8"),
        "timestamp": int(time.time())
    }


class SimpleDevice():
    """ Device metadata """
    metadata: dict[str, str]
    """ The device's private/public key pair """
    key_pair: RSA.RsaKey
    """ Authentication request as dictionary """
    request: dict[str, Any]
    """ Authentication request as raw bytes """
    request_bytes: bytes
    """ Base64 signature to put in the request"""
    signature: str


    def __init__(self, metadata, key: Optional[RSA.RsaKey] = None) -> None:
        self.metadata = metadata
        if key is None:
            self.key_pair = RSA.generate(bits=2048)
        else:
            self.key_pair = key
        self.request = make_authentication_request(self.metadata, self.key_pair)
        # The signature must be calculated on the raw bytes
        # No further modification of `payload` allowed!
        self.request_bytes = json.dumps(self.request).encode("utf-8")
        self.signature = make_signature(self.key_pair, self.request_bytes)


test_device = SimpleDevice(METADATA)


@pytest.fixture()
def process():
    if os.path.isfile(DBPATH):
        os.remove(DBPATH)

    print("Starting server..")
    process = subprocess.Popen(["python3", "-m", "rdfm_mgmt_server", "--debug", "--no-ssl", "--no-api-auth", "--database", f"sqlite:///{DBPATH}"])
    time.sleep(5)

    yield process

    print("Shutting down server..")
    process.kill()


@pytest.fixture
def list_registrations():
    response = requests.get(f"{SERVER}/api/v1/auth/pending")
    # This should always succeed
    assert response.status_code == 200, "registrations should have been fetched successfully"
    return response.json()


@pytest.fixture
def list_devices():
    response = requests.get(f"{SERVER}/api/v1/devices")
    # This should always succeed
    assert response.status_code == 200, "devices should have been fetched successfully"
    return response.json()


@pytest.fixture
def submit_authorization():
    """ Submit a valid authentication request to the server
    """
    response = requests.post(AUTH,
                             data=test_device.request_bytes,
                             headers={
                                 "Content-Type": "application/json",
                                 "X-RDFM-Device-Signature": test_device.signature,
                             })
    return response


@pytest.fixture
def submit_authorization_with_modified_version():
    """ Submit a valid authentication request to the server, but modify one of the
        metadata fields to simulate an update.

    This is meant to be used in conjunction with `submit_authorization` to test
    server metadata caching.
    """
    new_metadata = test_device.metadata.copy()
    new_metadata[TEST_METADATA_CACHING_KEY] = TEST_METADATA_CACHING_EXPECTED_VALUE
    modified_device = SimpleDevice(new_metadata, test_device.key_pair)
    response = requests.post(AUTH,
                             data=modified_device.request_bytes,
                             headers={
                                 "Content-Type": "application/json",
                                 "X-RDFM-Device-Signature": modified_device.signature,
                             })
    return response


@pytest.fixture
def approve_device():
    """ Approve the device's registration request
    """
    response = requests.post(f"{SERVER}/api/v1/auth/register",
                             json={
                                 "public_key": test_device.request["public_key"],
                                 "mac_address": METADATA["rdfm.hardware.macaddr"]
                             })
    return response


@pytest.fixture
def submit_and_approve():
    """ Submit a valid authentication request to the server, and then approve
        the registration request
    """
    response = requests.post(AUTH,
                             data=test_device.request_bytes,
                             headers={
                                 "Content-Type": "application/json",
                                 "X-RDFM-Device-Signature": test_device.signature,
                             })
    # Device sends it's first authentication request, so a registration is created
    assert response.status_code == 401, "the server should validate the signature and return an unauthorized status"

    response = requests.post(f"{SERVER}/api/v1/auth/register",
                             json={
                                 "public_key": test_device.request["public_key"],
                                 "mac_address": METADATA["rdfm.hardware.macaddr"]
                             })
    # Approve the device registration next
    assert response.status_code == 200, "the device registration should have been accepted"


@pytest.fixture
def change_registered_device_key(submit_and_approve):
    """ Re-submit an authentication request for the device, this time containing a different
        public key. This simulates a scenario in which a device changes it's key after an
        update or by other means.
    """
    new_device = SimpleDevice(METADATA)
    response = requests.post(AUTH,
                             data=new_device.request_bytes,
                             headers={
                                 "Content-Type": "application/json",
                                 "X-RDFM-Device-Signature": new_device.signature,
                             })
    return new_device, response


@pytest.fixture
def make_dummy_authenticated_request(submit_authorization):
    """ Make a dummy authenticated request to a device API endpoint.

    Used for testing the "Last accessed" timestamp available in the device API.
    """
    assert submit_authorization.status_code == 200, "the device should receive a successful authentication response"
    token = submit_authorization.json()["token"]

    # Intentionally sleep for a second
    # This is to make sure the timestamp actually changes
    time.sleep(1)

    # We don't care about the result, the timestamp should be updated
    # on any usage of the token.
    response = requests.post(UPDATES_ENDPOINT, json=test_device.metadata,
                             headers={
                                 "Authorization": f"Bearer token={token}"
                             })
    assert response.status_code != 401, "the request should have been authenticated"


def test_signature_missing(process):
    """ This tests whether the server requires the device signature header
        to be present in the request.
    """
    response = requests.post(AUTH,
                             data=test_device.request_bytes,
                             headers={
                                 "Content-Type": "application/json",
                             })
    assert response.status_code == 400, "the server should return an error when the signature is missing"


def test_valid_signature(process, submit_authorization):
    """ This tests whether the server properly validates the signature
        of the registration payload when given a valid signature.
    """
    assert submit_authorization.status_code == 401, "the server should validate the signature and return an unauthorized status"


def test_invalid_signature(process):
    """ This tests whether the signature is properly rejected when it's
        been corrupted/tampered with.
    """
    response = requests.post(AUTH,
                             data=test_device.request_bytes,
                             headers={
                                 "Content-Type": "application/json",
                                 # Mutate the contents of the signature a bit by skipping the first byte
                                 "X-RDFM-Device-Signature": base64.b64encode(base64.b64decode(test_device.signature)[1:]),
                             })
    assert response.status_code == 400, "signature validation should fail after manipulating the signature"


def test_invalid_pubkey(process):
    """ This tests whether the server rejects a request with an invalid
        public key.
    """
    modified_payload = test_device.request.copy()
    modified_payload["public_key"] = "this is an invalid key"
    response = requests.post(AUTH,
                             json=modified_payload,
                             headers={
                                 "X-RDFM-Device-Signature": test_device.signature,
                             })
    assert response.status_code == 400, "server should reject a request with an invalid public key"


def test_different_pubkey(process):
    """ This tests whether the server rejects a request containing a different
        public key than the one that was used to create the signature.
    """
    key_pair = RSA.generate(2048)
    public_key = key_pair.public_key().export_key("PEM").decode("utf-8")

    modified_payload = test_device.request.copy()
    modified_payload["public_key"] = public_key
    response = requests.post(AUTH,
                             json=modified_payload,
                             headers={
                                 "X-RDFM-Device-Signature": test_device.signature,
                             })
    assert response.status_code == 400, "server should reject the request with a different public key as the signature is invalid"


def test_key_change(process, submit_and_approve, change_registered_device_key, list_devices, list_registrations):
    """ This tests the scenario in which a device changes it's key.
    """
    new_device, response = change_registered_device_key
    assert response.status_code == 401, "server should reject the new authentication request, as the device's key has changed"
    assert list_devices[0]["public_key"] == test_device.request["public_key"], "the device's authorized public key remains unchanged"
    assert list_registrations[0]["public_key"] == new_device.request["public_key"], "a new registration request should appear containing the new public key"


def test_registrations_list_empty(process, list_registrations):
    """ This tests whether fetching registrations works
    """
    assert len(list_registrations) == 0, "registration list should be empty as no requests for authorization have been made"


def test_registrations_list_after_auth(process, submit_authorization, list_registrations):
    """ This tests whether a new device has appeared on the registration list
        after successfully submitting it's authorization payload, but before being approved.
    """
    assert submit_authorization.status_code == 401, "the server should validate the signature and return an unauthorized status"
    assert len(list_registrations) > 0, "registrations list should now have an entry for the new device"
    assert list_registrations[0]["public_key"] == test_device.request["public_key"], "registration entry should contain the public key used in the authentication payload"


def test_registrations_approve_device(process, submit_and_approve, list_registrations):
    """ This tests whether submitting a request and approving the device afterwards
        properly removes the registration entry from the list.
    """
    assert len(list_registrations) == 0, "registrations list should now be empty, as the device has been approved"


def test_list_devices_without_approval(process, submit_authorization, list_devices):
    """ This tests if the device is not added to the devices list when it hasn't
        been approved yet.
    """
    assert submit_authorization.status_code == 401, "the server should validate the signature and return an unauthorized status"
    assert len(list_devices) == 0, "there should be no devices present, as the device wasn't approved"


def test_list_devices_with_approval(process, submit_and_approve, list_devices):
    """ This tests if the device is properly added to the devices list after
        being approved.
    """
    assert len(list_devices) > 0, "the device should be present in the devices list, as it has been approved"


def test_auth_after_approval(process, submit_and_approve, submit_authorization):
    """ This tests if the device receives an app token after successful authentication
        and authorization.
    """
    assert submit_authorization.status_code == 200, "the device should receive a successful authentication response"
    assert "token" in submit_authorization.json(), "the authentication response should contain an app token"


def test_device_metadata_change(process,
                                submit_and_approve,
                                submit_authorization_with_modified_version,
                                list_devices):
    """ This tests if the server properly updates the server-side stored device metadata
    """
    assert submit_authorization_with_modified_version.status_code == 200, "the device should receive a successful authentication response"
    assert list_devices[0]["metadata"][TEST_METADATA_CACHING_KEY] == TEST_METADATA_CACHING_EXPECTED_VALUE, "the metadata should have been updated on the server"


def test_device_last_access_tracking(process,
                                     submit_and_approve,
                                     list_devices,
                                     make_dummy_authenticated_request):
    """ This tests if the last access timestamp is properly updated on requests to the device API.
    """
    # Can't re-use the list_devices fixture again (as the value is cached)
    response = requests.get(f"{SERVER}/api/v1/devices")
    assert response.status_code == 200, "devices should have been fetched successfully"
    devices = response.json()

    assert list_devices[0]["last_access"] != devices[0]["last_access"], "last access timestamp should have changed after making a request"


def test_device_token_verification_none(process):
    """ This tests if the server rejects a request to a device API endpoint without
        a device token.
    """
    response = requests.post(f"{SERVER}/api/v1/update/check", json=METADATA)
    assert response.status_code == 401, "the endpoint should not be accessible without presenting a device token"


def test_device_token_verification_invalid(process):
    """ This tests if the server rejects a request to a device API endpoint with an
        invalid device token.
    """
    response = requests.post(f"{SERVER}/api/v1/update/check", json=METADATA, headers={
        "Authorization": f"Bearer token=AAAAAAAAAAAAAAAAAAAAAAA"
    })
    assert response.status_code == 401, "the endpoint should not be accessible with an invalid device token"


def test_device_token_verification_valid(process, submit_and_approve, submit_authorization):
    """ This tests if the server allows a request to a device API endpoint with a valid
        device token.

    For this, the update check endpoint is used, as the behavior should be identical
    in all cases when using the `device_api` decorator.
    """
    assert submit_authorization.status_code == 200, "the device should receive a successful authentication response"
    assert "token" in submit_authorization.json(), "the authentication response should contain an app token"
    token = submit_authorization.json()["token"]

    # Now, add the token to the request
    response = requests.post(f"{SERVER}/api/v1/update/check", json=METADATA, headers={
        "Authorization": f"Bearer token={token}"
    })
    assert response.status_code != 401, "the endpoint should now be accessible"
