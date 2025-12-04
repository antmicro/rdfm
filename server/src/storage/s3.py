import uuid
import os
import configuration
import boto3
import boto3.session
from botocore.exceptions import ClientError
from botocore.config import Config
from typing import Type
from storage.common import upload_part_count
import datetime


META_S3_UUID = "rdfm.storage.s3.uuid"
META_S3_SIZE = "rdfm.storage.s3.size"
META_S3_DIRECTORY = "rdfm.storage.s3.directory"
DESIRED_PART_SIZE = 10 * 2**20
MULTIPART_EXPIRY = 3600


class S3Storage:
    """Storage driver for storing packages on S3"""

    client: boto3.session.Session.client
    bucket: str

    def __init__(self, config: configuration.ServerConfig) -> None:
        """Initialize the S3 storage driver

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

        client_config = Config(
            signature_version="s3v4" if config.s3_use_v4_signature else None,
            region_name=config.s3_region_name,
        )

        kwargs["config"] = client_config

        self.client = boto3.client("s3", **kwargs)

    @staticmethod
    def get_object_path(bucket_directory: str | None, object_id: str) -> str:
        if bucket_directory is None or bucket_directory == "":
            return object_id
        else:
            return bucket_directory + "/" + object_id

    def upsert(
        self,
        metadata: dict[str, str],
        package_path: str,
        bucket_directory: str | None = None,
    ) -> bool:
        """Updates the contents of the package specified by `metadata`"""
        try:
            # Generate a unique object identifier
            object_id = str(uuid.uuid4())
            # Upload the file
            print(
                "Uploading package with metadata:",
                metadata,
                "object ID:",
                object_id,
                flush=True,
            )
            self.client.upload_file(
                package_path,
                self.bucket,
                S3Storage.get_object_path(bucket_directory, object_id),
            )
            # Finally, save metadata about the stored object
            metadata[META_S3_UUID] = object_id
            metadata[META_S3_SIZE] = os.path.getsize(package_path)
            if bucket_directory is not None:
                metadata[META_S3_DIRECTORY] = str(bucket_directory)
            else:
                metadata[META_S3_DIRECTORY] = ""
            return True
        except ClientError as e:
            print(
                "Uploading package to bucket",
                self.bucket,
                "failed:",
                e,
                flush=True,
            )
            return False

    def generate_url(self, metadata: dict[str, str], expiry: int) -> str:
        """Generate a signed URL to the package specified by `metadata`"""
        try:
            # This shouldn't happen
            object_id = metadata.get(META_S3_UUID, None)
            if object_id is None:
                raise RuntimeError(
                    "Package does not have the required S3 storage metadata:",
                    META_S3_UUID,
                )
            bucket_directory = metadata.get(META_S3_DIRECTORY, None)

            return self.client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": S3Storage.get_object_path(
                        bucket_directory, object_id
                    ),
                },
                ExpiresIn=expiry,
            )
        except ClientError as e:
            print("Failed to generate presigned S3 link:", e, flush=True)
            raise

    def delete(self, metadata: dict[str, str]):
        """Deletes the specified package from storage"""
        try:
            # This shouldn't happen
            object_id = metadata.get(META_S3_UUID, None)
            if object_id is None:
                print(
                    "WARNING: Deleting a package that does not have S3 object "
                    "metadata!",
                    flush=True,
                )
                return
            bucket_directory = metadata.get(META_S3_DIRECTORY, None)

            self.client.delete_object(
                Bucket=self.bucket,
                Key=S3Storage.get_object_path(bucket_directory, object_id),
            )
        except ClientError as e:
            print("Failed deleting package object from S3:", e, flush=True)
            raise

    class MultipartUploader:
        """Helper class for handling multipart upload"""
        def __init__(self, s3, key: str):
            self.s3 = s3
            self.key = key
            self.mpu = self.s3.client.create_multipart_upload(
                Bucket=self.s3.bucket,
                Key=self.key,
                Expires=(datetime.datetime.now()
                         + datetime.timedelta(seconds=MULTIPART_EXPIRY))
            )

        def generate_urls(self, upload_size: int, expiry: int) -> tuple[list[str], int]:
            """
            Returns list of upload urls and upload size for each upload url.
            The amount of upload urls depends on upload_size param
            """
            urls = []
            part_count, part_size = upload_part_count(upload_size, DESIRED_PART_SIZE)

            for i in range(part_count):
                try:
                    urls.append(self.s3.client.generate_presigned_url(
                        "upload_part",
                        Params={
                            "Bucket": self.s3.bucket,
                            "Key": self.key,
                            "PartNumber": i + 1,
                            "UploadId": self.mpu["UploadId"]
                        },
                        ExpiresIn=expiry,
                    ))
                except ClientError as e:
                    print("Failed to generate presigned S3 link:", e, flush=True)
                    raise

            return urls, part_size

        def complete_upload(self, etags: list[str]):
            """Finalizes the upload - etags param must contain etags returned by each upload"""
            self.s3.client.complete_multipart_upload(
                Bucket=self.s3.bucket,
                Key=self.key,
                MultipartUpload={
                    'Parts': [
                        {"ETag": etag, "PartNumber": idx + 1} for idx, etag in enumerate(etags)
                    ]
                },
                UploadId=self.mpu["UploadId"]
            )

        def abort_upload(self):
            """Terminates the upload"""
            self.s3.client.abort_multipart_upload(
                Bucket=self.s3.bucket,
                Key=self.key,
                UploadId=self.mpu["UploadId"]
            )

    def create_multipart_downloader(self, key: str) -> Type[MultipartUploader]:
        """Creates multipart downloader"""
        return self.MultipartUploader(self, key)

    def generate_fs_download_url(self, key: str, expiry: int, filename: str | None = None) -> str:
        """Returns download link for given item"""
        try:
            params = {
                "Bucket": self.bucket,
                "Key": key,
            }
            if filename is not None:
                params["ResponseContentDisposition"] = f"attachment; filename = {filename}"
            return self.client.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=expiry,
            )
        except ClientError as e:
            print("Failed to generate presigned S3 link:", e, flush=True)
            raise

    def upload_action_log(
        self,
        content: bytes,
        storage_directory: str,
        object_id: str,
    ) -> bool:
        """Uploads file containg action execution log"""
        try:
            self.client.put_object(
                Body=content,
                Bucket=self.bucket,
                Key=S3Storage.get_object_path(storage_directory, object_id),
            )
            return True
        except ClientError as e:
            print(
                "Uploading action log to bucket",
                self.bucket,
                "failed:",
                e,
                flush=True,
            )
            return False
