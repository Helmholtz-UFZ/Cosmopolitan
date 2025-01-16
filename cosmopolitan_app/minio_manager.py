"""This module provides a class to manage the interaction with Minio."""

import logging
import os
from datetime import datetime

import boto3

from cosmopolitan_app.config import (
    MINIO_ACCESS_KEY,
    MINIO_BUCKET,
    MINIO_SECRET_KEY,
    MINIO_URL,
    WEB_WORK_DIR,
)


class MinioManager:
    """This manages the interaction with minio."""

    s3_client = boto3.client(
        "s3",
        endpoint_url=MINIO_URL,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
    )

    @classmethod
    def list_s3_files(cls, folder):
        """List files in an S3 bucket."""
        files = {}
        response = cls.s3_client.list_objects_v2(Bucket=MINIO_BUCKET, Prefix=folder)
        if "Contents" in response:
            for obj in response["Contents"]:
                relative_path = obj["Key"][len(folder) :]  # noqa: E203
                if relative_path:
                    files[relative_path] = obj["LastModified"]
        return files

    @classmethod
    def list_local_files(cls, folder):
        """List files in a local directory."""
        files = {}
        base_dir = os.path.join(WEB_WORK_DIR, folder)
        for root, _, filenames in os.walk(base_dir):
            for filename in filenames:
                filepath = os.path.join(root, filename)
                relative_path = os.path.relpath(filepath, WEB_WORK_DIR)
                files[relative_path] = datetime.fromtimestamp(
                    os.path.getmtime(filepath)
                )
        return files

    @classmethod
    def is_not_synced(cls, folder):
        """Check if there are any files that are not synced between S3 and local."""
        logging.debug(f"Checking if files in {folder} are not synced.")
        local_files = cls.list_local_files(folder)
        s3_files = cls.list_s3_files(folder)
        return local_files != s3_files

    @classmethod
    def sync_files(cls, folder):
        """Sync files between S3 bucket and local directory within a specific folder."""
        logging.debug(
            f"Synchronizing files in {folder} between S3 and local directory."
        )
        s3_files = cls.list_s3_files(folder)
        local_files = cls.list_local_files(folder)

        for file_key in {**s3_files, **local_files}.keys():
            local_path = os.path.join(WEB_WORK_DIR, file_key)

            if file_key not in local_files:
                cls.download_file(file_key, local_path)
            elif file_key not in s3_files:
                cls.upload_file(file_key, local_path)
            else:
                local_time = local_files[file_key]
                s3_time = s3_files[file_key]

                if local_time > s3_time:
                    cls.upload_file(file_key, local_path)
                elif s3_time > local_time:
                    cls.download_file(file_key, local_path)

    @classmethod
    def download_file(cls, s3_key, local_path):
        """Download a file from S3 to a local directory."""
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        cls.s3_client.download_file(MINIO_BUCKET, s3_key, local_path)

    @classmethod
    def upload_file(cls, s3_key, local_path):
        """Upload a file from a local directory to S3."""
        cls.s3_client.upload_file(local_path, MINIO_BUCKET, s3_key)


if __name__ == "__main__":
    folder_to_sync = "specific_folder"
    MinioManager.sync_files(folder=folder_to_sync)
