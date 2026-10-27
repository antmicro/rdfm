import datetime
import os
import tempfile
import uuid
import pytest
import requests
from azure.storage.blob import BlobServiceClient
from configuration import ServerConfig


# Azurite (the Azure Storage emulator) must be running, for example:
#   docker run -p 10000:10000 mcr.microsoft.com/azure-storage/azurite \
#       azurite-blob --blobHost 0.0.0.0 --skipApiVersionCheck
AZURITE_URL = os.environ.get(
    "RDFM_TEST_AZURITE_URL", "http://127.0.0.1:10000/devstoreaccount1"
)
# Well-known development account of Azurite
AZURITE_ACCOUNT = "devstoreaccount1"
AZURITE_KEY = (
    "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsu"
    "Fq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=="
)
# The contents of the metadata is irrelevant to this test
TEST_PACKAGE_META = {
    "rdfm.software.version": "v0",
    "rdfm.hardware.devtype": "dummy"
}
TEST_PACKAGE_CONTENT = b"rdfm test package\n" * 1000
TEST_EXPIRY_TIME = 600


@pytest.fixture
def container() -> str:
    """ Creates a fresh blob container for each test and removes it afterwards
    """
    client = BlobServiceClient(
        account_url=AZURITE_URL,
        credential={"account_name": AZURITE_ACCOUNT, "account_key": AZURITE_KEY},
    )
    name = "rdfm-test-" + uuid.uuid4().hex[:12]
    client.create_container(name)
    yield name
    client.delete_container(name)


@pytest.fixture
def container_client(container):
    return BlobServiceClient(
        account_url=AZURITE_URL,
        credential={"account_name": AZURITE_ACCOUNT, "account_key": AZURITE_KEY},
    ).get_container_client(container)


@pytest.fixture
def create_server_configuration(container) -> ServerConfig:
    """ Creates a dummy server configuration to use for the driver instance
    """
    config = ServerConfig()
    config.azure_storage_account = AZURITE_ACCOUNT
    config.azure_account_key = AZURITE_KEY
    config.azure_blob_url = AZURITE_URL
    config.azure_container = container
    return config


@pytest.fixture
def create_driver(create_server_configuration):
    from storage.azure_blob import AzureBlobStorage
    return AzureBlobStorage(create_server_configuration)


@pytest.fixture
def create_dummy_temp_file():
    """ Creates a file to use as the "package" that will be uploaded

    The file will be deleted after the test is done
    """
    with tempfile.NamedTemporaryFile('wb+') as f:
        f.write(TEST_PACKAGE_CONTENT)
        f.flush()
        yield f.name


@pytest.fixture
def metadata():
    """ Creates dummy metadata to use during package upload

    The dictionary is modified after a call to `upsert()`, which is why
    this is a copy.
    """
    return TEST_PACKAGE_META.copy()


@pytest.fixture(
    scope="function",
    params=[None, "", "test", "test/a/b", "/test", "test/", "test//a", "test\\test"]
)
def upload_dummy(create_driver, create_dummy_temp_file, metadata, request):
    assert create_driver.upsert(metadata, create_dummy_temp_file, request.param)
    return metadata


def list_blobs(container_client) -> list[str]:
    return [b.name for b in container_client.list_blobs()]


def test_package_uploaded_successfully(upload_dummy, container_client):
    """ Uploading a package stores it under <directory>/<uuid> and records
        the object in the package metadata.
    """
    from storage.azure_blob import (
        META_AZURE_UUID, META_AZURE_DIRECTORY, META_AZURE_SIZE
    )
    if upload_dummy[META_AZURE_DIRECTORY] != "":
        object_name = upload_dummy[META_AZURE_DIRECTORY] + "/" + upload_dummy[META_AZURE_UUID]
    else:
        object_name = upload_dummy[META_AZURE_UUID]

    assert list_blobs(container_client) == [object_name]
    assert upload_dummy[META_AZURE_SIZE] == len(TEST_PACKAGE_CONTENT)
    assert container_client.download_blob(object_name).readall() == TEST_PACKAGE_CONTENT


@pytest.mark.parametrize("directory,expected", [
    (None, ""),
    ("/test/", "test"),
    ("test//a", "test/a"),
    ("test\\test", "test/test"),
])
def test_directory_is_normalized(create_driver, create_dummy_temp_file, metadata,
                                 directory, expected):
    """ The stored directory matches the blob name Azure actually uses
    """
    from storage.azure_blob import META_AZURE_DIRECTORY
    assert create_driver.upsert(metadata, create_dummy_temp_file, directory)
    assert metadata[META_AZURE_DIRECTORY] == expected


@pytest.mark.parametrize("directory", ["test/../c", "../../../test", "./test"])
def test_directory_with_dot_segments_is_rejected(create_driver, create_dummy_temp_file,
                                                 metadata, container_client, directory):
    """ Dot segments would be collapsed by Azure, so the upload is refused
    """
    assert not create_driver.upsert(metadata, create_dummy_temp_file, directory)
    assert list_blobs(container_client) == []


def test_generate_package_link(upload_dummy, create_driver):
    """ The generated link downloads the package without any credentials
    """
    link = create_driver.generate_url(upload_dummy, TEST_EXPIRY_TIME)

    response = requests.get(link)
    assert response.status_code == 200
    assert response.content == TEST_PACKAGE_CONTENT


def test_package_link_is_read_only(upload_dummy, create_driver):
    """ A package link can't be used to overwrite the package
    """
    link = create_driver.generate_url(upload_dummy, TEST_EXPIRY_TIME)

    response = requests.put(link, data=b"evil", headers={"x-ms-blob-type": "BlockBlob"})
    assert response.status_code == 403


def test_delete_package(upload_dummy, create_driver, container_client):
    """ Deleting a package removes its object; deleting it again is harmless
    """
    create_driver.delete(upload_dummy)
    assert list_blobs(container_client) == []

    create_driver.delete(upload_dummy)


def upload_parts_like_a_device(urls: list[str], part_size: int, content: bytes) -> list[str]:
    """ Mimics the device client (devices/linux-client/daemon/device.go):
        a plain PUT of each part with no extra headers, collecting the Etag
        header and ignoring the status code.
    """
    etags = []
    for i, url in enumerate(urls):
        part = content[i * part_size:(i + 1) * part_size]
        response = requests.put(url, data=part)
        etags.append(response.headers.get("Etag", ""))
    return etags


def test_multipart_upload(create_driver, container_client):
    """ A device-style multipart upload produces the original file, and the
        download link saves it under the requested file name.
    """
    from storage.azure_blob import DESIRED_PART_SIZE
    content = os.urandom(2 * DESIRED_PART_SIZE + 1234)
    key = "rdfm.downloads/" + str(uuid.uuid4())

    mpu = create_driver.create_multipart_downloader(key)
    urls, part_size = mpu.generate_urls(len(content), TEST_EXPIRY_TIME)
    assert len(urls) == 3
    assert part_size == DESIRED_PART_SIZE

    etags = upload_parts_like_a_device(urls, part_size, content)
    mpu.complete_upload(etags)

    link = create_driver.generate_fs_download_url(key, TEST_EXPIRY_TIME, "syslog.1")
    response = requests.get(link)
    assert response.status_code == 200
    assert response.content == content
    assert 'filename="syslog.1"' in response.headers["Content-Disposition"]


def test_multipart_upload_missing_part_fails(create_driver, container_client):
    """ If a part upload fails silently on the device, committing the upload
        fails instead of producing a truncated file.
    """
    from storage.azure_blob import DESIRED_PART_SIZE
    content = os.urandom(DESIRED_PART_SIZE + 10)
    key = "rdfm.downloads/" + str(uuid.uuid4())

    mpu = create_driver.create_multipart_downloader(key)
    urls, part_size = mpu.generate_urls(len(content), TEST_EXPIRY_TIME)
    upload_parts_like_a_device(urls[:1], part_size, content)

    with pytest.raises(Exception):
        mpu.complete_upload(["", ""])
    assert list_blobs(container_client) == []


def test_aborted_multipart_upload_leaves_nothing(create_driver, container_client):
    """ Aborting an upload leaves no committed blob behind
    """
    key = "rdfm.downloads/" + str(uuid.uuid4())
    mpu = create_driver.create_multipart_downloader(key)
    urls, part_size = mpu.generate_urls(100, TEST_EXPIRY_TIME)
    upload_parts_like_a_device(urls, part_size, b"x" * 100)

    mpu.abort_upload()
    assert list_blobs(container_client) == []


def test_upload_action_log(create_driver):
    """ Action logs are stored and downloadable under the execution ID
    """
    object_id = str(uuid.uuid4())
    assert create_driver.upload_action_log(b"action output\n", "rdfm.actions", object_id)

    link = create_driver.generate_fs_download_url(
        f"rdfm.actions/{object_id}", TEST_EXPIRY_TIME, "execution-42"
    )
    response = requests.get(link)
    assert response.status_code == 200
    assert response.content == b"action output\n"
    assert 'filename="execution-42"' in response.headers["Content-Disposition"]


def test_attachment_header_escapes_filename():
    """ Quotes and non-ASCII characters can't break the header
    """
    from storage.azure_blob import _attachment
    header = _attachment('we"ird ñame.txt')
    assert header == (
        'attachment; filename="we_ird ?ame.txt"; '
        "filename*=UTF-8''we%22ird%20%C3%B1ame.txt"
    )


class FakeBlobServiceClient:
    """ Records requests for user delegation keys """

    def __init__(self):
        self.requests = []

    def get_user_delegation_key(self, key_start_time, key_expiry_time):
        self.requests.append((key_start_time, key_expiry_time))
        return f"key-{len(self.requests)}"


def test_user_delegation_key_is_cached_and_refreshed():
    """ Without an account key, links are signed with a user delegation key
        that is reused until it would expire before a new link does.
    """
    from storage.azure_blob import _StorageAccount, DELEGATION_KEY_LIFETIME
    account = _StorageAccount.__new__(_StorageAccount)
    account.name = "dummy"
    account.account_key = None
    account.client = FakeBlobServiceClient()
    account._delegation_key = None
    account._delegation_key_expiry = datetime.datetime.now(datetime.timezone.utc)
    import threading
    account._lock = threading.Lock()

    now = datetime.datetime.now(datetime.timezone.utc)
    hour = datetime.timedelta(hours=1)

    assert account.signing_key(now + hour) == {"user_delegation_key": "key-1"}
    assert account.signing_key(now + hour) == {"user_delegation_key": "key-1"}
    assert len(account.client.requests) == 1
    start, expiry = account.client.requests[0]
    assert start < now
    assert expiry - now >= DELEGATION_KEY_LIFETIME - datetime.timedelta(seconds=5)

    # A link outliving the cached key gets a new, long enough key
    assert account.signing_key(now + 2 * DELEGATION_KEY_LIFETIME) == {
        "user_delegation_key": "key-2"
    }
    assert account.client.requests[1][1] > now + 2 * DELEGATION_KEY_LIFETIME
