from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Signature.pkcs1_15 import PKCS115_SigScheme
import requests
import time
import json
import base64

# This is a reference script for sending a valid device authorization request
# Some key notes:
#   - Signature type is RSASSA-PKCS1-V1_5-SIGN
#   - The server expects a PEM-encoded public key in the `public_key` field.
#   - Make sure the request payload isn't modified in any way after calculating
#     the signature, as that would invalidate it.

SERVER = "http://127.0.0.1:5000"
AUTH = f"{SERVER}/api/v1/auth/device"
METADATA = {
    "rdfm.software.version": "v0",
    "rdfm.hardware.devtype": "dummy",
    "rdfm.hardware.macaddr": "00:00:00:00:00:00"
}

key_pair = RSA.generate(bits=1024)
payload = {
    "metadata": METADATA,
    "public_key": key_pair.public_key().export_key("PEM").decode("utf-8"),
    "timestamp": int(time.time())
}
payload_bytes = json.dumps(payload).encode("utf-8")

h = SHA256.new(payload_bytes)
s = PKCS115_SigScheme(key_pair)
signature = s.sign(h)
signature_b64 = base64.b64encode(signature)

response = requests.post(AUTH,
                         data=payload_bytes,
                         headers={
                            "Content-Type": "application/json",
                            "X-RDFM-Device-Signature": signature_b64,
                         })
print("Status code:", response.status_code)
print("Response body:", response.content)
