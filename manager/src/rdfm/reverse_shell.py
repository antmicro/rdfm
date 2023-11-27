import signal
import simple_websocket
import threading
import sys
import tty
import termios
import select
import subprocess
import os
from rdfm.helpers import replace_http_schema_with_ws
from typing import Optional
from wsproto.frame_protocol import CloseReason
from rdfm.api import wrap_api_error
import urllib
import rdfm.ws


def shell_ws_url(server_url: str,
                 device: str) -> str:
    """ Create a shell WS URL for the specified device MAC
    """
    ws_url = replace_http_schema_with_ws(server_url)
    path = f"/api/v1/devices/{device}/shell"
    url = urllib.parse.urljoin(ws_url,
                               urllib.parse.quote(path))
    return url


def format_ws_error(status: int,
                    message: Optional[str]) -> str:
    """ Convert a WS status code and message to an error string
    """
    err: str = ""
    match status:
        # Standard WS error codes
        case CloseReason.NORMAL_CLOSURE:
            err = "device disconnected"
        case CloseReason.ABNORMAL_CLOSURE:
            err = "server closed connection abnormally"
        case CloseReason.NO_STATUS_RCVD:
            err = "lost connection to the server"
        case CloseReason.TLS_HANDSHAKE_FAILED:
            err = "server TLS handshake failed"
        # RDFM-specific error codes
        case rdfm.ws.RDFM_WS_UNAUTHORIZED:
            err = "unauthorized to access the WebSocket"
        case rdfm.ws.RDFM_WS_INVALID_REQUEST:
            err = "invalid request"
        case rdfm.ws.RDFM_WS_MISSING_CAPABILITIES:
            err = "device does not provide the required capabilities"
        case _:
            err = f"unexpected status code {status}"

    if message is not None and len(message) > 0:
        err += f" (message: {message})"

    return err


class ReverseShell():
    ws: simple_websocket.Client
    reader_thread: threading.Thread
    writer_thread: threading.Thread
    closed: threading.Event


    def __init__(self, server_url: str, device: str, auth_header: Optional[str] = None) -> None:
        """ Initialize the reverse shell connection

        Connect to the device shell WebSocket and prepare worker threads.

        Args:
            server_url:  URL to the RDFM server, assumed to be a regular
                         HTTP schema URL
            device:      MAC address of the device to attach to
            auth_header: Optional Authorization header to attach to the WS
                         handshake request
        """
        extra_headers = None
        if auth_header is not None:
            extra_headers = {
                "Authorization": auth_header
            }

        try:
            self.ws = simple_websocket.Client.connect(shell_ws_url(server_url, device),
                                                      headers=extra_headers)
        except simple_websocket.ConnectionError as e:
            raise RuntimeError(wrap_api_error(e, "WebSocket connection failed"))

        self.closed = threading.Event()
        self.reader_thread = threading.Thread(target=self.__reader_thread, daemon=True)
        self.writer_thread = threading.Thread(target=self.__writer_thread, daemon=True)


    def __reader_thread(self):
        """ WebSocket reader thread

        This reads from the WebSocket and writes to STDOUT
        """
        try:
            while True:
                data = self.ws.receive()
                if data is not None:
                    sys.stdout.buffer.write(data)
                    sys.stdout.flush()
        except (simple_websocket.ConnectionClosed, simple_websocket.ConnectionError):
            self.closed.set()


    def __writer_thread(self):
        """ STDIN reader thread

        This reads user input from STDIN and sends it to the shell WS
        """
        try:
            while True:
                # Avoid blocking on readline(). Otherwise, when the connection is
                # already closed, the writer thread will be blocked in a kernel
                # call to read(). By avoiding the read call until we know data is
                # there, we can avoid an annoying input prompt when rdfm-mgmt is closing.
                # FIXME: select does not allow for monitoring file fd's on Windows
                r, _, _ = select.select([sys.stdin.fileno()], [], [], 1.0)
                if len(r) > 0:
                    data = sys.stdin.readline()
                    if len(data) == 0:
                        break
                    self.ws.send(data.encode())
                if self.closed.is_set():
                    break
        finally:
            self.closed.set()


    def run(self):
        """ Run the reverse shell

        This function will block until the reverse shell is terminated (either
        by the server/device disconnecting, or user interrupting with Ctrl-C/Ctrl-D).
        """
        self.reader_thread.start()
        self.writer_thread.start()

        try:
            self.closed.wait()
        except:
            pass

        if self.ws.connected:
            # Normal exit (Ctrl-C / EOF on STDIN)
            self.ws.close()
        else:
            # We were forcibly disconnected from the WS
            err = format_ws_error(self.ws.close_reason, self.ws.close_message)
            raise RuntimeError(f"WebSocket connection closed: {err}")
