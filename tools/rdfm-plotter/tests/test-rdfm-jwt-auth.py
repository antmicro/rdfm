import pytest
import time
import jwt
import subprocess


# This value is also hardcoded in the associated apptainer definition file
DEVICE_MAC = "00:00:00:00:00:00"


def build_encoded_jwt(secret,
                      expires: int = 100,
                      created_offset: int = 0,
                      device_id: str = DEVICE_MAC):
    return jwt.encode({"device_id": device_id,
                       "created_at": int(time.time()) - created_offset,
                       "expires": expires
                       },
                      secret,
                      algorithm="HS256")


def build_metadata_request_args(bootstrap_server: str,
                                encoded_jwt: str,
                                device_id: str = DEVICE_MAC) -> list[str]:
    return ["kcat",
            "-b", bootstrap_server,
            "-X", "security.protocol=sasl_plaintext",
            "-X", "sasl.mechanism=PLAIN",
            "-X", f"sasl.username={device_id}",
            "-X", f"sasl.password={encoded_jwt}",
            "-L",  # List cluster metadata
            ]


def test_valid(get_rdfm_jwt_secret, broker, dev_endpoint):
    encoded_jwt = build_encoded_jwt(get_rdfm_jwt_secret)
    args = build_metadata_request_args(dev_endpoint, encoded_jwt)
    result = subprocess.run(args)

    assert 0 == result.returncode, "Contacting DEV endpoint with a valid JWT should be successful"


def test_invalid(broker, dev_endpoint):
    encoded_jwt = build_encoded_jwt("this_secret_is_not_correct")
    args = build_metadata_request_args(dev_endpoint, encoded_jwt)
    result = subprocess.run(args)

    assert 1 == result.returncode, ("Contacting DEV endpoint with a JWT created"
                                    " from a wrong secret should fail")


def test_valid_mac_mistmatch(get_rdfm_jwt_secret, broker, dev_endpoint):
    encoded_jwt = build_encoded_jwt(get_rdfm_jwt_secret, device_id="11:11:11:11:11:11")
    args = build_metadata_request_args(dev_endpoint, encoded_jwt, device_id="22:22:22:22:22:22")
    result = subprocess.run(args)

    assert 1 == result.returncode, ("Claiming having a differet MAC address than"
                                    " declared in the JWT should fail")


def test_valid_with_claim_missing(get_rdfm_jwt_secret, broker, dev_endpoint):
    encoded_jwt = jwt.encode({"device_id": DEVICE_MAC,
                              "created_at": int(time.time())
                              #  Missing the "expires" claim
                              },
                             get_rdfm_jwt_secret,
                             algorithm="HS256")
    args = build_metadata_request_args(dev_endpoint, encoded_jwt)
    result = subprocess.run(args)

    assert 1 == result.returncode, "Using a JWT with a missing claim should fail"


def test_valid_expired(get_rdfm_jwt_secret, broker, dev_endpoint):
    encoded_jwt = build_encoded_jwt(get_rdfm_jwt_secret, expires=100, created_offset=110)
    args = build_metadata_request_args(dev_endpoint, encoded_jwt)
    result = subprocess.run(args)

    assert 1 == result.returncode, "Using an expired JWT should fail"


def test_incorrectly_typed_claims(get_rdfm_jwt_secret, broker, dev_endpoint):
    encoded_jwt = jwt.encode({"device_id": DEVICE_MAC,
                              "created_at": str(int(time.time())),
                              "expires": str(100)
                              },
                             get_rdfm_jwt_secret,
                             algorithm="HS256")
    args = build_metadata_request_args(dev_endpoint, encoded_jwt)
    result = subprocess.run(args)

    assert 1 == result.returncode, "Using a JWT with claims being wrongly type should fail"
