import base64
import time
from typing import Optional, Tuple
import jwt
import os
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature.pkcs1_15 import PKCS115_SigScheme
from models.device import Device
from rdfm.schema.v1.updates import META_MAC_ADDRESS
import server
from auth.token import DeviceToken


""" JWT expiration time (in seconds) """
DEVICE_JWT_EXPIRY = 300
""" Algorithm in call to jwt.{encode,decode} to use. """
DEVICE_JWT_ALGO = "HS256"


def verify_signature(body: bytes, public_key: str, signature: str) -> bool:
    """Verify the device signature of an incoming request

    Args:
        body: bytes that were signed with the given signature.
        public_key: RSA public key (PEM-encoded) corresponding to the private
                    key used during signing.
        signature: base64-encoded signature of the body

    Returns:
        True, if the signature was verified successfully
        False, if:
            - the signature is not valid base64
            - the public key is not a valid PEM RSA key
            - the signature is invalid
    """
    try:
        signature_bytes = base64.b64decode(signature)
        key = RSA.import_key(public_key)
    except Exception as e:
        print("Exception during signature verification:", e)
        return False

    # Hash the message body
    h = SHA256.new(body)
    # Now verify the signature
    s = PKCS115_SigScheme(key)
    # `verify` raises a ValueError on failure
    try:
        s.verify(h, signature_bytes)
    except ValueError:
        print("Exception during signature verification: invalid signature")
        return False

    # Signature is valid
    return True


def verify_authorization(device_id: str, public_key: str) -> bool:
    """Verifies if the device is authorized to access the server.

    This function verifies if the device is actually authorized to access the
    server.
    This must happen after the device was authenticated (by verifying ownership
    of the private key from which the provided public key is derived - see
    `verify_signature`).

    Args:
        device_id: device identifier (i.e, MAC address).
        public_key: RSA public key (PEM-encoded) corresponding to the private
                    key used during signing.
        metadata: metadata reported by the device during the authentication.

    Returns:
        True, if the device is authorized to access the server.
        False, if the device is not yet authorized to access the server.
    """
    # Check if the device is already in the devices database.
    # If not, it needs to be accepted by an administrator first.
    device: Optional[Device] = server.instance._devices_db.get_device_data(
        device_id
    )
    if device is None:
        return False

    # Device was explicitly de-authorized by an administrator
    if device.public_key is None:
        return False

    # If the public key changed, create a new registration entry
    if device.public_key != public_key:
        return False

    # Along with `verify_signature`, at this point we've verified that:
    # - The request sender has possession of the private key corresponding
    #   to the public key reported by the device.
    # - The device was previously authorized by an administrator user
    # - The reported public key matches the one previously accepted by an
    #   administrator. This confirms that the device is authorized to access
    #   the server.
    return True


def try_acquire_token(
    public_key: str, metadata: dict[str, str]
) -> Optional[Tuple[str, DeviceToken]]:
    """Tries acquiring a device token for the specified device.

    This must be called after a successful verification of the device signature
    (see above function: `verify_signature`).
    This checks if the device is authorized to access the server before
    generating a token - if the device is unauthorized, a registration is
    created for the specified MAC address + public key pair.

    Args:
        device_id: device identifier (i.e, MAC address).
        public_key: RSA public key (PEM-encoded) corresponding to the private
                    key used during signing.
        metadata: metadata reported by the device during the authentication.

    Returns:
        None, if the device is unauthorized to access the server.
        Otherwise, returns a tuple containing the JWT token and data stored
        inside the token.
    """
    # If the device is unauthorized, create a registration entry
    device_id: str = metadata[META_MAC_ADDRESS]
    if not verify_authorization(device_id, public_key):
        server.instance._registrations_db.create_registration(
            device_id, public_key, metadata
        )
        return None

    # Device is authorized, we can generate a token now
    token_data = DeviceToken()
    token_data.device_id = device_id
    token_data.created_at = int(time.time())
    token_data.expires = DEVICE_JWT_EXPIRY

    secret = os.environ["JWT_SECRET"]
    token = jwt.encode(token_data.to_dict(), secret, algorithm=DEVICE_JWT_ALGO)
    return token, token_data


def decode_and_verify_token(token: str) -> Optional[DeviceToken]:
    """Decode and verify the validity of a given token

    This can be used to check if a given JWT token string is valid.

    Args:
        token: JWT token string

    Returns:
        None, if the token is invalid in any way (expiration, token format,
        etc.); DeviceToken, if the token is valid. Data contained within the
        token is returned.
    """
    try:
        secret = os.environ["JWT_SECRET"]
        token_data = jwt.decode(token, secret, algorithms=DEVICE_JWT_ALGO)
        device_token = DeviceToken.from_dict(token_data)

        # Check token expiration
        current_time = int(time.time())
        if current_time >= device_token.created_at + device_token.expires:
            return None

        return device_token
    except:     # noqa: E722
        return None
