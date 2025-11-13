import signal
import subprocess
import sys
import pytest
import tempfile
from typing import List, Tuple
import time
import pexpect

from rdfm.permissions import (
    READ_PERMISSION,
    UPDATE_PERMISSION,
    SHELL_PERMISSION,
    PACKAGE_RESOURCE,
    DEVICE_RESOURCE,
    GROUP_RESOURCE,
    DEVICE_NAMED_RESOURCE,
)

GROUP_NAME = "dummy_group"
GROUP_DESCRIPTION = "dummy_group_description"
GROUP_PRIORITY = "25"
PACKAGE_VERSION = "THIS_IS_A_PACKAGE_VERSION_v0"
PACKAGE_DEVICE_TYPE = "x86_64"
DEVICE_MAC = "00:00:00:00:00:00"


def format_manager_args(rdfm_mgmt_args: List[str]) -> List[str]:
    return ["poetry",  "run", "-C", "../manager/", "rdfm-mgmt"] + rdfm_mgmt_args


def run_manager_command(rdfm_mgmt_args: List[str]) -> Tuple[str, int]:
    """ Run an rdfm-mgmt command and return the result and exit code

    This assumes that the current working directory is in the server/ folder,
    which is already the case for most of the tests here.
    """
    process = subprocess.Popen(format_manager_args(rdfm_mgmt_args), stdout=subprocess.PIPE)
    code: int = process.wait()
    output: bytes = process.stdout.read()
    return (output.decode(), code)


@pytest.fixture
def create_dummy_group(install_manager_to_venv):
    """ Create a dummy group

    The group's identifier is assumed to be #1, as we're spawning a new
    server every time.
    """
    return run_manager_command(["--no-api-auth", "groups", "create",
                                "--name", GROUP_NAME,
                                "--description", GROUP_DESCRIPTION,
                                "--priority", GROUP_PRIORITY])


@pytest.fixture
def upload_dummy_package(install_manager_to_venv):
    """ Upload a dummy package

    The package's identifier is assumed to be #1 for the exact same reason
    as above.
    """
    with tempfile.NamedTemporaryFile("w+b") as f:
        f.write(b'\x00' * 1024)
        yield run_manager_command(["--no-api-auth", "packages", "upload",
                                   "--device", PACKAGE_DEVICE_TYPE,
                                   "--version", PACKAGE_VERSION,
                                   "--path", f.name])


@pytest.fixture(scope="function")
def start_shell_mock(process):
    """ Starts a mock device providing shell functionality
    """
    process = pexpect.spawn("poetry run python3 tests/scripts/device-websocket-loop.py")
    try:
        process.expect("connected", timeout=10.0)
    except pexpect.EOF:
        pytest.fail("shell mock closed unexpectedly!")
    except pexpect.TIMEOUT:
        pytest.fail("shell mock did not connect to the server in time!")

    yield process

    process.kill(signal.SIGINT)


@pytest.fixture
def device_shell():
    """ Connect to the above mock shell using rdfm-mgmt
    """
    manager = pexpect.spawn(" ".join(format_manager_args(["--no-api-auth", "devices", "shell", DEVICE_MAC])))
    time.sleep(1.0)

    yield manager

    manager.kill(signal.SIGINT)


@pytest.fixture
def device_shell_no_teardown():
    manager = subprocess.Popen(format_manager_args(["--no-api-auth", "devices", "shell", DEVICE_MAC]), stdout=sys.stderr, stderr=sys.stderr, stdin=subprocess.PIPE)
    time.sleep(5.0)

    return manager


def test_list_devices(process, install_manager_to_venv):
    """ Test if listing registered devices works
    """
    out, code = run_manager_command(["--no-api-auth", "devices", "list"])
    assert code == 0, "listing devices should succeed"
    assert DEVICE_MAC in out, "the output should contain the registered device"


def test_list_packages(process, install_manager_to_venv):
    """ Test if listing packages works
    """
    out, code = run_manager_command(["--no-api-auth", "packages", "list"])
    assert code == 0, "listing packages should succeed"
    assert 'Available packages:' in out, "the output should contain the uploaded packages"


def test_list_groups(process, install_manager_to_venv):
    """ Test if listing groups works
    """
    out, code = run_manager_command(["--no-api-auth", "groups", "list"])
    assert code == 0, "listing groups should succeed"
    assert 'Device groups:' in out, "the output should contain the created groups"


def test_list_registrations(process, install_manager_to_venv):
    """ Test if listing pending registrations works
    """
    out, code = run_manager_command(["--no-api-auth", "devices", "pending"])
    assert code == 0, "listing registrations should succeed"
    assert 'Registration requests:' in out, "the output should contain the registrations"


def test_create_group(process, create_dummy_group):
    """ Test if creating groups works
    """
    out, code = create_dummy_group
    assert code == 0, "creating a group should succeed"
    assert "Created group with identifier" in out, "the group identifier should be present"


def test_delete_group(process, create_dummy_group):
    """ Test if deleting a previously created group works
    """
    out, code = run_manager_command(["--no-api-auth", "groups", "delete",
                                     "--group-id", "1"])
    assert code == 0, "deleting the group should succeed"

    out, code = run_manager_command(["--no-api-auth", "groups", "list"])
    assert code == 0, "listing the groups should succeed"
    assert GROUP_NAME not in out, "the group should no longer be present in the list"


def test_list_created_group(process, create_dummy_group):
    """ Test if a created group appears in the group listing
    """
    out, code = run_manager_command(["--no-api-auth", "groups", "list"])
    assert code == 0, "listing groups should succeed"
    assert GROUP_NAME in out, "the output should contain the newly created group name"
    assert GROUP_DESCRIPTION in out, "the output should contain the newly created group description"
    assert GROUP_PRIORITY in out, "the output should contain the newly created group priority"


def test_upload_package(process, upload_dummy_package):
    """ Test if uploading packages works
    """
    out, code = upload_dummy_package
    assert code == 0, "uploading a package should succeed"
    assert "Package uploaded" in out, "uploading a package should succeed"


def test_list_uploaded_package(process, upload_dummy_package):
    """ Test if an uploaded package appears in the packages list
    """
    out, code = run_manager_command(["--no-api-auth", "packages", "list"])
    assert code == 0, "listing packages should succeed"
    assert PACKAGE_VERSION in out, "the uploaded package should be visible after listing"


def test_delete_package(process, upload_dummy_package):
    """ Test if deleting a package works
    """
    _, code = run_manager_command(["--no-api-auth", "packages", "delete",
                                     "--package-id", "1"])
    assert code == 0, "deleting the package should succeed"

    out, code = run_manager_command(["--no-api-auth", "packages", "list"])
    assert code == 0, "listing packages should succeed"
    assert PACKAGE_VERSION not in out, "the package should not be present anymore"


def test_group_device_assignment(process, create_dummy_group):
    """ Test if assigning a device to a group works
    """
    _, code = run_manager_command(["--no-api-auth", "groups", "modify-devices",
                                     "--group-id", "1",
                                     "--add", "1"])
    assert code == 0, "assigning the device to a group should succeed"


def test_group_package_assignment(process, create_dummy_group, upload_dummy_package):
    """ Test if assigning a package to a group works
    """
    _, code = run_manager_command(["--no-api-auth", "groups", "assign-package",
                                     "--group-id", "1",
                                     "--package-id", "1"])
    assert code == 0, "assigning the package to a group should succeed"


def test_shell_to_device_prompt(start_shell_mock, device_shell: pexpect.spawn):
    """ Test if we can reverse shell to a dummy device

    This tests only if we receive incoming data from the shell.
    """
    try:
        device_shell.expect("\\$|#", timeout=5.0)
    except:
        pytest.fail("should receive shell prompt after connecting")


def test_shell_to_device_command(start_shell_mock, device_shell: pexpect.spawn):
    """ Test if we can run commands in a reverse shell

    This tests bidirectional communication between the shell and the user.
    """
    TEST_STRING="MANAGER_TEST_STRING"
    try:
        device_shell.expect("\\$|#")
        device_shell.send(f"TEST_VARIABLE={TEST_STRING}\n")
        device_shell.expect("\\$|#")
        device_shell.send("echo ${TEST_VARIABLE}\n")
        device_shell.expect(TEST_STRING, timeout=5.0)
    except:
        pytest.fail("running a simple echo command should work")


def test_shell_to_device_sigint(start_shell_mock, device_shell_no_teardown: subprocess.Popen):
    """ Tests if Ctrl-C causes the shell to exit cleanly
    """
    device_shell_no_teardown.send_signal(signal.SIGINT)

    time.sleep(1.0)
    assert device_shell_no_teardown.poll() is not None, "rdfm-mgmt should have terminated after Ctrl-C"
    assert device_shell_no_teardown.wait() == 0, "Ctrl-C should be a clean exit"


def test_shell_to_device_eof_stdin(start_shell_mock, device_shell_no_teardown: subprocess.Popen):
    """ Tests if Ctrl-d causes the shell to exit cleanly
    """
    device_shell_no_teardown.communicate(input=0x04.to_bytes(1), timeout=1.0) # Sends End-of-Transmission character

    assert device_shell_no_teardown.poll() is not None, "rdfm-mgmt should have terminated after Ctrl-D"
    assert device_shell_no_teardown.wait() == 0, "Ctrl-D should be a clean exit"


def test_create_permission(process, create_dummy_group):
    """ Test if creating a permission works
    """
    _, code = run_manager_command(["--no-api-auth", "permissions", "create", GROUP_RESOURCE,
                                   "--id", "1",
                                   "--user", "1",
                                   "--permission", READ_PERMISSION])
    assert code == 0, "creating a permission should succeed"

    out, code = run_manager_command(["--no-api-auth", "permissions", "list"])
    expected = "Permission type: read\nResource type: group\nResource id: 1\nUser id: 1"
    assert code == 0, "listing permissions should succeed"
    assert expected in out, "the permission should be present"


def test_create_multiple_permissions(process, create_dummy_group):
    """ Test if creating multiple permissions works
    """
    _, code = run_manager_command(["--no-api-auth", "permissions", "create", GROUP_RESOURCE,
                                   "--id", "1",
                                   "--user", "1", "2",
                                   "--permission", READ_PERMISSION, UPDATE_PERMISSION])
    assert code == 0, "creating a permission should succeed"

    out, code = run_manager_command(["--no-api-auth", "permissions", "list"])
    assert code == 0, "listing permissions should succeed"
    expected = [
        "Permission type: read\nResource type: group\nResource id: 1\nUser id: 1",
        "Permission type: update\nResource type: group\nResource id: 1\nUser id: 1",
        "Permission type: read\nResource type: group\nResource id: 1\nUser id: 2",
        "Permission type: update\nResource type: group\nResource id: 1\nUser id: 2"
    ]
    for e in expected:
        assert e in out, "the permission should be present"


def test_create_device_permission_by_mac(process, create_dummy_group):
    """ Test if creating device permissions by MAC address works
    """
    _, code = run_manager_command(["--no-api-auth", "permissions", "create", DEVICE_RESOURCE,
                                   "--id", DEVICE_MAC,
                                   "--user", "1", "2",
                                   "--permission", READ_PERMISSION, UPDATE_PERMISSION])
    assert code == 0, "creating a permission should succeed"

    out, code = run_manager_command(["--no-api-auth", "permissions", "list"])
    assert code == 0, "listing permissions should succeed"
    expected = [
        "Permission type: read\nResource type: device\nResource id: 1\nUser id: 1",
        "Permission type: update\nResource type: device\nResource id: 1\nUser id: 1",
        "Permission type: read\nResource type: device\nResource id: 1\nUser id: 2",
        "Permission type: update\nResource type: device\nResource id: 1\nUser id: 2"
    ]
    for e in expected:
        assert e in out, "the permission should be present"


def test_create_named_device_permission(process, create_dummy_group):
    """ Test if creating device permissions by name and tag works
    """
    _, code = run_manager_command(["--no-api-auth", "permissions", "create", DEVICE_NAMED_RESOURCE,
                                   "--name", "linux-device",
                                   "--user", "1", "2",
                                   "--permission", SHELL_PERMISSION])
    assert code == 0, "creating a permission should succeed"

    out, code = run_manager_command(["--no-api-auth", "permissions", "list"])
    assert code == 0, "listing permissions should succeed"
    expected = [
        "Permission type: shell\nResource type: device_by_tag\nResource name: linux-device\nUser id: 1",
        "Permission type: shell\nResource type: device_by_tag\nResource name: linux-device\nUser id: 2",
    ]
    for e in expected:
        assert e in out, "the permission should be present"


def test_delete_permission(process, upload_dummy_package):
    """ Test if deleting a permission works
    """
    _, code = run_manager_command(["--no-api-auth", "permissions", "create", "package",
                                   "--id", "1",
                                   "--user", "1",
                                   "--permission", "read"])
    assert code == 0, "creating a permission should succeed"

    _, code = run_manager_command(["--no-api-auth", "permissions", "delete", "package",
                                   "--id", "1",
                                   "--user", "1",
                                   "--permission", "read"])
    assert code == 0, "deleting a permission should succeed"

    out, code = run_manager_command(["--no-api-auth", "permissions", "list"])
    assert code == 0, "listing permissions should succeed"
    not_expected = "Permission type: read\nResource type: package\nResource id: 1\nUser id: 1"
    assert not_expected not in out, "the permission should not be present"


def test_delete_named_device_permission(process):
    """ Test if deleting a named device permission works
    """
    _, code = run_manager_command(["--no-api-auth", "permissions", "create", DEVICE_NAMED_RESOURCE,
                                   "--name", "linux-device",
                                   "--user", "1",
                                   "--permission", SHELL_PERMISSION])
    assert code == 0, "creating a permission should succeed"

    _, code = run_manager_command(["--no-api-auth", "permissions", "delete", DEVICE_NAMED_RESOURCE,
                                   "--name", "linux-device",
                                   "--user", "1",
                                   "--permission", SHELL_PERMISSION])
    assert code == 0, "deleting a permission should succeed"

    out, code = run_manager_command(["--no-api-auth", "permissions", "list"])
    assert code == 0, "listing permissions should succeed"
    not_expected = "Permission type: shell\nResource type: device_by_tag\nResource name: linux-device\nUser id: 1"
    assert not_expected not in out, "the permission should not be present"


def test_delete_multiple_permissions(process, upload_dummy_package):
    """ Test if deleting multiple permission works
    """
    _, code = run_manager_command(["--no-api-auth", "permissions", "create", PACKAGE_RESOURCE,
                                   "--id", "1",
                                   "--user", "1", "2",
                                   "--permission", READ_PERMISSION, UPDATE_PERMISSION])
    assert code == 0, "creating permissions should succeed"

    _, code = run_manager_command(["--no-api-auth", "permissions", "delete", PACKAGE_RESOURCE,
                                   "--id", "1",
                                   "--user", "1", "2",
                                   "--permission", READ_PERMISSION, UPDATE_PERMISSION])
    assert code == 0, "deleting permissions should succeed"

    out, code = run_manager_command(["--no-api-auth", "permissions", "list"])
    assert code == 0, "listing permissions should succeed"
    not_expected = [
        "Permission type: read\nResource type: package\nResource id: 1\nUser id: 1",
        "Permission type: update\nResource type: package\nResource id: 1\nUser id: 1",
        "Permission type: read\nResource type: package\nResource id: 1\nUser id: 2",
        "Permission type: update\nResource type: package\nResource id: 1\nUser id: 2"
    ]
    for e in not_expected:
        assert e not in out, "the permission not should be present"


def test_delete_permissions_all_ids(process, upload_dummy_package):
    """ Test if deleting permissions with --all-ids works
    """
    for _ in range(0,2):
        _, code = run_manager_command(["--no-api-auth", "groups", "create",
                                    "--name", GROUP_NAME,
                                    "--description", GROUP_DESCRIPTION,
                                    "--priority", GROUP_PRIORITY])
        assert code == 0, "creating group should succeed"

    _, code = run_manager_command(["--no-api-auth", "permissions", "create", GROUP_RESOURCE,
                                   "--id", "1", "2",
                                   "--user", "1", "2",
                                   "--permission", READ_PERMISSION])
    assert code == 0, "creating a permission should succeed"

    _, code = run_manager_command(["--no-api-auth", "permissions", "delete", GROUP_RESOURCE,
                                   "--all-ids",
                                   "--user", "1",
                                   "--permission", READ_PERMISSION])
    assert code == 0, "deleting a permission should succeed"

    out, code = run_manager_command(["--no-api-auth", "permissions", "list"])
    assert code == 0, "listing permissions should succeed"
    expected = [
        "Permission type: read\nResource type: group\nResource id: 1\nUser id: 2",
        "Permission type: read\nResource type: group\nResource id: 2\nUser id: 2"
    ]
    not_expected = [
        "Permission type: read\nResource type: group\nResource id: 1\nUser id: 1",
        "Permission type: read\nResource type: group\nResource id: 2\nUser id: 1"
    ]
    for e in expected:
        assert e in out, "the permission should be present"
    for e in not_expected:
        assert e not in out, "the permission not should be present"
