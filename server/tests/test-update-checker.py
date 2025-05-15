import requests
import pytest
from common import (
        GROUPS_ENDPOINT,
        UPDATES_ENDPOINT,
        create_fake_device_token,
        group_assign_packages,
        group_change_policy,
        package_create_dummy,
        update_check,
)

# This should match the ID of any of the devices created
# by the `-test_mocks` flag
DUMMY_DEVICE_ID = 1
# Same as above
DUMMY_DEVICE_MAC = "00:00:00:00:00:00"
META_SOFT_VER = "rdfm.software.version"
META_DEV_TYPE = "rdfm.hardware.devtype"
META_MAC_ADDR = "rdfm.hardware.macaddr"
META_XDELTA_SUPPORT = "rdfm.software.supports_xdelta"
META_RSYNC_SUPPORT = "rdfm.software.supports_rsync"


@pytest.fixture
def create_dummy_group(process):
    # Create the group
    resp = requests.post(GROUPS_ENDPOINT, json={"metadata":{}})
    assert resp.status_code == 200, "group creation should succeed"

    # Add the dummy device to the group
    gid = resp.json()["id"]
    resp = requests.patch(f"{GROUPS_ENDPOINT}/{gid}/devices", json={
        "add": [DUMMY_DEVICE_ID],
        "remove": []
    })
    assert resp.status_code == 200, "assigning device to group should succeed"

    return gid


"""
    Simple sequential update scenario

    This tests whether the device receives proper packages for the simple case
    of sequential updates:
        v0 --> v1 --> v2 --> v3
"""


@pytest.fixture
def prepare_simple_sequential(create_dummy_group):
    package_create_dummy({
        META_SOFT_VER: "v0",
        META_DEV_TYPE: "dummy",
    })
    package_create_dummy({
        META_SOFT_VER: "v1",
        META_DEV_TYPE: "dummy",
        f"requires:{META_SOFT_VER}": "v0"
    })
    package_create_dummy({
        META_SOFT_VER: "v2",
        META_DEV_TYPE: "dummy",
        f"requires:{META_SOFT_VER}": "v1"
    })
    package_create_dummy({
        META_SOFT_VER: "v3",
        META_DEV_TYPE: "dummy",
        f"requires:{META_SOFT_VER}": "v2"
    })
    group_assign_packages(create_dummy_group, [1, 2, 3, 4])
    group_change_policy(create_dummy_group, "exact_match,v3")


def test_simple_sequential(prepare_simple_sequential):
    """ This tests a simple sequential update scenario from the point of view
        of a device requesting an update check.
    """
    assert update_check({
                META_SOFT_VER: "v0",
                META_DEV_TYPE: "dummy",
                META_MAC_ADDR: DUMMY_DEVICE_MAC
            }) == 2, "device should receive package to go from v0 to v1"

    assert update_check({
                META_SOFT_VER: "v1",
                META_DEV_TYPE: "dummy",
                META_MAC_ADDR: DUMMY_DEVICE_MAC
            }) == 3, "device should receive package to go from v1 to v2"

    assert update_check({
                META_SOFT_VER: "v2",
                META_DEV_TYPE: "dummy",
                META_MAC_ADDR: DUMMY_DEVICE_MAC
            }) == 4, "device should receive package to go from v2 to v3"

    assert update_check({
                META_SOFT_VER: "v3",
                META_DEV_TYPE: "dummy",
                META_MAC_ADDR: DUMMY_DEVICE_MAC
            }) is None, "device should be up-to-date"


def test_package_accessible(prepare_simple_sequential):
    """ This tests whether the generated package URL is actually
        accessible.
    """
    response = requests.post(UPDATES_ENDPOINT, json={
        META_SOFT_VER: "v0",
        META_DEV_TYPE: "dummy",
        META_MAC_ADDR: DUMMY_DEVICE_MAC
    }, headers={
        "Authorization": f"Bearer token={create_fake_device_token()}",
    })
    assert response.status_code == 200, "the update check should succeed"

    package_data = response.json()
    assert "uri" in package_data, "the response should contain a generated package URL"     # noqa: E501

    url = package_data["uri"]
    response = requests.get(url)
    assert response.status_code == 200, "the package should be accessible"


"""
    Delta algorithm support scenario

    This tests whether devices receive correct delta update packages based on
    their support for XDELTA or RSYNC algorithms:
        v0 --> v1 (XDELTA or RSYNC delta)
"""


@pytest.fixture
def prepare_delta_algorithm_support(create_dummy_group):
    package_create_dummy({
        META_SOFT_VER: "v0",
        META_DEV_TYPE: "dummy",
    })
    package_create_dummy({
        META_SOFT_VER: "v1",
        META_DEV_TYPE: "dummy",
        f"requires:{META_XDELTA_SUPPORT}": "true",
        f"requires:{META_SOFT_VER}": "v0",
    })
    package_create_dummy({
        META_SOFT_VER: "v1",
        META_DEV_TYPE: "dummy",
        f"requires:{META_RSYNC_SUPPORT}": "true",
        f"requires:{META_SOFT_VER}": "v0",
    })
    package_create_dummy({
        META_SOFT_VER: "v1",
        META_DEV_TYPE: "dummy",
    })
    group_assign_packages(create_dummy_group, [1, 2, 3, 4])
    group_change_policy(create_dummy_group, "exact_match,v1")


def test_delta_algorithm_support(prepare_delta_algorithm_support):
    """ This tests whether devices receive correct delta update packages based
        on their support for XDELTA or RSYNC algorithms, or a full update if no
        delta support is available.
    """
    # Device with XDELTA support gets XDELTA delta package
    assert update_check({
                META_SOFT_VER: "v0",
                META_DEV_TYPE: "dummy",
                META_MAC_ADDR: DUMMY_DEVICE_MAC,
                META_XDELTA_SUPPORT: "true",
            }) == 2, "device should receive XDELTA delta package"

    # Device with RSYNC support gets RSYNC delta package
    assert update_check({
                META_SOFT_VER: "v0",
                META_DEV_TYPE: "dummy",
                META_MAC_ADDR: DUMMY_DEVICE_MAC,
                META_RSYNC_SUPPORT: "true",
            }) == 3, "device should receive RSYNC delta package"

    # Device with both XDELTA and RSYNC support gets either delta package
    result = update_check({
                META_SOFT_VER: "v0",
                META_DEV_TYPE: "dummy",
                META_MAC_ADDR: DUMMY_DEVICE_MAC,
                META_XDELTA_SUPPORT: "true",
                META_RSYNC_SUPPORT: "true",
            })
    assert result in [2, 3], "device should receive either any delta package"

    # Device without delta support gets full update package
    assert update_check({
                META_SOFT_VER: "v0",
                META_DEV_TYPE: "dummy",
                META_MAC_ADDR: DUMMY_DEVICE_MAC,
            }) == 4, "device should receive full update package"

    # Device already on v1 gets no update
    assert update_check({
                META_SOFT_VER: "v1",
                META_DEV_TYPE: "dummy",
                META_MAC_ADDR: DUMMY_DEVICE_MAC,
                META_XDELTA_SUPPORT: "true",
                META_RSYNC_SUPPORT: "true",
            }) is None, "device should be up-to-date"
