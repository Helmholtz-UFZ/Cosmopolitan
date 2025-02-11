"""This module provides a class to manage the interaction with Minio."""

import logging
import subprocess

from cosmopolitan_app.config import (
    JOB_WORK_DIR_TEMPLATE,
    MINIO_ACCESS_KEY,
    MINIO_ALIAS,
    MINIO_BUCKET,
    MINIO_SECRET_KEY,
    MINIO_URL,
)


class MinioError(Exception):
    """Exception raised for errors in the MinioManager class."""

    def __init__(self, dirname: str):
        """Initialize the MinioError class."""
        self.dirname = dirname
        super().__init__(f"Minio error for directory {dirname}")


def set_alias(dirname: str, reset_alias: bool = False) -> None:
    """Set the MinIO alias if it doesn't exist.

    Args:
        dirname: Name of the directory to sync from MinIO
        reset_alias: Set to True to reset the alias
    """
    try:
        logging.debug(f"Setting MinIO alias {MINIO_ALIAS}.")
        output = subprocess.run(
            ["mc", "alias", "list", MINIO_ALIAS],
            capture_output=True,
            text=True,
            check=False,
        )

        # Checke if command failed because of something else than missing alias. And
        # reraise the exception if so.
        if (
            output.returncode != 0
            and f"No such alias `{MINIO_ALIAS}` found" not in output.stderr
        ):
            logging.error(f"Failed to create MinIO bucket: {output.stderr}")
            raise subprocess.CalledProcessError(
                output.returncode,
                output.args,
                output=output.stdout,
                stderr=output.stderr,
            )

        if output.returncode != 0 or reset_alias:
            logging.debug(f"Creating MinIO alias {MINIO_ALIAS}.")
            output = subprocess.run(
                [
                    "mc",
                    "alias",
                    "set",
                    MINIO_ALIAS,
                    MINIO_URL,
                    MINIO_ACCESS_KEY,
                    MINIO_SECRET_KEY,
                ],
                check=True,
                capture_output=True,
            )
    except subprocess.CalledProcessError as e:
        error_msg = f"Failed to check/create MinIO alias: {e}\n{e.stderr.decode()}"
        error_msg = error_msg.replace(MINIO_SECRET_KEY, "****")
        error_msg = error_msg.replace(MINIO_ACCESS_KEY, "****")
        logging.error(error_msg)
        # Raise from None to suppress the original exception. Possible key leak to logs.
        raise MinioError(dirname) from None
    except FileNotFoundError as e:
        logging.error(f"Failed to find mc command: {e}")
        raise MinioError(dirname)


def create_bucket(reset_alias: bool = False) -> None:
    """Create the MinIO bucket.

    This only for local testing. In production, the bucket should be created by the
    system administrator and the service should not have the necessary permissions to
    create buckets. Thus this function should fail in production.
    """
    logging.debug(f"Creating MinIO bucket {MINIO_BUCKET}.")
    set_alias(MINIO_BUCKET, reset_alias)

    output = subprocess.run(
        ["mc", "stat", f"{MINIO_ALIAS}/{MINIO_BUCKET}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if output.returncode == 0:
        logging.debug(f"MinIO bucket {MINIO_BUCKET} already exists.")
        return

    output = subprocess.run(
        ["mc", "mb", f"{MINIO_ALIAS}/{MINIO_BUCKET}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if (
        output.returncode != 0
        and "Your previous request to create the named bucket succeeded and you already own it."  # noqa
        not in output.stderr
    ):
        logging.error(f"Failed to create MinIO bucket: {output.stderr}")
        raise subprocess.CalledProcessError(
            output.returncode,
            output.args,
            output=output.stdout,
            stderr=output.stderr,
        )


def sync_workdir(dirname: str, reset_alias: bool = False) -> None:
    """Sync a directory from MinIO to a local work directory using mc mirror.

    First checks/creates the MinIO alias if it doesn't exist.

    Args:
        dirname: Name of the directory to sync from MinIO
    """
    logging.debug(f"Syncing directory {dirname} from MinIO to local work directory.")
    set_alias(dirname, reset_alias)

    local_path = JOB_WORK_DIR_TEMPLATE.format(job_id=dirname)
    minio_path = f"{MINIO_ALIAS}/{MINIO_BUCKET}/{dirname}"

    try:
        result = subprocess.run(
            ["mc", "mirror", "--overwrite", local_path, minio_path],
            capture_output=True,
            text=True,
            check=True,
        )
        stdout = result.stdout.split("\n")
        num_files = len(stdout) - 2
        last_line = stdout[-2]
        logging.debug(f"Synced {num_files} files to bucket. {last_line}")

        result = subprocess.run(
            ["mc", "mirror", minio_path, local_path],
            capture_output=True,
            text=True,
            check=True,
        )
        stdout = result.stdout.split("\n")
        num_files = len(stdout) - 2
        last_line = stdout[-2]
        logging.debug(f"Synced {num_files} files to local directory. {last_line}")
    except subprocess.CalledProcessError as e:
        logging.error(
            (
                f"Failed to sync directory {dirname}: {e}\n"
                f"Error output: {e.stderr.decode()}"
            )
        )
        raise MinioError(dirname)


def delete_from_bucket(dirname: str, reset_alias: bool = False) -> None:
    """Delete all files with dirname from the MinIO bucket using mc rm.

    First checks/creates the MinIO alias if it doesn't exist.

    Args:
        dirname: Name of the directory to delete from MinIO
    """
    logging.debug(f"Deleting directory {dirname} from MinIO bucket.")
    set_alias(dirname, reset_alias)

    minio_path = f"{MINIO_ALIAS}/{MINIO_BUCKET}/{dirname}"
    try:
        # Use mc rm with --recursive and --force to delete all files in directory
        result = subprocess.run(
            ["mc", "rm", "--recursive", "--force", minio_path],
            capture_output=True,
            text=True,
            check=True,
        )
        stdout = result.stdout.split("\n")
        num_files = len(stdout) - 1
        logging.debug(f"Deleted {num_files} files from bucket.")
    except subprocess.CalledProcessError as e:
        logging.error(
            (
                f"Failed to sync directory {dirname}: {e}\n"
                f"Error output: {e.stderr.decode()}"
            )
        )
        raise MinioError(dirname)


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        level=logging.DEBUG,
    )
    folder_to_sync = "whimsical_affable_chipmunk"
    # create_bucket(reset_alias=True)
    sync_workdir(folder_to_sync, reset_alias=True)
    # delete_from_bucket(folder_to_sync, reset_alias=True)
