import socket
import json
import sys
import ssl
import time
from request_models import *

from typing import Optional, cast


def decode_json(to_decode: bytes) -> Request | int:
    """Decodes json received from the tcp socket, without header

    Args:
        to_decode: Encoded json

    Returns:
        Decoded json to request or int (header with msg length)
    """
    decoded = to_decode.decode('utf-8').strip()
    if decoded.isnumeric():
        return int(decoded)
    else:
        decoded = Container.model_validate({
            'data': json.loads(to_decode)
        }).data

        return decoded
