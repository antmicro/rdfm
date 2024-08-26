import time
from typing import Any
from common import (DEVICES_WS,
                    manager_shell_ws, device_attach_shell_ws,
                    create_fake_device_token)
import simple_websocket
import pytest
from rdfm.ws import receive_message, send_message
from rdfm_mgmt_communication import CapabilityReport, DeviceAttachToManager


FAKE_DEVICE_MAC = "00:00:00:00:00:00"
MESSAGE_WAIT_TIMEOUT = 10.0


def receive(ws: simple_websocket.Client) -> Any:
    try:
        if not ws.connected:
            pytest.fail("failed receiving message on WebSocket, "
                        f"the connection was closed with status: {ws.close_reason} "
                        f"and message: {ws.close_message}")
        return ws.receive(timeout=MESSAGE_WAIT_TIMEOUT)
    except (simple_websocket.ConnectionClosed, simple_websocket.ConnectionError) as e:
        pytest.fail(f"failed receiving message on WebSocket: {e}")


@pytest.fixture
def connect_mock_device():
    """ Connect a mock device to the server

    The returned Client can be used to receive/send messages as the device.
    """
    try:
        client = simple_websocket.Client.connect(DEVICES_WS, headers={
            "Authorization": f"Bearer token={create_fake_device_token()}",
        })
        hello = receive(client)
        assert hello is not None, "the server should have sent a welcome message"

        yield client

        client.close()
    except (simple_websocket.ConnectionClosed, simple_websocket.ConnectionError) as e:
        pytest.fail(f"connecting to the device WebSocket failed: {e}")


@pytest.fixture
def connect_mock_device_with_shell_capability(connect_mock_device: simple_websocket.Client):
    """ Sets up capabilities for the mock device to enable shell support
    """
    try:
        send_message(connect_mock_device,
                     CapabilityReport(capabilities={
                         "shell": True
                     }))
        # Hacky sleep to ensure delivery
        time.sleep(5.0)
        return connect_mock_device
    except (simple_websocket.ConnectionClosed, simple_websocket.ConnectionError) as e:
        pytest.fail(f"connecting to the device WebSocket failed: {e}")


@pytest.fixture
def spawn_shell_on_mock_device():
    """ Spawn a shell on the mock device
    """
    try:
        client = simple_websocket.Client.connect(manager_shell_ws(FAKE_DEVICE_MAC))
        yield client
        client.close()
    except (simple_websocket.ConnectionError) as e:
        pytest.fail(f"connecting to the shell WebSocket failed: {e}")


def test_ws_connect_device(process, connect_mock_device):
    """ This tests if the device WebSocket connection works properly

    The device connects to this endpoint. This is a simple test to see
    if we establish a connection and if we receive the welcome message
    from the server.
    """
    # The fixture `connect_mock_device` will fail if the above fails.
    pass


def test_ws_device_capability_report(process,
                                     connect_mock_device):
    """ This tests if device capabilities are considered by the server

    We accomplish this by attempting to spawn a shell. The connection should
    be terminated, as the device does not provide the shell capability.
    """
    # Connection should be closed by the server, with the close message
    # signalling a missing device capability.
    with pytest.raises((simple_websocket.ConnectionClosed,)):
        client = simple_websocket.Client.connect(manager_shell_ws(FAKE_DEVICE_MAC))
        _ = client.receive(timeout=MESSAGE_WAIT_TIMEOUT)
        pytest.fail("the shell connection was not terminated, even though device does not support shell capability")

    assert "shell_attach" in client.close_message, "the close message should indicate the missing capability"


def test_ws_device_receives_shell_attach_message(process,
                                                 connect_mock_device_with_shell_capability,
                                                 spawn_shell_on_mock_device):
    """ This tests if the device receives a shell attach message

    When a manager spawns a shell, the device should receive a `shell_attach`
    message from the server indicating where it should connect to provide
    the shell contents.
    """
    msg = receive_message(connect_mock_device_with_shell_capability, MESSAGE_WAIT_TIMEOUT)
    assert isinstance(msg, DeviceAttachToManager), "the device should have received a shell_attach message"


def test_ws_device_attaching_to_shell_session(process,
                                              connect_mock_device_with_shell_capability,
                                              spawn_shell_on_mock_device):
    """ This tests if the device can attach to the shell session
        indicated in the `shell_attach` message.
    """
    msg: DeviceAttachToManager = receive_message(connect_mock_device_with_shell_capability, MESSAGE_WAIT_TIMEOUT)
    try:
        device_client = simple_websocket.Client.connect(device_attach_shell_ws(FAKE_DEVICE_MAC, msg.uuid), headers={
            "Authorization": f"Bearer token={create_fake_device_token()}",
        })
    except Exception as e:
        pytest.fail(f"device failed to attach to the shell session: {e}")


def test_ws_shell_bidirectional_communication(process,
                                              connect_mock_device_with_shell_capability,
                                              spawn_shell_on_mock_device):
    """ This tests if data is transferred between the manager and device
        in a established shell session.
    """

    msg: DeviceAttachToManager = receive_message(connect_mock_device_with_shell_capability, MESSAGE_WAIT_TIMEOUT)
    device_client = simple_websocket.Client.connect(device_attach_shell_ws(FAKE_DEVICE_MAC, msg.uuid), headers={
        "Authorization": f"Bearer token={create_fake_device_token()}",
    })

    manager: simple_websocket.Client = spawn_shell_on_mock_device
    TEST_MESSAGE = b'\x1b[1;31mRDFM TEST SHELL MESSAGE\033[m'

    device_client.send(TEST_MESSAGE)
    received = manager.receive(MESSAGE_WAIT_TIMEOUT)
    assert received == TEST_MESSAGE, "device to manager data transfer should work"

    manager.send(TEST_MESSAGE)
    received = device_client.receive(MESSAGE_WAIT_TIMEOUT)
    assert received == TEST_MESSAGE, "manager to device data transfer should work"


def test_ws_shell_spawn_on_nonexistent_device(process):
    """ This tests if trying to spawn a shell on a nonexistent device fails properly.
    """
    with pytest.raises(simple_websocket.ConnectionClosed):
        client = simple_websocket.Client.connect(manager_shell_ws("DUMMYMAC"))
        _ = client.receive(MESSAGE_WAIT_TIMEOUT)
        pytest.fail("shell connection did not close, despite the device not existing")

    assert "not connected" in client.close_message, "close message should indicate the device does not exist"
