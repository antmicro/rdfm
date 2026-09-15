import pytest
import os
import tempfile
import random
import requests
import uuid
import time
import jwt
import hashlib
import tempfile
import auth.upload_token
from auth import JWT_ALGO
from configuration import ServerConfig
from storage.local import LocalStorage
from api.v2.devices import MAX_UPLOAD_PART_SIZE
from common import HOSTNAME, PORT


DOWNLOAD_BUCKET_SUBDIR = "test_bucket"
MULTIPART_UPLOAD_FULL_SIZE = int(2.56e+8)
MULTIPART_UPLOAD_DEFAULT_EXPIRY = 3600
TEST_UPLOAD_NAME = "test.dat"


@pytest.fixture(scope="session")
def create_server_configuration(local_package_dir, request) -> ServerConfig:
    config = ServerConfig()
    config.hostname = HOSTNAME
    config.http_port = PORT
    config.package_dir = request.getfixturevalue(local_package_dir)
    return config


@pytest.fixture(scope="session")
def create_local_driver(create_server_configuration) -> LocalStorage:
    return LocalStorage(create_server_configuration)


@pytest.fixture()
def create_multipart_downloader(create_local_driver) -> LocalStorage.MultipartUploader:
    object_name = str(uuid.uuid4())
    return create_local_driver.create_multipart_downloader(f"{DOWNLOAD_BUCKET_SUBDIR}/{object_name}")


@pytest.fixture
def mint_upload_urls(create_multipart_downloader) -> tuple[list[str], int]:
    return create_multipart_downloader.generate_urls(MULTIPART_UPLOAD_FULL_SIZE, MULTIPART_UPLOAD_DEFAULT_EXPIRY)


@pytest.fixture
def mint_upload_token():
    return auth.upload_token.acquire_token(TEST_UPLOAD_NAME, MULTIPART_UPLOAD_DEFAULT_EXPIRY)


@pytest.fixture
def create_artifact_for_upload() -> str:
    tmp_file = tempfile.NamedTemporaryFile(mode="wb")
    tmp_file.write(random.randbytes(MULTIPART_UPLOAD_FULL_SIZE))
    yield tmp_file.name
    os.remove(tmp_file.name)


def test_upload_token_decode_expired():
    token = auth.upload_token.acquire_token("test", 0)
    res = auth.upload_token.decode_and_verify_token(token)
    assert res is None


def test_upload_token_invalid_audience():
    now = int(time.time())
    token_dict = auth.upload_token.UploadToken("test", now, now + 3600, "urn:WRONG").to_dict()
    token = jwt.encode(token_dict, os.environ["JWT_SECRET"], algorithm=JWT_ALGO)
    res = auth.upload_token.decode_and_verify_token(token)
    assert res is None


def test_server_localstorage_simple_put(setup_server, mint_upload_token):
    url = f"http://{HOSTNAME}:{PORT}/local_storage_multipart/parts/{TEST_UPLOAD_NAME}?token={mint_upload_token}"
    resp = requests.put(url, b"\x08\x59")
    assert 200 == resp.status_code, "Authenticated PUT to local storage should be allowed"


def test_server_localstorage_simple_put_expired(setup_server):
    token = auth.upload_token.acquire_token(TEST_UPLOAD_NAME, 0)
    url = f"http://{HOSTNAME}:{PORT}/local_storage_multipart/parts/{TEST_UPLOAD_NAME}?token={token}"
    resp = requests.put(url, b"\x08\x59")
    assert 401 == resp.status_code, "Authenticated but expired PUT should be denied with 401"


def test_server_localstorage_simple_put_invalid_audience(setup_server):
    now = int(time.time())
    token_data = auth.upload_token.UploadToken(TEST_UPLOAD_NAME, now, now + 3600, "urn:WRONG")
    token = jwt.encode(token_data.to_dict(), os.environ["JWT_SECRET"], algorithm=JWT_ALGO)
    url = f"http://{HOSTNAME}:{PORT}/local_storage_multipart/parts/{TEST_UPLOAD_NAME}?token={token}"
    resp = requests.put(url, b"\x08\x59")
    assert 401 == resp.status_code, "PUT with wrong audience should be denied with 401"


def test_server_localstorage_simple_put_name_mismatch(setup_server, mint_upload_token):
    url = f"http://{HOSTNAME}:{PORT}/local_storage_multipart/parts/WRONG_NAME.dat?token={mint_upload_token}"
    resp = requests.put(url, b"\x08\x59")
    assert 403 == resp.status_code, "Authenticated PUT with mismatched resource should be denied with 403"


def test_server_localstorage_unauthenticated_put(setup_server):
    url = f"http://{HOSTNAME}:{PORT}/local_storage_multipart/parts/11111111-1111-1111-1111-111111111111_part0"
    resp = requests.put(url, b"\x08\x59")
    assert 401 == resp.status_code, "Unauthenticated PUT to local storage should be denied with 401"


def test_server_localstorage_directory_traversal_attempt(setup_server, mint_upload_token):
    url = f"http://{HOSTNAME}:{PORT}/local_storage_multipart/parts/..%2f..%2f{TEST_UPLOAD_NAME}?token={mint_upload_token}"
    resp = requests.put(url, b"\x13\x17")
    assert 404 == resp.status_code, "Directory traversal attempt should fail with 404 on resource"


def helper_compute_bytes_per_part(generated_urls: tuple[list[str], int]) -> int:
    # How many URLs were generated?
    n_parts = len(generated_urls[0])

    bytes_per_part = MULTIPART_UPLOAD_FULL_SIZE / n_parts

    # This is a test so it doesn't handle more complex scenarios in which the upload size may be not divisible by the size of parts
    assert bytes_per_part == int(bytes_per_part), "Bytes per part should come out to be an integer"

    return int(bytes_per_part)


def test_server_localstorage_multipart_integrity_ok(setup_server, create_multipart_downloader, mint_upload_urls, create_artifact_for_upload):
    mpu = create_multipart_downloader
    urls = mint_upload_urls[0]
    bytes_per_part = helper_compute_bytes_per_part(mint_upload_urls)

    etags = []

    with open(create_artifact_for_upload, "rb") as f:
        for url in urls:
            data = f.read(bytes_per_part)
            resp = requests.put(url, data)
            assert 200 == resp.status_code, "The part upload should have succeeded"
            assert "Etag" in resp.headers.keys(), "The Etag should be present in upload response"
            etags.append(resp.headers["Etag"])

    mpu.complete_upload(etags)


def test_server_localstorage_multipart_integrity_bad(setup_server, create_multipart_downloader, mint_upload_urls, create_artifact_for_upload):
    mpu = create_multipart_downloader
    urls = mint_upload_urls[0]
    bytes_per_part = helper_compute_bytes_per_part(mint_upload_urls)

    etags = []

    malform = True

    with open(create_artifact_for_upload, "rb") as f:
        for url in urls:
            data = f.read(bytes_per_part)
            resp = requests.put(url, data)

            assert 200 == resp.status_code, "The part upload should have succeeded"
            assert "Etag" in resp.headers.keys(), "The Etag should be present in upload response"

            if malform:
                # Modify one part and recalculate Etag in place to simulate data corruption
                data = bytes_per_part * b"\x11"
                bad_etag = hashlib.sha256(data).hexdigest()
                etags.append(bad_etag)
                malform = False
            else:
                etags.append(resp.headers["Etag"])

    try:
        mpu.complete_upload(etags)
    except RuntimeError:
        pass
    else:
        pytest.fail("Complete upload shouldn't succeed in the case of en Etag mismatch")


def test_server_localstorage_data_over_max_size(setup_server, mint_upload_token):
    url = f"http://{HOSTNAME}:{PORT}/local_storage_multipart/parts/{TEST_UPLOAD_NAME}?token={mint_upload_token}"
    data = (MAX_UPLOAD_PART_SIZE + 1) * b"\xff"
    resp = requests.put(url, data)
    assert 413 == resp.status_code, "PUT request should be rejected because of the exceeding file size"
