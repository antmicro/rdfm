import uuid
import os
import shutil
import configuration
import urllib.parse
import boto3
import boto3.session
from botocore.exceptions import ClientError


META_S3_UUID = "rdfm.storage.s3.uuid"
META_S3_SIZE = "rdfm.storage.s3.size"


class S3Storage():
    """ Storage driver for storing packages on S3
    """
    client: boto3.session.Session.client
    bucket: str


    def __init__(self, config: configuration.ServerConfig) -> None:
        """ Initialize the S3 storage driver

        The server configuration is expected to contain the S3
        Access Key ID and Secret Access Key. Optionally, an
        override for the S3 endpoint URL can be present, which
        will force the use of a custom S3-compatible server.
        """
        self.bucket = config.s3_bucket_name

        kwargs = {
            "aws_access_key_id": config.s3_access_key_id,
            "aws_secret_access_key": config.s3_secret_access_key,
        }
        # Handle custom servers
        if config.s3_url is not None:
            kwargs["endpoint_url"] = config.s3_url

        self.client = boto3.client('s3', **kwargs)


    def upsert(self, metadata: dict[str, str], package_path: str) -> bool:
        """ Updates the contents of the package specified by `metadata`
        """
        try:
            # Generate a unique object identifier
            object_id = str(uuid.uuid4())
            # Upload the file
            print("Uploading package with metadata:", metadata,
                  "object ID:", object_id, flush=True)
            self.client.upload_file(package_path, self.bucket, object_id)
            # Finally, save metadata about the stored object
            metadata[META_S3_UUID] = object_id
            metadata[META_S3_SIZE] = os.path.getsize(package_path)
            return True
        except ClientError as e:
            print("Uploading package to bucket", self.bucket, "failed:", e, flush=True)
            return False


    def generate_link(self, metadata: dict[str, str], expiry: int) -> str:
        """ Generate a signed link to the package specified by `metadata`
        """
        try:
            # This shouldn't happen
            object_id = metadata.get(META_S3_UUID, None)
            if object_id is None:
                raise RuntimeError("Package does not have the required S3 storage metadata:", META_S3_UUID)

            return self.client.generate_presigned_url('get_object',
                                                      Params={
                                                          'Bucket': self.bucket,
                                                          'Key': object_id
                                                      },
                                                      ExpiresIn=expiry)
        except ClientError as e:
            print("Failed to generate presigned S3 link:", e, flush=True)
            raise


    def delete(self, metadata: dict[str, str]):
        """ Deletes the specified package from storage
        """
        try:
            # This shouldn't happen
            object_id = metadata.get(META_S3_UUID, None)
            if object_id is None:
                print("WARNING: Deleting a package that does not have S3 object metadata!", flush=True)
                return

            self.client.delete_object(Bucket=self.bucket,
                                      Key=object_id)
        except ClientError as e:
            print("Failed deleting package object from S3:", e, flush=True)
            raise
