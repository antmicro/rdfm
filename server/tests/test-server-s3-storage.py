import tempfile
import pytest
import boto3
import urllib.parse
from moto import mock_s3
from configuration import ServerConfig


TEST_BUCKET_NAME = 'rdfm-packages'
# The contents of the metadata is irrelevant to this test
TEST_PACKAGE_META = {
    "rdfm.software.version": "v0",
    "rdfm.hardware.devtype": "dummy"
}
TEST_EXPIRY_TIME = 600


@pytest.fixture(autouse=True)
def start_s3_mock():
    """ Fixture to start the S3 mock

    Instead of using the `mock_s3` decorator, this fixture is used
    to provide a way of persisting state between fixture invocations.
    Without it, requesting multiple fixtures with the `mock_s3` decorator
    won't persist any data between the calls.
    """
    mock = mock_s3()
    mock.start()
    yield None
    mock.stop()


@pytest.fixture
def create_server_configuration() -> ServerConfig:
    """ Creates a dummy server configuration to use for the driver instance
    """
    config = ServerConfig()
    # The endpoint must not be overridden for the mock to work!
    config.s3_url = None
    # The secrets don't matter, the bucket name is important however
    config.s3_access_key_id = 'DUMMY'
    config.s3_secret_access_key = 'DUMMY'
    config.s3_region_name = 'DUMMY'
    config.s3_use_v4_signature = False
    config.s3_bucket_name = TEST_BUCKET_NAME
    return config


@pytest.fixture
def create_driver(create_server_configuration):
    # The module must be imported after the `mock_s3` decorator
    from storage.s3 import S3Storage
    return S3Storage(create_server_configuration)


@pytest.fixture
def create_dummy_temp_file():
    """ Creates a file to use as the "package" that will be uploaded

    The file will be deleted after the test is done
    """
    with tempfile.NamedTemporaryFile('wb+') as f:
        yield f.name


@pytest.fixture
def metadata():
    """ Creates dummy metadata to use during package upload

    The contents are irrelevant to the test, but the dictionary
    is modified after a call to `upsert()`, which is why this
    is a copy.
    """
    return TEST_PACKAGE_META.copy()


@pytest.fixture(
    scope="function",
    params=[None, "/test", "test", "test/", "test/a/b", "test/../c", "../../../test", "test\\test"]
)
def upload_dummy(create_driver, create_dummy_temp_file, metadata, request):
    # The module must be imported after the `mock_s3` decorator
    # The self-assignment is only for type hints, as we can't
    # put the type in the arguments because the module hasn't
    # been imported yet
    from storage.s3 import S3Storage
    create_driver: S3Storage = create_driver
    s3_dir = request.param

    boto3.client('s3').create_bucket(Bucket=TEST_BUCKET_NAME)

    create_driver.upsert(metadata, create_dummy_temp_file, s3_dir)
    return metadata


@pytest.fixture
def generate_link_to_dummy(upload_dummy: dict[str, str],
                           create_driver):
    """ Uploads a dummy package, and generates a link to the
        newly uploaded package.
    """
    from storage.s3 import S3Storage
    create_driver: S3Storage = create_driver

    return create_driver.generate_url(upload_dummy, TEST_EXPIRY_TIME)


@pytest.fixture
def delete_dummy(upload_dummy: dict[str, str],
                 create_driver):
    """ Uploads a dummy package, then deletes it afterwards.
    """
    from storage.s3 import S3Storage
    create_driver: S3Storage = create_driver

    create_driver.delete(upload_dummy)
    # Return the metadata of the package to test if the object
    # was actually deleted
    return upload_dummy


@pytest.fixture
def list_test_bucket_contents():
    """ List names/keys of objects contained in the test bucket (`TEST_BUCKET_NAME`).
    """
    s3 = boto3.client('s3')
    objects = s3.list_objects(Bucket=TEST_BUCKET_NAME)
    # Empty buckets don't have a `Contents` field.
    if 'Contents' not in objects:
        return []
    return [x['Key'] for x in objects['Contents']]


def test_package_uploaded_successfully(upload_dummy: dict[str, str],
                                       list_test_bucket_contents):
    """ Test if uploading a package using the storage driver actually works

    After upload, the test bucket should contain the uploaded package.
    """
    from storage.s3 import META_S3_UUID, META_S3_DIRECTORY
    # Extract the object name from the package metadata
    if upload_dummy[META_S3_DIRECTORY] != "":
        object_name = upload_dummy[META_S3_DIRECTORY] + "/" + upload_dummy[META_S3_UUID]
    else:
        object_name = upload_dummy[META_S3_UUID]

    assert object_name in list_test_bucket_contents, "the package should have been uploaded to the bucket successfully"


def test_generate_package_link(generate_link_to_dummy):
    """ Test if generating links for a package works properly

    Unfortunately with this mock we can't check if the package is actually
    accessible, however we can check if the generation itself does not throw
    any unexpected errors, or if the generated link is an obviously invalid one.
    """
    assert isinstance(generate_link_to_dummy, str), "return value from the driver should be a string"
    assert len(generate_link_to_dummy) > 0, "generated link should not be an empty string"

    scheme = urllib.parse.urlparse(generate_link_to_dummy).scheme
    assert scheme in ['http', 'https'], "generated link should be of HTTP or HTTPS schema"


def test_delete_package(delete_dummy: dict[str, str],
                        list_test_bucket_contents):
    """ Test if deleting a package after uploading it works properly.

    The object should no longer exist after deleting it using the driver.
    """
    assert len(list_test_bucket_contents) == 0, "the test bucket should be empty after deleting the uploaded package"
