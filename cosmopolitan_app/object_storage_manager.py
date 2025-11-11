"""This module provides a class to manage object storage using rclone."""

import logging
import os
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

    def __init__(self, message="An error occurred while managing object storage."):
        """Initialize the ObjectStorageError class."""
        super().__init__(message)


def check_result(params: list, result: subprocess.CompletedProcess) -> None:
    """Check the result of a subprocess command and raise an error if it failed.

    Args:
        result: The result of the subprocess command

    Raises:
        ObjectStorageError: If the command failed
    """
    error_msg = result.stderr.replace(OBJECT_STORAGE_SECRET_KEY, "****")
    error_msg = error_msg.replace(OBJECT_STORAGE_ACCESS_KEY, "****")
    output = result.stdout.replace(OBJECT_STORAGE_SECRET_KEY, "****")
    output = output.replace(OBJECT_STORAGE_ACCESS_KEY, "****")
    call = " ".join(params)
    call = call.replace(OBJECT_STORAGE_SECRET_KEY, "****")
    call = call.replace(OBJECT_STORAGE_ACCESS_KEY, "****")
    logging.debug(
        f"Command executed: {call}\nOutput: {output}\nError: {error_msg}",
        extra={"tag": "object_storage"},
    )
    if result.returncode != 0:
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


def get_local_files(local_path: str) -> set:
    """Get set of all files in a local directory (relative paths).

    Args:
        local_path: Path to local directory

    Returns:
        Set of relative file paths
    """
    files = set()
    if not os.path.exists(local_path):
        return files

    for root, _, filenames in os.walk(local_path):
        for filename in filenames:
            # Get full path and make it relative to local_path
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, local_path)
            files.add(rel_path)
    return files


def get_remote_files(remote_path: str) -> set:
    """Get set of all files in a remote directory using rclone ls.

    Args:
        remote_path: Remote path in format "remote:bucket/dirname"

    Returns:
        Set of relative file paths
    """
    ls_params = ["rclone", "ls", remote_path]

    result = subprocess.run(
        ls_params,
        capture_output=True,
        text=True,
    )

    # rclone ls returns lines like: "  123456 path/to/file.txt"
    # Extract just the filenames
    files = set()
    for line in result.stdout.strip().split("\n"):
        if line:
            # Split on whitespace and take everything after the size
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                files.add(parts[1])

    return files


def sync_workdir(dirname: str) -> None:
    """Sync a directory between local work directory and object storage using rclone.

    This function performs bidirectional sync and verifies that all local files
    are successfully synced to remote storage.

    Args:
        dirname: Name of the directory to sync

    Raises:
        ObjectStorageError: If sync verification fails (local and remote don't match)
    """
    logging.debug(
        f"Syncing directory {dirname} between local work directory and object storage.",
        extra={"tag": "object_storage"},
    )
    local_path = JOB_WORK_DIR_TEMPLATE.format(job_id=dirname)
    remote_path = f"{OBJECT_STORAGE_REMOTE_NAME}:{OBJECT_STORAGE_BUCKET}/{dirname}"

    # List local files before sync
    local_files_before = get_local_files(local_path)
    logging.debug(
        f"Local files before sync ({len(local_files_before)} files): "
        f"{sorted(local_files_before)}",
        extra={"tag": "object_storage"},
    )

    # Upload local changes to remote
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

    # Verify sync: compare local and remote files
    local_files_after = get_local_files(local_path)
    remote_files = get_remote_files(remote_path)

    logging.debug(
        f"Local files after sync ({len(local_files_after)} files): "
        f"{sorted(local_files_after)}",
        extra={"tag": "object_storage"},
    )
    logging.debug(
        f"Remote files after sync ({len(remote_files)} files): {sorted(remote_files)}",
        extra={"tag": "object_storage"},
    )

    # Check if sets match
    if local_files_after != remote_files:
        missing_remote = local_files_after - remote_files
        missing_local = remote_files - local_files_after

        error_msg = f"Sync verification failed for {dirname}!\n"
        if missing_remote:
            error_msg += f"Files missing from remote: {sorted(missing_remote)}\n"
        if missing_local:
            error_msg += f"Files missing from local: {sorted(missing_local)}\n"

        logging.error(error_msg, extra={"tag": "object_storage"})
        raise ObjectStorageError(error_msg)

    logging.debug(
        f"Sync verification successful: {len(local_files_after)} files match "
        f"between local and remote",
        extra={"tag": "object_storage"},
    )


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
