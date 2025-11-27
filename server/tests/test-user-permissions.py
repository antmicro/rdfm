import requests
import pytest
import os
import subprocess
import time
import json
from typing import Optional
from mocks.oauth2_token_introspection import start_token_mock, configure_token_mock, MockConfig
from api.v1.middleware import SCOPE_READ_ONLY, SCOPE_READ_WRITE, SCOPE_SINGLE_FILE, SCOPE_ROOTFS_IMAGE
from common import GROUPS_ENDPOINT, SERVER_WAIT_TIMEOUT, wait_for_api

from rdfm.permissions import (
    READ_PERMISSION,
    GROUP_RESOURCE,
    DEVICE_NAMED_RESOURCE,
)

SERVER = "http://127.0.0.1:5000/"
DBPATH = "test-db.db"

PERMISSIONS_ENDPOINT = f"{SERVER}/api/v1/permissions"
GROUPS_ENDPOINT = f"{SERVER}/api/v2/groups"
DEVICES_ENDPOINT = f"{SERVER}/api/v2/devices"

AUTH_AS_MGMT = {
    "Authorization": "Bearer token=management"
}
AUTH_AS_USER = {
    "Authorization": "Bearer token=user"
}

@pytest.fixture()
def process(db, configure_token_mock, request):
    new_env = os.environ.copy()
    new_env["JWT_SECRET"] = "TESTDEVELOPMENTSECRET123"
    new_env["RDFM_OAUTH_URL"] = configure_token_mock
    new_env["RDFM_OAUTH_CLIENT_ID"] = "rdfm-server-introspection"
    new_env["RDFM_OAUTH_CLIENT_SEC"] = "qPsZzvAUtDVREjJyuyAEu3SDBQElATgX"

    print("Starting server..")
    process = subprocess.Popen([
        "poetry", "run", "python3", "-m", "rdfm_mgmt_server",
        "--debug", "--no-ssl", "--test-mocks", "--database", request.getfixturevalue(db)
    ], env=new_env)
    assert wait_for_api(SERVER_WAIT_TIMEOUT, SERVER, success_status=401), "server has started successfully"

    yield process

    print("Shutting down server..")
    process.kill()


@pytest.mark.parametrize('token_mock_config', [MockConfig(valid=True)])
def test_permission_by_id(process):
    """ This tests access to a read-only endpoint using different tokens.

    For each token, a GET request is made to the predefined endpoint and the
    response is checked against an expected value.
    This should be an endpoint that always succeeds, for example listing groups.
    """
    # Manager creates a group
    test_group = {
        "metadata": {
            "description": "An example group"
        },
    }
    resp = requests.post(GROUPS_ENDPOINT, headers=AUTH_AS_MGMT, json=test_group)
    assert resp.status_code == 200, "creating a group should succeed"

    # User tries to access the group
    resp = requests.get(f"{GROUPS_ENDPOINT}/1", headers=AUTH_AS_USER)
    assert resp.status_code == 404, "user should not have access to the resource"

    # Manager assigns permission 
    permission = {
        "resource": GROUP_RESOURCE,
        "resource_id": 1,
        "user_id": "user",
        "permission": READ_PERMISSION
    }
    resp = requests.post(PERMISSIONS_ENDPOINT, headers=AUTH_AS_MGMT, json=permission)
    assert resp.status_code == 200, "creating permission should succeed"

    # User tries to access the group
    resp = requests.get(f"{GROUPS_ENDPOINT}/1", headers=AUTH_AS_USER)
    assert resp.status_code == 200, "user should have access to the resource"


@pytest.mark.parametrize('token_mock_config', [MockConfig(valid=True)])
def test_permission_by_name(process):
    """ This tests access to a read-only endpoint using different tokens.

    For each token, a GET request is made to the predefined endpoint and the
    response is checked against an expected value.
    This should be an endpoint that always succeeds, for example listing groups.
    """
    # User tries to access the device
    resp = requests.get(f"{DEVICES_ENDPOINT}/1", headers=AUTH_AS_USER)
    assert resp.status_code == 404, "user should not have access to the resource"

    # Manager assigns device tag
    resp = requests.post(f"{DEVICES_ENDPOINT}/1/tag/test-device", headers=AUTH_AS_MGMT, json={})
    assert resp.status_code == 200, "assigning tag should succeed"

    # Manager assigns permission 
    permission = {
        "resource": DEVICE_NAMED_RESOURCE,
        "resource_name": "test-device",
        "user_id": "user",
        "permission": READ_PERMISSION
    }
    resp = requests.post(PERMISSIONS_ENDPOINT, headers=AUTH_AS_MGMT, json=permission)
    assert resp.status_code == 200, "creating permission should succeed"

    # User tries to access the device
    resp = requests.get(f"{DEVICES_ENDPOINT}/1", headers=AUTH_AS_USER)
    assert resp.status_code == 200, "user should have access to the resource"

