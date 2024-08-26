import os
import time
import requests
import jwt
import urllib.parse
import base64
import json
from dataclasses import dataclass
from typing import Any, Optional
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Signature.pkcs1_15 import PKCS115_SigScheme


# Which path to use for probing by default
PROBE_PATH_DEFAULT = "/api/v1/packages"
# Which status code should be considered a successful response
PROBE_SUCCESS_STATUS = 200
# Path to the DB file to use for tests
DBPATH = "test-db.db"
# Server URL
SERVER = "http://127.0.0.1:5000/"
SERVER_WS = "ws://127.0.0.1:5000/"
# Server wait timeout, in seconds
SERVER_WAIT_TIMEOUT = 20

# Commonly used endpoints
AUTH_ENDPOINT = f"{SERVER}/api/v1/auth"
GROUPS_ENDPOINT = f"{SERVER}/api/v2/groups"
PACKAGES_ENDPOINT = f"{SERVER}/api/v1/packages"
UPDATES_ENDPOINT = f"{SERVER}/api/v1/update/check"
DEVICES_ENDPOINT = f"{SERVER}/api/v2/devices"
LOGS_ENDPOINT = f"{SERVER}/api/v1/logs"
DEVICES_WS = f"{SERVER}/api/v1/devices/ws"

@dataclass
class ProcessConfig():
    """A class representing RDFM server configuration
    """
    insert_mocks: bool = True
    no_ssl: bool = True
    no_api_auth: bool = True
    debug: bool = False


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


def manager_shell_ws(mac: str):
    return f"{SERVER_WS}/api/v1/devices/{mac}/shell"


def device_attach_shell_ws(mac: str, session: str):
    return f"{manager_shell_ws(mac)}/attach/{session}"


def wait_for_api(timeout: int,
                 server_url: str,
                 probe_path: str = PROBE_PATH_DEFAULT,
                 success_status: int = PROBE_SUCCESS_STATUS) -> bool:
    """ Wait for the API to become accessible by probing one of
        the endpoints until the specified status code is returned.

    Args:
        timeout: how long to wait for, in seconds
        server_url: base URL of the server

    Returns:
        True, if the API has become accessible
        False, if a timeout occurred
    """
    if timeout <= 0:
        raise ValueError("timeout should be greater than zero")

    probe_path = "/api/v1/packages"
    probe_url = urllib.parse.urljoin(server_url, probe_path)

    time_left = timeout
    last = time.time()
    while time_left > 0:
        now = time.time()
        time_left -= now - last
        last = now
        try:
            resp = requests.get(probe_url)
            if resp.status_code == success_status:
                return True
            time.sleep(0.1)
        except:
            time.sleep(0.1)
    return False


def create_fake_device_token():
    """ Creates a fake device token to use for mocking device authentication
        during API tests
    """
    from auth.device import DeviceToken, DEVICE_JWT_ALGO
    token = DeviceToken()
    token.created_at = int(time.time())
    token.expires = 600
    token.device_id = "00:00:00:00:00:00"
    secret = os.environ['JWT_SECRET']
    return jwt.encode(token.to_dict(), secret, algorithm=DEVICE_JWT_ALGO)

def device_fetch_all() -> list[dict]:
    """ Fetches all authorized devices.
    """
    response = requests.get(DEVICES_ENDPOINT)
    assert response.status_code == 200, "fetching devices should succeed"
    return response.json()


def package_create_dummy(meta: dict[str, str], size: int = 1024):
    """ Create a package with the specified metadata and dummy content.
    """
    dummy_package = {
        "file": ("file", b"\xff" * size)
    }
    for k, v in meta.items():
        dummy_package[k] = (None, v)
    response = requests.post(PACKAGES_ENDPOINT, files=dummy_package)
    assert response.status_code == 200, "making a test package should succeed"
    return response

def package_fetch_all() -> list[dict]:
    """ Fetches all packages.
    """
    response = requests.get(PACKAGES_ENDPOINT)
    assert response.status_code == 200, "fetching package should succeed"
    return response.json()

def package_delete(pid: int):
    """ Deletes package with `pid`.
    """
    response = requests.delete(f"{PACKAGES_ENDPOINT}/{pid}")
    assert response.status_code == 200, "deleting package should succeed"


def group_create(**metadata) -> dict:
    """ Creates new group with `metadata`.
    """
    json_default_priority = {}
    json_default_priority["metadata"] = metadata

    response = requests.post(GROUPS_ENDPOINT, json=json_default_priority)
    assert response.status_code == 200, "creating group should succeed"
    return response.json()

def group_assign_packages(gid: int, ids: list[int]):
    """ Assign the packages from `ids` to group `gid`.
    """
    response = requests.post(f"{GROUPS_ENDPOINT}/{gid}/package", json={
        "packages": ids
    })
    assert response.status_code == 200, "assigning packages should succeed"

def group_assign_devices(gid: int, add: list[int] = None, remove: list[int] = None):
    """ Adds or removes devices from group `gid`.
    """
    response = requests.patch(f"{GROUPS_ENDPOINT}/{gid}/devices", json={
        "add": add if add else [],
        "remove": remove if remove else [],
    })
    assert response.status_code == 200, "assigning devices should succeed"

def group_delete(gid: int):
    """ Deletes group `gid`.
    """
    response = requests.delete(f"{GROUPS_ENDPOINT}/{gid}")
    assert response.status_code == 200, "deleting group should succeed"

def update_check(meta: dict[str, str]) -> Optional[int]:
    """ Simulate an update check of a device with metadata `meta`.
    """
    response = requests.post(UPDATES_ENDPOINT, json=meta, headers={
        "Authorization": f"Bearer token={create_fake_device_token()}",
    })
    assert response.status_code in [200, 204], "update check should return a successful status code"
    match response.status_code:
        case 200:
            return response.json()["id"]
        case 204:
            return None


def group_change_policy(gid: int, policy: str):
    """ Change a group's update policy.
    """
    response = requests.post(f"{GROUPS_ENDPOINT}/{gid}/policy", json={
        "policy": policy
    })
    assert response.status_code == 200, "changing policy should succeed"

def auth_pending() -> list[dict]:
    """ Returns all pending devices.
    """
    response = requests.get(f"{AUTH_ENDPOINT}/pending")
    assert response.status_code == 200, "changing policy should succeed"
    return response.json()

