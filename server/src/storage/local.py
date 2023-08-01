import uuid
import os
import hashlib
import shutil

"""Local storage driver, used for debugging purposes
"""

LOCAL_STORAGE_PATH: str = "/tmp/.rdfm-local-storage/"

class LocalStorage():
    """Updates the contents of the specified package
       This method has upsert semantics - if the specified package does not exist,
       it is created. Otherwise, contents of the package are modified.
       The metadata of the package is updated. All storage drivers shall use:
            rdfm.storage.<storage-driver-name>.<key>
       metadata keys.
    """
    def upsert(self, metadata: dict[str, str], package_path: str) -> bool:
        # Create the storage directory if it does not exist
        if not os.path.isdir(LOCAL_STORAGE_PATH):
            os.mkdir(LOCAL_STORAGE_PATH)
        print("Local storage update package:", metadata, "path:", package_path)
        store_name = str(uuid.uuid4())
        destination_path = os.path.join(LOCAL_STORAGE_PATH, store_name)
        shutil.copy(package_path, destination_path)

        metadata["rdfm.storage.local.uuid"] = store_name
        metadata["rdfm.storage.local.length"] = os.path.getsize(destination_path)
        return True


    """Makes a direct HTTP link to the specified package with given expiration time
       Expiration is in seconds.
    """
    def generate_link(self, metadata: dict[str, str], expiry: int) -> str:
        # Expiration time ignored, as local storage is just for debugging
        return f"http://127.0.0.1:5000/local_storage/{metadata['rdfm.storage.local.uuid']}"


    """Deletes the specified package from storage
    """
    def delete(self, metadata: dict[str, str]):
        name = metadata["rdfm.storage.local.uuid"]
        os.remove(os.path.join(LOCAL_STORAGE_PATH, name))

