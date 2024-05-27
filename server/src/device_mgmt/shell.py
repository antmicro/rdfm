from uuid import UUID
from device_mgmt.models.reverse_shell import ReverseShell
import simple_websocket
from rdfm.ws import RDFM_WS_INVALID_REQUEST
import device_mgmt.helpers
from rdfm.ws import WebSocketException
from request_models import DeviceAttachToManager
import server


def attach_device_to_manager(
    ws: simple_websocket.Client, mac_address: str, uuid: str
):
    """Attach a device WebSocket to the shell session specified by UUID

    The WebSocket connection that we get here is coming from a device that
    has spawned a shell executable and is now trying to connect to a remote
    manager to send the shell STDOUT and receive user input.
    """
    shell = server.instance.shell_sessions.get(mac_address, UUID(uuid))
    if shell is None:
        print(
            "Attaching device shell failed: shell session with UUID",
            uuid,
            "MAC",
            mac_address,
            "not found",
            flush=True,
        )
        raise WebSocketException(
            "invalid shell session identifier", RDFM_WS_INVALID_REQUEST
        )

    # Signal that a device has connected to the shell
    shell.device_connected.set()

    # Run the copy loop - copy from the device shell socket to the
    # manager socket
    device_mgmt.helpers.bidirectional_copy(ws, shell.manager_socket)

    # Signal the manager websocket to close
    # Otherwise, we could end up leaking connections
    shell.device_connection_closed.set()


def attach_manager_to_shell(ws: simple_websocket.Client, mac_address: str):
    """Handles a shell attach request (coming from the Manager)

    This handles an incoming shell spawn request from a manager.
    A new shell session is created, and a management message is sent to
    the device telling it to connect to the newly created session.
    """
    remote_device = server.instance.remote_devices.get(mac_address)
    if remote_device is None:
        raise WebSocketException(
            f"device {mac_address} not connected to the management WS",
            RDFM_WS_INVALID_REQUEST,
        )

    # Create a shell session
    # Each shell session is identified by the target MAC and a UUID
    shell = ReverseShell(ws, mac_address)
    server.instance.shell_sessions.add(shell)

    print(
        "Reverse shell session",
        shell.uuid,
        "created for MAC",
        mac_address,
        flush=True,
    )
    try:
        # Send a message to the device indicating which shell it should
        # connect to
        try:
            remote_device.send_message(
                DeviceAttachToManager(
                    mac_addr=mac_address, uuid=str(shell.uuid)
                )
            )
        except WebSocketException as e:
            print(
                "Failed to send shell attach message for session",
                shell.uuid,
                "to remote device:",
                e.message,
                flush=True,
            )
            raise WebSocketException(
                f"shell attach request failed: {e.message}", e.status_code
            )

        # Wait for a bit until the device connects to the shell
        if not shell.device_connected.wait(5.0):
            print(
                "Connecting to device shell failed: device did not connect "
                "within 5s",
                flush=True,
            )
            raise WebSocketException(
                "device did not connect within 5s", RDFM_WS_INVALID_REQUEST
            )

        # Once the device has connected, the thread that handles the WS
        # connection handles the process of copying to and from the manager.
        # See above function, `attach_device_to_manager`.
        # In here, we only need to check if the device or the manager
        # have closed the connection.
        while True:
            # Check if the device has closed the connection
            if shell.device_connection_closed.wait(5.0):
                break
            # Check if the manager has closed the connection
            if not shell.manager_socket.connected:
                break
    finally:
        print("Reverse shell session", shell.uuid, "terminated", flush=True)
        server.instance.shell_sessions.remove(shell)
