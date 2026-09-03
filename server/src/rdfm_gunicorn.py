from gunicorn.workers.ggevent import GeventWorker
from gevent.server import StreamServer
import ssl
import functools


class QuietServer(StreamServer):
    def wrap_socket_and_handle(self, client_socket, address):
        try:
            return super().wrap_socket_and_handle(client_socket, address)
        except ssl.SSLError as e:
            # Ignore SSL errors instead of printing tracebacks
            message = str(e)
            ignored = (
                'sslv3 alert bad certificate',
                'sslv3 alert certificate unknown',
                'tlsv1 alert unknown ca',
                'http request',
                'wrong version number',
            )
            if any(msg in message for msg in ignored):
                return
            raise

    def __init__(self, listener, spawn, ssl_context, **kwargs):
        hfun = functools.partial(__class__.handle, listener)
        super().__init__(listener, handle=hfun, spawn=spawn, ssl_context=ssl_context)


class QuietGeventWorker(GeventWorker):
    # Modified version of gunicorn's gevent worker that suppresses certain errors
    server_class = QuietServer

    def __init__(self, *args, **kwargs):
        __class__.server_class.handle = self.handle
        super().__init__(*args, **kwargs)
