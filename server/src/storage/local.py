import uuid
import os
import shutil
import configuration
import urllib.parse
from pathlib import Path, PosixPath
from typing import Type
from storage.common import upload_part_count

"""Local storage driver, used for debugging purposes
"""

DESIRED_PART_SIZE = 10 * 2**20


class LocalStorage:
    config: configuration.ServerConfig

    def __init__(self, config: configuration.ServerConfig) -> None:
        self.config = config

    """
    Updates the contents of the specified package
    This method has upsert semantics - if the specified package does not
    exist, it is created. Otherwise, contents of the package are modified.
    The metadata of the package is updated. All storage drivers shall use:
         rdfm.storage.<storage-driver-name>.<key>
    metadata keys.
    """

    def upsert(
        self,
        metadata: dict[str, str],
        package_path: str,
        storage_directory: str | None = None,
    ) -> bool:
        print("Local storage update package:", metadata, "path:", package_path)
        if storage_directory is None:
            storage_directory = "."
        store_name = str(uuid.uuid4())
        destination_path = (
            Path(self.config.package_dir) / storage_directory / store_name
        )
        destination_path = destination_path.resolve()
        storage_location = Path(self.config.package_dir).resolve()
        if not destination_path.is_relative_to(storage_location):
            print(
                f"Destination path {destination_path} is not a subdirectory "
                f"of the local storage ({self.config.package_dir})"
            )
            return False
        # Create the storage directory
        destination_path.parent.mkdir(exist_ok=True, parents=True)
        shutil.copy(package_path, destination_path)

        metadata["rdfm.storage.local.uuid"] = store_name
        metadata["rdfm.storage.local.length"] = os.path.getsize(
            destination_path
        )
        metadata["rdfm.storage.local.directory"] = str(
            destination_path.parent.relative_to(storage_location)
        )
        return True

    """
    Makes a direct HTTP URL to the specified package with given expiration time
    Expiration is in seconds.
    """

    def generate_url(self, metadata: dict[str, str], expiry: int) -> str:
        schema = "http"
        port = self.config.http_port
        if self.config.encrypted:
            schema = "https"
        hostname = self.config.hostname
        storage_path = (
            PosixPath(metadata.get("rdfm.storage.local.directory", "."))
            / metadata["rdfm.storage.local.uuid"]
        )
        path = f"/local_storage/{storage_path}"
        # Expiration time ignored, as local storage is just for debugging
        return urllib.parse.urljoin(f"{schema}://{hostname}:{port}", path)

    """Deletes the specified package from storage
    """

    def delete(self, metadata: dict[str, str]):
        name = metadata["rdfm.storage.local.uuid"]
        os.remove(
            str(
                Path(self.config.package_dir)
                / metadata.get("rdfm.storage.local.directory", ".")
                / name
            )
        )

    class MultipartUploader:
        """Helper class for handling multipart upload"""
        def __init__(self, local_storage, key: str):
            self.local_storage = local_storage
            self.key = key
            self.uploaded = []
            self.part_files = []
            self.final_file = None
            self.part_count = 0
            self.part_size = 0
            pass

        def generate_urls(self, upload_size: int, expiry: int) -> tuple[list[str], int]:
            """
            Returns list of upload urls and upload size for each upload url.
            The amount of upload urls depends on upload_size param
            """
            urls = []
            part_count, part_size = upload_part_count(upload_size, DESIRED_PART_SIZE)
            self.part_count = part_count
            self.part_size = part_size
            hostname = self.local_storage.config.hostname
            port = self.local_storage.config.http_port
            upload_name = str(uuid.uuid4())
            self.final_file = Path(
                self.local_storage.config.package_dir) / "multipart" / f"{self.key}"

            for i in range(part_count):
                self.part_files.append(Path(
                    self.local_storage.config.package_dir) / "multipart" / "parts"
                    / f"{upload_name}_part{i}"
                )
                path = f"/local_storage_multipart/parts/{upload_name}_part{i}"
                urls.append(urllib.parse.urljoin(f"http://{hostname}:{port}", path))

            return urls, part_size

        def complete_upload(self, etags: list[str]):
            """Finalizes the upload - etags param must contain etags returned by each upload"""
            if len(etags) != len(self.part_files):
                return

            for etag, expected_etag in zip(etags, self.part_files):
                if etag != expected_etag.name:
                    return

            self.final_file.parent.mkdir(exist_ok=True, parents=True)
            with open(self.final_file, "wb") as ofile:
                for f in self.part_files:
                    with open(f, "rb") as part_file:
                        ofile.write(part_file.read())

        def abort_upload(self):
            """Terminates the upload"""
            for part_file in self.part_files:
                try:
                    os.remove(part_file)
                except Exception as e:
                    pass

    def create_multipart_downloader(self, key: str) -> Type[MultipartUploader]:
        """Creates multipart downloader"""
        return self.MultipartUploader(self, key)

    def generate_fs_download_url(self, key: str, expiry: int, filename: str | None = None) -> str:
        """Returns download link for given item"""
        hostname = self.config.hostname
        port = self.config.http_port
        path = f"/local_storage_multipart/multipart/{key}"
        return urllib.parse.urljoin(f"http://{hostname}:{port}", path)
