import datetime
import requests
import json
from kafka.sasl.oauth import AbstractTokenProvider
from typing import Optional


class KeycloakTokenProvider(AbstractTokenProvider):
    _token: Optional[str]
    acquire: Optional[datetime.datetime]

    def __init__(self,
                 id: str,
                 secret: str,
                 url: str,
                 audience: str,
                 reauth_margin: int = 15) -> None:
        self.id = id
        self.secret = secret
        self.audience = audience
        self.url = url
        self.reauth = reauth_margin
        self.acquire = None
        self._token = None

    def token(self) -> Optional[str]:
        if self._token is None or self.acquire is None:
            self._token = self.fetch()
        elif self.acquire < datetime.datetime.now():
            self._token = self.fetch()
        return self._token

    def fetch(self) -> Optional[str]:
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:uma-ticket",
            "client_id": self.id,
            "client_secret": self.secret,
            "audience": self.audience
        }
        response = requests.post(self.url, data=data)
        if 200 == response.status_code:
            r = json.loads(response.text)
            expires = r["expires_in"]
            now = datetime.datetime.now()
            self.acquire = (now + datetime.timedelta(seconds=expires - self.reauth)
                            if expires > self.reauth else now)
            return str(r["access_token"]) if r["access_token"] else None
        return None
