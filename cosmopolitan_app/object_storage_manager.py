"""This module provides a class to manage object storage using rclone."""

import logging
import subprocess
import sys

from cosmopolitan_app.config import (
    JOB_WORK_DIR_TEMPLATE,
    OBJECT_STORAGE_ACCESS_KEY,
    OBJECT_STORAGE_BUCKET,
    OBJECT_STORAGE_HOST,
    OBJECT_STORAGE_REMOTE_NAME,
    OBJECT_STORAGE_SECRET_KEY,
)


class ObjectStorageError(Exception):
    """Exception raised for errors in the ObjectStorageManager class."""

    def __init__(self):
        """Initialize the ObjectStorageError class."""
        super().__init__("An error occurred while managing object storage.")


def check_result(params: list, result: subprocess.CompletedProcess) -> None:
    """Check the result of a subprocess command and raise an error if it failed.

    Args:
        result: The result of the subprocess command

    Raises:
        ObjectStorageError: If the command failed
    """
    if result.returncode != 0:
        error_msg = result.stderr.replace(OBJECT_STORAGE_SECRET_KEY, "****")
        error_msg = error_msg.replace(OBJECT_STORAGE_ACCESS_KEY, "****")
        output = result.stdout.replace(OBJECT_STORAGE_SECRET_KEY, "****")
        output = output.replace(OBJECT_STORAGE_ACCESS_KEY, "****")
        call = " ".join(params)
        call = call.replace(OBJECT_STORAGE_SECRET_KEY, "****")
        call = call.replace(OBJECT_STORAGE_ACCESS_KEY, "****")
        logging.error(
            f"Command failed: {call}\n{error_msg}\n{output}",
            extra={"tag": "object_storage"},
        )
        raise ObjectStorageError


def setup_remote() -> None:
    """Set up rclone remote configuration.

    Args:
        dirname: Name of the directory (used for error handling)
    """
    logging.debug("Setting up rclone remote.", extra={"tag": "object_storage"})
    config_params = [
        "rclone",
        "config",
        "create",
        OBJECT_STORAGE_REMOTE_NAME,
        "s3",
        "provider=Other",
        f"access_key_id={OBJECT_STORAGE_ACCESS_KEY}",
        f"secret_access_key={OBJECT_STORAGE_SECRET_KEY}",
        "region=us-east-1",
        f"endpoint={OBJECT_STORAGE_HOST}",
        "acl=private",
        "force_path_style=true",
    ]

    result = subprocess.run(
        config_params,
        capture_output=True,
        text=True,
    )
    check_result(config_params, result)

    logging.debug(
        f"Successfully created remote {OBJECT_STORAGE_REMOTE_NAME}",
        extra={"tag": "object_storage"},
    )


def sync_workdir(dirname: str) -> None:
    """Sync a directory between local work directory and object storage using rclone.

    Args:
        dirname: Name of the directory to sync
    """
    logging.debug(
        f"Syncing directory {dirname} between local work directory and object storage.",
        extra={"tag": "object_storage"},
    )
    local_path = JOB_WORK_DIR_TEMPLATE.format(job_id=dirname)
    remote_path = f"{OBJECT_STORAGE_REMOTE_NAME}:{OBJECT_STORAGE_BUCKET}/{dirname}"

    sync_remote_params = [
        "rclone",
        "sync",
        local_path,
        remote_path,
        "--progress",
        "--checksum",
    ]
    result = subprocess.run(
        sync_remote_params,
        capture_output=True,
        text=True,
    )
    check_result(sync_remote_params, result)

    # Download remote changes to local
    sync_local_params = [
        "rclone",
        "sync",
        remote_path,
        local_path,
        "--progress",
        "--checksum",
    ]
    result = subprocess.run(
        sync_local_params,
        capture_output=True,
        text=True,
    )
    check_result(sync_local_params, result)


def delete_file_from_storage(filepath: str) -> None:
    """Delete a file from the object storage using rclone.

    Args:
        filepath: Path of the file to delete from object storage
    """
    logging.debug(
        f"Deleting file {filepath} from object storage.",
        extra={"tag": "object_storage"},
    )

    remote_path = f"{OBJECT_STORAGE_REMOTE_NAME}:{OBJECT_STORAGE_BUCKET}/{filepath}"

    delete_params = [
        "rclone",
        "delete",
        remote_path,
    ]
    result = subprocess.run(
        delete_params,
        capture_output=True,
        text=True,
    )
    check_result(delete_params, result)
    logging.debug(
        f"Successfully deleted file {filepath} from object storage",
        extra={"tag": "object_storage"},
    )


def delete_directory_from_storage(dirpath: str) -> None:
    """Delete a directory from the object storage using rclone.

    Args:
        dirpath: Path of the directory to delete from object storage
    """
    logging.debug(
        f"Deleting directory {dirpath} from object storage.",
        extra={"tag": "object_storage"},
    )

    remote_path = f"{OBJECT_STORAGE_REMOTE_NAME}:{OBJECT_STORAGE_BUCKET}/{dirpath}"

    purge_params = [
        "rclone",
        "purge",
        remote_path,
    ]
    result = subprocess.run(
        purge_params,
        capture_output=True,
        text=True,
    )
    check_result(purge_params, result)
    logging.debug(
        f"Successfully deleted directory {dirpath} from object storage",
        extra={"tag": "object_storage"},
    )


def create_bucket() -> None:
    """Create the object storage bucket."""
    logging.debug(
        f"Creating bucket {OBJECT_STORAGE_BUCKET}", extra={"tag": "object_storage"}
    )

    remote_bucket = f"{OBJECT_STORAGE_REMOTE_NAME}:{OBJECT_STORAGE_BUCKET}"
    bucket_params = [
        "rclone",
        "mkdir",
        remote_bucket,
    ]
    print(" ".join(bucket_params))  # For debugging purposes

    result = subprocess.run(
        bucket_params,
        capture_output=True,
        text=True,
    )
    check_result(bucket_params, result)
    logging.debug(
        f"Successfully created bucket {OBJECT_STORAGE_BUCKET}",
        extra={"tag": "object_storage"},
    )


def main():
    """Execute setup_remote or create_bucket based on command line argument."""
    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) != 2:
        print("Usage: python object_storage_manager.py [setup_remote|create_bucket]")
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "setup_remote":
            setup_remote()
            logging.info(
                "Object storage remote setup completed successfully.",
                extra={"tag": "object_storage"},
            )
        elif command == "create_bucket":
            create_bucket()
            logging.info(
                "Bucket creation completed successfully.",
                extra={"tag": "object_storage"},
            )
        else:
            print(f"Unknown command: {command}")
            print(
                "Usage: python object_storage_manager.py [setup_remote|create_bucket]"
            )
            sys.exit(1)
    except ObjectStorageError as e:
        logging.error(
            f"Failed to execute {command}: {e}", extra={"tag": "object_storage"}
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
