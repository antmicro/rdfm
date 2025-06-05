from kafka.sasl.oauth import AbstractTokenProvider
import datetime
import requests
import json

AUDIENCE = "kafka-broker-introspection"
KEYCLOAK = "http://keycloak:8080/realms/master/protocol/openid-connect/token"

class KeycloakTokenProvider(AbstractTokenProvider):
    def __init__(self, id, secret, url=KEYCLOAK, audience=AUDIENCE, reauth_margin=15):
        self.id = id
        self.secret = secret
        self.audience = audience
        self.url = url
        self.reauth = reauth_margin
        self.acquire = None
        self._token = None

    def token(self):
        if self._token is None:
            self._token = self.fetch()
        elif self.acquire < datetime.datetime.now():
            self._token = self.fetch()
        return self._token

    def fetch(self):
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
            self.acquire = now + datetime.timedelta(seconds=expires - self.reauth) if expires > self.reauth else now
            print("successfully fetched token", flush=True)
            return r["access_token"]
        return None

if __name__ == "__main__":
    provider = KeycloakTokenProvider("mock-consumer", "WMoI6gQDCVmPkpHiNYLGSzCEowUWpXjz")
    provider.token()
    provider.token()
