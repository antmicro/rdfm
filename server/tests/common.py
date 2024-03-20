import os
import time
import requests
import jwt
import urllib.parse
from typing import Optional


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
SERVER_WAIT_TIMEOUT = 5

# Commonly used endpoints
AUTH_ENDPOINT = f"{SERVER}/api/v1/auth"
GROUPS_ENDPOINT = f"{SERVER}/api/v2/groups"
PACKAGES_ENDPOINT = f"{SERVER}/api/v1/packages"
UPDATES_ENDPOINT = f"{SERVER}/api/v1/update/check"
DEVICES_ENDPOINT = f"{SERVER}/api/v2/devices"
DEVICES_WS = f"{SERVER}/api/v1/devices/ws"


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

