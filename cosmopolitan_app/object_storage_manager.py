"""This module provides a class to manage object storage using rclone."""

import logging
import subprocess

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


def check_result(result: subprocess.CompletedProcess) -> None:
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
        logging.error(f"Command failed: {error_msg}\n{output}")
        raise ObjectStorageError


def setup_remote() -> None:
    """Set up rclone remote configuration.

    Args:
        dirname: Name of the directory (used for error handling)
    """
    logging.debug("Setting up rclone remote.")
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
        "no_check_bucket=true",
    ]

    result = subprocess.run(
        config_params,
        capture_output=True,
        text=True,
    )
    check_result(result)

    logging.debug(f"Successfully created remote {OBJECT_STORAGE_REMOTE_NAME}")


def sync_workdir(dirname: str) -> None:
    """Sync a directory between local work directory and object storage using rclone.

    Args:
        dirname: Name of the directory to sync
    """
    logging.debug(
        f"Syncing directory {dirname} between local work directory and object storage."
    )
    local_path = JOB_WORK_DIR_TEMPLATE.format(job_id=dirname)
    remote_path = f"{OBJECT_STORAGE_REMOTE_NAME}:{OBJECT_STORAGE_BUCKET}/{dirname}"

    result = subprocess.run(
        ["rclone", "copy", local_path, remote_path, "--progress", "--checksum"],
        capture_output=True,
        text=True,
    )
    check_result(result)

    # Download remote changes to local
    result = subprocess.run(
        ["rclone", "copy", remote_path, local_path, "--progress", "--checksum"],
        capture_output=True,
        text=True,
    )
    check_result(result)


def delete_file_from_storage(filepath: str) -> None:
    """Delete a file from the object storage using rclone.

    Args:
        filepath: Path of the file to delete from object storage
    """
    logging.debug(f"Deleting file {filepath} from object storage.")

    remote_path = f"{OBJECT_STORAGE_REMOTE_NAME}:{OBJECT_STORAGE_BUCKET}/{filepath}"

    result = subprocess.run(
        ["rclone", "delete", remote_path],
        capture_output=True,
        text=True,
    )
    check_result(result)
    logging.debug(f"Successfully deleted file {filepath} from object storage")


def delete_directory_from_storage(dirpath: str) -> None:
    """Delete a directory from the object storage using rclone.

    Args:
        dirpath: Path of the directory to delete from object storage
    """
    logging.debug(f"Deleting directory {dirpath} from object storage.")

    remote_path = f"{OBJECT_STORAGE_REMOTE_NAME}:{OBJECT_STORAGE_BUCKET}/{dirpath}"

    result = subprocess.run(
        ["rclone", "purge", remote_path],
        capture_output=True,
        text=True,
    )
    check_result(result)
    logging.debug(f"Successfully deleted directory {dirpath} from object storage")


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        level=logging.DEBUG,
    )
    folder_to_sync = "whimsical_affable_chipmunk"

    setup_remote()
    sync_workdir(folder_to_sync)
    delete_directory_from_storage(folder_to_sync)
