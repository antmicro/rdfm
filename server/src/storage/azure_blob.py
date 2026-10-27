import base64
import datetime
import os
import threading
import urllib.parse
import uuid
import configuration
from azure.core.exceptions import AzureError, ResourceNotFoundError
from azure.storage.blob import (
    BlobBlock,
    BlobSasPermissions,
    BlobServiceClient,
    UserDelegationKey,
    generate_blob_sas,
)
from typing import Any, Optional
from storage.common import upload_part_count


META_AZURE_UUID = "rdfm.storage.azure.uuid"
META_AZURE_SIZE = "rdfm.storage.azure.size"
META_AZURE_DIRECTORY = "rdfm.storage.azure.directory"
DESIRED_PART_SIZE = 10 * 2**20
# Signed links become valid slightly in the past to tolerate clock skew
# between the server and Azure Storage.
SAS_CLOCK_SKEW = datetime.timedelta(minutes=5)
# User delegation keys may be valid for at most 7 days. A fresh key is
# requested once the cached one would expire before a new link does.
DELEGATION_KEY_LIFETIME = datetime.timedelta(days=1)
DELEGATION_KEY_MAX_LIFETIME = datetime.timedelta(days=7)
DELEGATION_KEY_MARGIN = datetime.timedelta(minutes=10)


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class _StorageAccount:
    """Client and link-signing key for one storage account

    The storage driver is instantiated on every request, so everything
    expensive to create (the credential, its tokens and the user delegation
    key) lives here and is shared between driver instances.
    """

    def __init__(self, url: str, name: str, account_key: Optional[str]) -> None:
        self.name = name
        self.account_key = account_key
        if account_key is not None:
            self.client = BlobServiceClient(
                account_url=url,
                credential={"account_name": name, "account_key": account_key},
            )
        else:
            # Imported lazily, so deployments using a shared key don't need it
            from azure.identity import DefaultAzureCredential
            self.client = BlobServiceClient(
                account_url=url, credential=DefaultAzureCredential()
            )
        self._delegation_key: Optional[UserDelegationKey] = None
        self._delegation_key_expiry = _utcnow()
        self._lock = threading.Lock()

    def signing_key(self, valid_until: datetime.datetime) -> dict[str, Any]:
        """Returns the `generate_blob_sas` arguments for signing a link

        With an account key, links are signed with it directly. Otherwise
        they are signed with a user delegation key obtained through
        Microsoft Entra ID, which must outlive the link.
        """
        if self.account_key is not None:
            return {"account_key": self.account_key}

        with self._lock:
            if (
                self._delegation_key is None
                or self._delegation_key_expiry < valid_until + DELEGATION_KEY_MARGIN
            ):
                now = _utcnow()
                lifetime = min(
                    max(DELEGATION_KEY_LIFETIME,
                        valid_until - now + DELEGATION_KEY_MARGIN),
                    DELEGATION_KEY_MAX_LIFETIME,
                )
                self._delegation_key = self.client.get_user_delegation_key(
                    key_start_time=now - SAS_CLOCK_SKEW,
                    key_expiry_time=now + lifetime,
                )
                self._delegation_key_expiry = now + lifetime
            return {"user_delegation_key": self._delegation_key}


_accounts: dict[tuple[str, str, Optional[str]], _StorageAccount] = {}
_accounts_lock = threading.Lock()


def _get_account(config: configuration.ServerConfig) -> _StorageAccount:
    name = config.azure_storage_account
    assert name is not None, "Azure storage account name is required"
    url = config.azure_blob_url or f"https://{name}.blob.core.windows.net"
    key = (url, name, config.azure_account_key)
    with _accounts_lock:
        if key not in _accounts:
            _accounts[key] = _StorageAccount(url, name, config.azure_account_key)
        return _accounts[key]


def _normalize_directory(directory: str | None) -> str:
    """Normalizes a storage directory into a blob name prefix

    Azure treats backslashes as slashes and collapses dot segments, so
    names containing them wouldn't match the signed links generated for
    them. Backslashes are converted, empty segments dropped, and dot
    segments rejected with a ValueError.
    """
    if directory is None:
        return ""
    segments = [s for s in directory.replace("\\", "/").split("/") if s != ""]
    if any(s in (".", "..") for s in segments):
        raise ValueError(f"storage directory must not contain . or .. segments: {directory}")
    return "/".join(segments)


def _attachment(filename: str) -> str:
    """Content-Disposition value making browsers save the file as `filename`"""
    fallback = (
        filename.encode("ascii", "replace").decode("ascii")
        .replace('"', "_").replace("\\", "_")
    )
    encoded = urllib.parse.quote(filename, safe="")
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{encoded}"


class AzureBlobStorage:
    """Storage driver for storing packages on Azure Blob Storage"""

    def __init__(self, config: configuration.ServerConfig) -> None:
        """Initialize the Azure Blob Storage driver

        The server configuration is expected to contain the storage
        account and container names. Without an account key, the server
        authenticates using `DefaultAzureCredential` (for example, a managed
        identity), which needs the Storage Blob Data Contributor role on the
        container. Optionally, an override for the endpoint URL can be
        present, for example to use the Azurite emulator.
        """
        assert config.azure_container is not None, "Azure container name is required"
        self.account = _get_account(config)
        self.container: str = config.azure_container
        self.container_client = self.account.client.get_container_client(self.container)

    @staticmethod
    def get_object_path(directory: str | None, object_id: str) -> str:
        if directory is None or directory == "":
            return object_id
        else:
            return directory + "/" + object_id

    def _signed_url(self, blob_name: str, permission: BlobSasPermissions,
                    expiry: int, **kwargs: Any) -> str:
        """Returns a URL to the blob signed with a SAS token"""
        now = _utcnow()
        expires = now + datetime.timedelta(seconds=expiry)
        sas = generate_blob_sas(
            account_name=self.account.name,
            container_name=self.container,
            blob_name=blob_name,
            permission=permission,
            start=now - SAS_CLOCK_SKEW,
            expiry=expires,
            **self.account.signing_key(expires),
            **kwargs,
        )
        return self.container_client.get_blob_client(blob_name).url + "?" + sas

    def upsert(
        self,
        metadata: dict[str, str],
        package_path: str,
        directory: str | None = None,
    ) -> bool:
        """Updates the contents of the package specified by `metadata`"""
        try:
            directory = _normalize_directory(directory)
        except ValueError as e:
            print("Uploading package failed:", e, flush=True)
            return False

        try:
            # Generate a unique object identifier
            object_id = str(uuid.uuid4())
            print(
                "Uploading package with metadata:",
                metadata,
                "object ID:",
                object_id,
                flush=True,
            )
            with open(package_path, "rb") as f:
                self.container_client.upload_blob(
                    AzureBlobStorage.get_object_path(directory, object_id),
                    f,
                    overwrite=True,
                )
            # Finally, save metadata about the stored object
            metadata[META_AZURE_UUID] = object_id
            # Stored as a number, as the S3 driver does
            metadata[META_AZURE_SIZE] = os.path.getsize(package_path)  # type: ignore[assignment]
            metadata[META_AZURE_DIRECTORY] = directory
            return True
        except AzureError as e:
            print(
                "Uploading package to container",
                self.container,
                "failed:",
                e,
                flush=True,
            )
            return False

    def generate_url(self, metadata: dict[str, str], expiry: int) -> str:
        """Generate a signed URL to the package specified by `metadata`"""
        try:
            # This shouldn't happen
            object_id = metadata.get(META_AZURE_UUID, None)
            if object_id is None:
                raise RuntimeError(
                    "Package does not have the required Azure storage metadata:",
                    META_AZURE_UUID,
                )
            directory = metadata.get(META_AZURE_DIRECTORY, None)

            return self._signed_url(
                AzureBlobStorage.get_object_path(directory, object_id),
                BlobSasPermissions(read=True),
                expiry,
            )
        except AzureError as e:
            print("Failed to generate signed Azure link:", e, flush=True)
            raise

    def delete(self, metadata: dict[str, str]) -> None:
        """Deletes the specified package from storage"""
        try:
            # This shouldn't happen
            object_id = metadata.get(META_AZURE_UUID, None)
            if object_id is None:
                print(
                    "WARNING: Deleting a package that does not have Azure object "
                    "metadata!",
                    flush=True,
                )
                return
            directory = metadata.get(META_AZURE_DIRECTORY, None)

            self.container_client.delete_blob(
                AzureBlobStorage.get_object_path(directory, object_id)
            )
        except ResourceNotFoundError:
            print("WARNING: Deleted package object was already gone", flush=True)
        except AzureError as e:
            print("Failed deleting package object from Azure:", e, flush=True)
            raise

    class MultipartUploader:
        """Helper class for handling multipart upload

        Azure has no multipart upload sessions. Each upload URL is a write
        SAS link to the blob with `comp=block&blockid=<id>` appended, so a
        plain PUT to it stages one block (Put Block). `complete_upload()`
        commits the blocks in order (Put Block List). Blocks that are never
        committed are discarded by Azure after 7 days, so aborting an upload
        needs no request.
        """

        def __init__(self, storage: "AzureBlobStorage", key: str) -> None:
            self.storage = storage
            self.key = key
            self.part_count = 0

        @staticmethod
        def block_id(index: int) -> str:
            """Block ID of the part at `index`

            All block IDs of a blob must have the same length. The SDK
            base64-encodes the IDs it sends when committing.
            """
            return f"{index:06d}"

        def generate_urls(self, upload_size: int, expiry: int) -> tuple[list[str], int]:
            """
            Returns list of upload urls and upload size for each upload url.
            The amount of upload urls depends on upload_size param
            """
            part_count, part_size = upload_part_count(upload_size, DESIRED_PART_SIZE)
            try:
                url = self.storage._signed_url(
                    self.key, BlobSasPermissions(write=True), expiry
                )
            except AzureError as e:
                print("Failed to generate signed Azure link:", e, flush=True)
                raise

            self.part_count = part_count
            urls = []
            for i in range(part_count):
                encoded_id = base64.b64encode(self.block_id(i).encode()).decode()
                urls.append(
                    url + "&comp=block&blockid=" + urllib.parse.quote(encoded_id, safe="")
                )
            return urls, part_size

        def complete_upload(self, etags: list[str]) -> None:
            """Finalizes the upload

            Put Block returns no ETag, so the ETags reported by the device
            are only used to check that every part was attempted.
            """
            if len(etags) != self.part_count:
                print(
                    "WARNING: Device reported",
                    len(etags),
                    "uploaded parts, expected",
                    self.part_count,
                    flush=True,
                )
            try:
                self.storage.container_client.get_blob_client(self.key).commit_block_list(
                    [BlobBlock(block_id=self.block_id(i)) for i in range(self.part_count)]
                )
            except AzureError as e:
                # Devices don't check the status of their part uploads, so a
                # failed part only shows up here as a missing block.
                print(
                    "Failed to commit multipart upload of",
                    self.key,
                    "- a part upload from the device probably failed:",
                    e,
                    flush=True,
                )
                raise

        def abort_upload(self) -> None:
            """Terminates the upload

            Nothing to do: uncommitted blocks are discarded by Azure.
            """
            pass

    def create_multipart_downloader(self, key: str) -> MultipartUploader:
        """Creates multipart downloader"""
        return self.MultipartUploader(self, key)

    def generate_fs_download_url(self, key: str, expiry: int, filename: str | None = None) -> str:
        """Returns download link for given item"""
        try:
            kwargs: dict[str, Any] = {}
            if filename is not None:
                kwargs["content_disposition"] = _attachment(filename)
            return self._signed_url(key, BlobSasPermissions(read=True), expiry, **kwargs)
        except AzureError as e:
            print("Failed to generate signed Azure link:", e, flush=True)
            raise

    def upload_action_log(
        self,
        content: bytes,
        storage_directory: str,
        object_id: str,
    ) -> bool:
        """Uploads file containg action execution log"""
        try:
            self.container_client.upload_blob(
                AzureBlobStorage.get_object_path(storage_directory, object_id),
                content,
                overwrite=True,
            )
            return True
        except AzureError as e:
            print(
                "Uploading action log to container",
                self.container,
                "failed:",
                e,
                flush=True,
            )
            return False
