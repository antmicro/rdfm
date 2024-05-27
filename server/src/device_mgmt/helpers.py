import simple_websocket
import threading


# Timeout for reading from the WebSocket
# Lowering this value will decrease the time it takes
# for a closed WS connection to be cleaned up, but it
# may increase the server load when a lot of shell
# sessions are open.
WS_READ_TIMEOUT = 5.0

# WebSocket ping interval, in seconds
# This is the time between the WebSocket pings
# used to detect device disconnections
WS_PING_INTERVAL = 25.0


class CopierThread:
    """Used for threaded copying of data from one WebSocket to another

    This allows us to implement bidirectional transfer of data between
    two WebSockets.
    Synchronization between the RX/TX is achieved using the `conn_died`
    Event variable.
    """

    source: simple_websocket.Client
    destination: simple_websocket.Client
    connection_died: threading.Event

    def __init__(
        self,
        source: simple_websocket.Client,
        destination: simple_websocket.Client,
        conn_died: threading.Event,
    ) -> None:
        self.source = source
        self.destination = destination
        self.connection_died = conn_died

    def _do_copy(self):
        while True:
            try:
                if self.connection_died.is_set():
                    return

                data = self.source.receive(WS_READ_TIMEOUT)
                if data is not None:
                    self.destination.send(data)
            except simple_websocket.errors.ConnectionClosed:
                self.connection_died.set()
                return

    def start(self):
        """Start the copier thread"""
        threading.Thread(target=self._do_copy).start()


def bidirectional_copy(
    first: simple_websocket.Client, second: simple_websocket.Client
):
    """Bidirectionally copies data between two websockets

    All data read from `first` is sent into `second` and vice versa.
    This function will block until one of the involved parties is disconnected,
    or an exception occurs.
    """
    on_connection_dead = threading.Event()
    A = CopierThread(first, second, on_connection_dead)
    B = CopierThread(second, first, on_connection_dead)
    A.start()
    B.start()
    on_connection_dead.wait()
