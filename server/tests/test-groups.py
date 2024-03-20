import requests
import subprocess

from common import (GROUPS_ENDPOINT)

DUMMY_DEVICE_ID = 1
GROUP_DEFAULT_PRIORITY = 25


def test_groups(process):
    # Fetching all groups, assumes that no groups were already created
    # i.e empty database
    resp = requests.get(GROUPS_ENDPOINT)
    assert resp.status_code == 200, "fetching all groups works"
    assert resp.content == b"[]", "empty database returns no groups"

    # Creating groups
    test_json_group_default_priority = {
        "metadata": {
            "description": "An example group"
        },
    }

    resp = requests.post(GROUPS_ENDPOINT, json=test_json_group_default_priority)
    assert resp.status_code == 200, "creating a group works"
    group_data = resp.json()
    assert group_data["metadata"] == test_json_group_default_priority["metadata"], "metadata was added to the group"
    assert group_data["priority"] == GROUP_DEFAULT_PRIORITY, "priority was set to the default value"

    resp = requests.post(GROUPS_ENDPOINT, json=test_json_group_default_priority)
    assert resp.status_code == 200, "creating a group with the same priority as an existing group works"
    group_data = resp.json()
    assert group_data["priority"] == GROUP_DEFAULT_PRIORITY, "priority was set to the default value"

    test_json_group_high_priority = {
        "metadata": {
            "description": "An example group"
        },
        "priority": 0
    }

    resp = requests.post(GROUPS_ENDPOINT, json=test_json_group_high_priority)
    assert resp.status_code == 200, "creating a group with an explicitly set priority works"
    group_data = resp.json()
    assert group_data["priority"] == test_json_group_high_priority["priority"], "priority was set to the requested value"

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

    # Create groups that will be used for testing package assignment
    test_group_default_priority_1 = requests.post(GROUPS_ENDPOINT, json=test_json_group_default_priority).json()
    test_group_default_priority_2 = requests.post(GROUPS_ENDPOINT, json=test_json_group_default_priority).json()
    test_group_high_priority = requests.post(GROUPS_ENDPOINT, json=test_json_group_high_priority).json()

    # Assign a device to the group (created in test-specific DB file `test.db`)
    resp = requests.patch(f"{GROUPS_ENDPOINT}/{test_group_default_priority_1['id']}/devices", json={
        "add": [DUMMY_DEVICE_ID],
        "remove": []
    })
    assert resp.status_code == 200, "modified device assignment successfully"
    resp  = requests.get(f"{GROUPS_ENDPOINT}/{test_group_default_priority_1['id']}").json()
    assert DUMMY_DEVICE_ID in resp["devices"], "device ID appears in fetched group information"

    # Trying to assign a second time should return an error
    resp = requests.patch(f"{GROUPS_ENDPOINT}/{test_group_default_priority_1['id']}/devices", json={
        "add": [DUMMY_DEVICE_ID],
        "remove": []
    })
    assert resp.status_code == 409, "signal trying to re-add an already existing device"

    # Assign a device to a group with different priority
    resp = requests.patch(f"{GROUPS_ENDPOINT}/{test_group_high_priority['id']}/devices", json={
        "add": [DUMMY_DEVICE_ID],
        "remove": []
    })
    assert resp.status_code == 200, "modified device assignment successfully"
    resp  = requests.get(f"{GROUPS_ENDPOINT}/{test_group_high_priority['id']}").json()
    assert DUMMY_DEVICE_ID in resp["devices"], "device ID appears in fetched group information"

    # Assign a device to a group with the same priority as other group the device is already assigned to should fail
    resp = requests.patch(f"{GROUPS_ENDPOINT}/{test_group_default_priority_2['id']}/devices", json={
        "add": [DUMMY_DEVICE_ID],
        "remove": []
    })
    assert resp.status_code == 409, "signal trying to assign a device to a group with the same priority as other group the device is already assigned to"

    # Changing a group priority
    resp = requests.post(f"{GROUPS_ENDPOINT}/{test_group_default_priority_1['id']}/priority", json={
        "priority": 10
    })
    assert resp.status_code == 200, "changing priority of a group works"

    # Changing a group priority to the same value as priority of another group assigned to the same device should fail
    resp = requests.post(f"{GROUPS_ENDPOINT}/{test_group_default_priority_1['id']}/priority", json={
        "priority": 0
    })
    assert resp.status_code == 409, "signal trying to set group priority to the same value as priority of another group assigned to the same device"

    # Deleting a group should fail, because a device is assigned to the group
    resp = requests.delete(f"{GROUPS_ENDPOINT}/{test_group_default_priority_1['id']}")
    assert resp.status_code == 409, "signal trying to remove group while a device is assigned"

    # Now remove the device from the group
    resp = requests.patch(f"{GROUPS_ENDPOINT}/{test_group_default_priority_1['id']}/devices", json={
        "add": [],
        "remove": [DUMMY_DEVICE_ID]
    })
    assert resp.status_code == 200, "removing devices from group works"
    resp  = requests.get(f"{GROUPS_ENDPOINT}/{test_group_default_priority_1['id']}").json()
    assert DUMMY_DEVICE_ID not in resp["devices"], "device ID no longer appears in fetched group information"

    # Deleting a group
    resp = requests.delete(f"{GROUPS_ENDPOINT}/{test_group_default_priority_1['id']}")
    assert resp.status_code == 200, "deleting a group with no devices works"
