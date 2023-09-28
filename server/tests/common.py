import os
import subprocess
import time
import urllib.parse
from typing import Optional
import pytest
import requests
import jwt
from auth.device import DeviceToken, DEVICE_JWT_ALGO


# Which path to use for probing by default
PROBE_PATH_DEFAULT = "/api/v1/packages"
# Path to the DB file to use for tests
DBPATH = "test-db.db"
# Server URL
SERVER = "http://127.0.0.1:5000/"
# Server wait timeout, in seconds
SERVER_WAIT_TIMEOUT = 5

# Commonly used endpoints
GROUPS_ENDPOINT = f"{SERVER}/api/v1/groups"
PACKAGES_ENDPOINT = f"{SERVER}/api/v1/packages"
UPDATES_ENDPOINT = f"{SERVER}/api/v1/update/check"


def wait_for_api(timeout: int,
                 server_url: str,
                 probe_path: str = PROBE_PATH_DEFAULT) -> bool:
    """ Wait for the API to become accessible by probing one of
        the endpoints until a 200 status code is returned.

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
            if resp.status_code == 200:
                return True
            time.sleep(0.1)
        except:
            time.sleep(0.1)
    return False


@pytest.fixture()
def process():
    """ Fixture to start the RDFM server
    """

    if os.path.isfile(DBPATH):
        os.remove(DBPATH)

    print("Starting server..")
    process = subprocess.Popen(["python3", "-m", "rdfm_mgmt_server", "--no-ssl", "--no-api-auth", "--test-mocks", "--database", f"sqlite:///{DBPATH}"])
    assert wait_for_api(SERVER_WAIT_TIMEOUT, SERVER), "server has started successfully"

    yield process

    print("Shutting down server..")
    process.kill()


def create_fake_device_token():
    """ Creates a fake device token to use for mocking device authentication
        during API tests
    """
    token = DeviceToken()
    token.created_at = int(time.time())
    token.expires = 600
    token.device_id = "00:00:00:00:00:00"
    secret = os.environ['JWT_SECRET']
    return jwt.encode(token.to_dict(), secret, algorithm=DEVICE_JWT_ALGO)


def package_create_dummy(meta: dict[str, str]):
    """ Create a package with the specified metadata and dummy content.
    """
    dummy_package = {
        "file": ("file", b"\xff" * 1024)
    }
    for k, v in meta.items():
        dummy_package[k] = (None, v)
    response = requests.post(PACKAGES_ENDPOINT, files=dummy_package)
    assert response.status_code == 200, "making a test package should succeed"


def group_assign_packages(gid: int, ids: list[int]):
    """ Assign the packages from `ids` to group `gid`.
    """
    response = requests.post(f"{GROUPS_ENDPOINT}/{gid}/package", json={
        "packages": ids
    })
    assert response.status_code == 200, "assigning packages should succeed"


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

