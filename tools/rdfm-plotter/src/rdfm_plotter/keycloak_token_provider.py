import datetime
import requests
import json
import time
from kafka.sasl.oauth import AbstractTokenProvider
from authlib.oauth2.rfc6749.wrappers import OAuth2Token
from authlib.integrations.requests_client import OAuth2Session
from typing import Optional


class KeycloakTokenProvider(AbstractTokenProvider):
    _token = Optional[OAuth2Token]
    _client_id: str
    _client_secret: str
    _token_endpoint: str
    _audience: str
    _cafile: Optional[str]
    _leeway: int

    def __init__(self,
                 client_id: str,
                 client_secret: str,
                 token_endpoint: str,
                 audience: str,
                 cacert: Optional[str] = None,
                 leeway: int = 30) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_endpoint = token_endpoint
        self._audience = audience
        self._token = None
        self._cacert = cacert
        self._leeway = leeway

    def token(self) -> str:
        if self._token and isinstance(self._token, OAuth2Token):
            if self._token["expires_at"] > time.time() + self._leeway:
                return self._token["access_token"]
        client = OAuth2Session(client_id=self._client_id, client_secret=self._client_secret)
        if self._cacert:
            client.verify = self._cacert
        self._token = client.fetch_token(self._token_endpoint,
                                         grant_type="urn:ietf:params:oauth:grant-type:uma-ticket",
                                         audience=self._audience)
        return self._token["access_token"]
