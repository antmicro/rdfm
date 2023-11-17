import time
import jwt
from simple_websocket import Client, ConnectionClosed
import pexpect
import threading
from rdfm_mgmt_communication import decode_json
from request_models import CapabilityReport, DeviceAttachToManager, Alert
from rdfm.ws import send_message, receive_message, WebSocketException
from auth.device import DeviceToken, DEVICE_JWT_ALGO


# This is an example implementation of a device client WebSocket loop.
# This performs the following:
#     - Connect to the management WebSocket on the RDFM server
#     - Read incoming messages from the above WebSocket and handle them
# Currently, the only available message is shell attach request.
# Run this script in the server venv:
#   poetry run python tests/scripts/device-websocket-loop.py
# You can use websocat to attach to the shell, for example:
#   websocat -E --ping-timeout 5 --ping-interval 2 -b ws://127.0.0.1:5000/api/v1/devices/00:00:00:00:00:00/shell


SHELL_BUFFER_SIZE = 4096
DATA_WAIT_TIMEOUT = 2.0  # in seconds
SERVER = "127.0.0.1:5000"
# This is the MAC that can be used to connect to the shell of this script
DEVICE_ID = "00:00:00:00:00:00"
# JWT secret, must match the one used for running the server
JWT_SECRET = "foobarbaz"


def create_dummy_token():
    token_data = DeviceToken()
    token_data.device_id = DEVICE_ID
    token_data.created_at = int(time.time())
    token_data.expires = 999999999
    return jwt.encode(token_data.to_dict(), JWT_SECRET, algorithm=DEVICE_JWT_ALGO)


DEVICE_TOKEN = create_dummy_token()
CAPABILITIES = {
    "shell": True
}
AUTH_HEADERS = {
    "Authorization": f"Bearer token={DEVICE_TOKEN}"
}

class ReverseShell():
    """ This implements the reverse shell functionality

    A thread is spawned running /bin/sh, and two other threads
    that handle reading and writing to the shell respectively.
    """
    shell: pexpect.spawn
    ws: Client
    on_exit: threading.Event
    uuid: str


    def __init__(self, ws, uuid) -> None:
         self.shell = None
         self.ws = ws
         self.on_exit = threading.Event()
         self.uuid = uuid


    def _do_copy_stdout_to_websocket(self):
         """ Copy STDOUT from the shell process to the specified WebSocket
         """
         while True:
            try:
                if self.on_exit.is_set():
                    print(self.uuid, "Closing shell reader", flush=True)
                    return

                try:
                    data = self.shell.read_nonblocking(size=SHELL_BUFFER_SIZE, timeout=DATA_WAIT_TIMEOUT)
                except:
                    data = None
                if data is not None and len(data) > 0:
                    print(self.uuid, "STDOUT: Send", data, flush=True)
                    self.ws.send(data)
                    print(self.uuid, "STDOUT SEND DONE", flush=True)
            except Exception as e:
                print(self.uuid, "Shell reader exception:", e, flush=True)
                self.on_exit.set()
                return


    def _do_copy_websocket_to_stdin(self):
        """ Copy input from the WebSocket to STDIN of the shell process
        """
        while True:
            try:
                if self.on_exit.is_set():
                    print(self.uuid, "Closing websocket reader", flush=True)
                    return

                data = self.ws.receive(timeout=DATA_WAIT_TIMEOUT)
                if data is not None:
                     print(self.uuid, "STDIN: Send", data, flush=True)
                     self.shell.write(data)
                     print(self.uuid, "STDIN SEND DONE", flush=True)
            except Exception as e:
                print(self.uuid, "Websocket reader exception:", e, flush=True)
                self.on_exit.set()
                return


    def start(self):
         """ Start the reverse shell
         """
         self.shell = pexpect.spawn("/bin/sh")
         threading.Thread(target=self._do_copy_stdout_to_websocket).start()
         threading.Thread(target=self._do_copy_websocket_to_stdin).start()


    def block_until_exit(self):
        """ Wait for the reverse shell to exit

        This happens if the connection is lost, or the manager has disconnected
        from the shell.
        """
        self.on_exit.wait()
        print("Terminated reverse shell session", self.uuid, flush=True)


def spawn_and_attach_shell(req: DeviceAttachToManager):
    """ Spawn the shell in a separate thread
    """
    ws = Client.connect(f'ws://{SERVER}/api/v1/devices/{req.mac_addr}/shell/attach/{req.uuid}',
                        headers=AUTH_HEADERS)
    rs = ReverseShell(ws, req.uuid)
    rs.start()
    rs.block_until_exit()


def main():
    ws = Client.connect(f'ws://{SERVER}/api/v1/devices/ws', headers=AUTH_HEADERS)
    try:
        # Send capabilities to the server
        send_message(ws, CapabilityReport(
            capabilities=CAPABILITIES,
        ))
        # Main management loop
        while True:
            if not ws.connected:
                print("Connection to the server terminated")
                break

            try:
                message = receive_message(ws)
            except WebSocketException as e:
                print("Receiving message from WS failed:", e, flush=True)
                continue

            match message:
                case DeviceAttachToManager():
                    print("Received shell attach request", flush=True)
                    threading.Thread(target=spawn_and_attach_shell, args=(message,)).start()
                case _:
                    print("Unsupported request:", message, flush=True)

    except (KeyboardInterrupt, EOFError, ConnectionClosed) as e:
        print("Exception during processing:", e, flush=True)
        ws.close()


if __name__ == '__main__':
    main()
