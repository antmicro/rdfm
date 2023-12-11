import multiprocessing
import os

hostname = os.getenv('RDFM_HOSTNAME', '127.0.0.1')
port = os.getenv('RDFM_API_PORT', '5000')
if 'RDFM_DISABLE_ENCRYPTION' not in os.environ:
    certfile = os.getenv('RDFM_SERVER_CERT')
    keyfile = os.getenv('RDFM_SERVER_KEY')
worker_connections = os.getenv('RDFM_WSGI_MAX_CONNECTIONS', 4000)

bind = f"{hostname}:{port}"
# MUST use exactly one worker!
# The server does not currently support being run in multiple workers
workers = 1