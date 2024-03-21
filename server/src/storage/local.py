import uuid
import os
import shutil
import configuration
import urllib.parse
from pathlib import Path, PosixPath

"""Local storage driver, used for debugging purposes
"""

class LocalStorage():
    config: configuration.ServerConfig

    def __init__(self, config: configuration.ServerConfig) -> None:
        self.config = config


    """Updates the contents of the specified package
       This method has upsert semantics - if the specified package does not exist,
       it is created. Otherwise, contents of the package are modified.
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
        metadata["rdfm.storage.local.length"] = os.path.getsize(destination_path)
        metadata["rdfm.storage.local.directory"] = str(
            destination_path.parent.relative_to(storage_location)
        )
        return True


    """Makes a direct HTTP URL to the specified package with given expiration time
       Expiration is in seconds.
    """
    def generate_url(self, metadata: dict[str, str], expiry: int) -> str:
        schema = "http"
        port = self.config.http_port
        if self.config.encrypted:
            schema = "https"
        hostname = self.config.hostname
        storage_path = PosixPath(
            metadata.get('rdfm.storage.local.directory', '.')
        ) / metadata['rdfm.storage.local.uuid']
        path = f"/local_storage/{storage_path}"
        # Expiration time ignored, as local storage is just for debugging
        return urllib.parse.urljoin(f"{schema}://{hostname}:{port}",
                                    path)


    """Deletes the specified package from storage
    """
    def delete(self, metadata: dict[str, str]):
        name = metadata["rdfm.storage.local.uuid"]
        os.remove(
            str(
                Path(self.config.package_dir)
                / metadata.get('rdfm.storage.local.directory', '.')
                / name
            )
        )

