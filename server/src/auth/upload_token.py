from typing import Any, Union
from auth import JWT_ALGO
from dataclasses import dataclass
import jwt
import time
import os
import logging

log = logging.getLogger(__name__)


UPLOAD_AUD = "urn:rdfm:api:localstorage:upload"


@dataclass
class UploadToken:
    upload_name: str
    iat: int
    exp: int
    aud: str = UPLOAD_AUD

    def to_dict(self) -> dict[str, Any]:
        return vars(self)

    @classmethod
    def from_dict(cls, dict: dict[str, Any]) -> "UploadToken":
        return UploadToken(**dict)


def acquire_token(upload_name: str, expiry: int) -> bytes:
    now = int(time.time())
    token_data = UploadToken(upload_name, now, now + expiry)
    token = jwt.encode(token_data.to_dict(), os.environ["JWT_SECRET"], algorithm=JWT_ALGO)
    return token


def decode_and_verify_token(token: Union[str, bytes]) -> UploadToken | None:
    try:
        token_data = jwt.decode(token,
                                os.environ["JWT_SECRET"],
                                audience=UPLOAD_AUD,
                                algorithms=JWT_ALGO)
    except Exception as e:
        log.info("Exception during UploadToken decoding: %s", repr(e))
        return None
    token_obj = UploadToken.from_dict(token_data)
    return token_obj
