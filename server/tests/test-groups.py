import pexpect
import time
import os
import json
import sys
import requests
import subprocess
import pytest


SERVER = "http://127.0.0.1:5000/"
GROUPS_ENDPOINT = f"{SERVER}/api/v1/groups"
DUMMY_DEVICE_ID = 1
DBPATH = "test-db.db"


@pytest.fixture()
def process():
    if os.path.isfile(DBPATH):
        os.remove(DBPATH)

    print("Starting server..")
    process = subprocess.Popen(["python3", "-m", "rdfm_mgmt_server", "--debug", "--no-ssl", "--no-api-auth", "--test-mocks", "--database", f"sqlite:///{DBPATH}"])
    time.sleep(5)

    yield process

    print("Shutting down server..")
    process.kill()


def test_groups(process: subprocess.Popen):
    # Fetching all groups, assumes that no groups were already created
    # i.e empty database
    resp = requests.get(GROUPS_ENDPOINT)
    assert resp.status_code == 200, "fetching all groups works"
    assert resp.content == b"[]", "empty database returns no groups"

    # Creating a group
    test_meta = {
        "description": "An example group"
    }
    resp = requests.post(GROUPS_ENDPOINT, json=test_meta)
    assert resp.status_code == 200, "creating a grup works"
    group_data = resp.json()
    assert group_data["metadata"] == test_meta, "metadata was added to the group"

    # Fetching information about a single group
    resp  = requests.get(f"{GROUPS_ENDPOINT}/{group_data['id']}")
    assert resp.status_code == 200, "fetching single group works"
    assert resp.json() == group_data, "fetched group data matches"

    # Deleting a group
    resp = requests.delete(f"{GROUPS_ENDPOINT}/{group_data['id']}")
    assert resp.status_code == 200, "deleting a group with no conflicts works"
    # The group should not exist
    resp  = requests.get(f"{GROUPS_ENDPOINT}/{group_data['id']}")
    assert resp.status_code == 404, "deleted group no longer exists"

    # Create a group that will be used for testing package assignment
    test_group = requests.post(GROUPS_ENDPOINT, json=test_meta).json()

    # Assign a device to the group (created in test-specific DB file `test.db`)
    resp = requests.patch(f"{GROUPS_ENDPOINT}/{test_group['id']}/devices", json={
        "add": [DUMMY_DEVICE_ID],
        "remove": []
    })
    assert resp.status_code == 200, "modified device assignment successfully"
    resp  = requests.get(f"{GROUPS_ENDPOINT}/{test_group['id']}").json()
    assert DUMMY_DEVICE_ID in resp["devices"], "device ID appears in fetched group information"

    # Trying to assign a second time should return an error
    resp = requests.patch(f"{GROUPS_ENDPOINT}/{test_group['id']}/devices", json={
        "add": [DUMMY_DEVICE_ID],
        "remove": []
    })
    assert resp.status_code == 409, "signal trying to re-add an already existing device"

    # Deleting a group should fail, because a device is assigned to the group
    resp = requests.delete(f"{GROUPS_ENDPOINT}/{test_group['id']}")
    assert resp.status_code == 409, "signal trying to remove group while a device is assigned"

    # Now remove the device from the group
    resp = requests.patch(f"{GROUPS_ENDPOINT}/{test_group['id']}/devices", json={
        "add": [],
        "remove": [DUMMY_DEVICE_ID]
    })
    assert resp.status_code == 200, "removing devices from group works"
    resp  = requests.get(f"{GROUPS_ENDPOINT}/{test_group['id']}").json()
    assert DUMMY_DEVICE_ID not in resp["devices"], "device ID no longer appears in fetched group information"

