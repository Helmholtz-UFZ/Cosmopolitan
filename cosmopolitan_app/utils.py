"""Utility functions for the web service."""

import logging
import os
import re
import shutil
import smtplib
import traceback
import zipfile
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import BytesIO

from flask import request
from sqlalchemy.exc import OperationalError
from werkzeug.exceptions import NotFound

from cosmopolitan_app.config import (
    EMAIL_PASSWORD,
    EMAIL_PORT,
    EMAIL_SENDER,
    EMAIL_SERVER,
    EMAIL_USERNAME,
    WEB_WORK_DIR,
)
from cosmopolitan_app.constants import (
    DAYS_DELETE_NOT_SUMBITTED,
    DAYS_DELETE_SUMBITTED,
    LOG_RETENTION_DAYS,
)
from cosmopolitan_app.object_storage_manager import ObjectStorageError
from cosmopolitan_app.postgres_manager import JobNotFound, PostgresManager

submission_url = "{external_url}/submission/{job_id}"


job_finished_template = """The job {job_id} finished.
The exit status was {status}.
To see further results visit:
{url}"""

job_submitted_template = """The job {job_id} finished.
The exit status was {status}.
To see further results visit:
{url}"""


def swap_classes(new_class: str, class_name: str) -> str:
    """Replace or add a class with the same prefix as new_class in a className string.

    The prefix is automatically extracted from the new_class.

    Parameters:
    new_class (str): The new class to add (e.g., "bg-primary", "text-white")
    class_name (str): The original className string

    Returns:
    str: The updated className string with the replaced class

    Examples:
    >>> swap_classes("bg-primary", "bg-info rounded-top py-2 mb-4")
    'bg-primary rounded-top py-2 mb-4'
    >>> swap_classes("text-danger", "bg-info text-dark py-2")
    'bg-info text-danger py-2'
    """
    # Extract prefix from new_class
    prefix_match = re.match(r"^([a-zA-Z0-9]+)-", new_class)
    if not prefix_match:
        raise ValueError(
            f"New class '{new_class}' must have a prefix followed by a hyphen (e.g., 'bg-primary')"  # noqa
        )

    class_prefix = prefix_match.group(1)

    # Pattern to match classes with the given prefix
    class_pattern = rf"\b{class_prefix}-[a-zA-Z0-9]+"

    # Check if a class with the given prefix exists
    match = re.search(class_pattern, class_name)

    if match:
        # Replace existing class with the new one
        updated_class_name = re.sub(class_pattern, new_class, class_name)
        return updated_class_name
    else:
        # Add new class if none with the prefix exists
        return f"{class_name} {new_class}"


def zip_directory(directory_path):
    """Create a zip archive of a directory and return it as a BytesIO object."""
    zip_buffer = BytesIO()

    if not os.path.isdir(directory_path):
        raise FileNotFoundError(f"The directory {directory_path} does not exist.")

    # Create a zipfile object and write the directory contents into the zip archive
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for foldername, subfolders, filenames in os.walk(directory_path):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                # Add the file to the archive, maintaining the directory structure
                arcname = os.path.relpath(file_path, directory_path)
                zip_file.write(file_path, arcname)

    zip_buffer.seek(0)
    return zip_buffer


def lock_task(task):
    """Decorate a background tasks to lock the function.

    Uses the function name as lock name, so only one function of the same name can run
    at a time.
    """

    def lock_function(*args, **kwargs):
        logging.debug(f"Lock function {task.__name__}.")
        if PostgresManager.get_lock(task.__name__):
            logging.debug(f"Lock acquired for {task.__name__}.")
            try:
                task(*args, **kwargs)
            finally:
                PostgresManager.release_lock(task.__name__)
                logging.debug(f"Lock released for {task.__name__}.")

    return lock_function


@lock_task
def clean_up():
    """Delete jobs older than a day and older than two months and their directories."""
    logging.info("Start cleaning up.")
    clean_up_jobs()

    log_cutoff = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    logging.info(f"Cleaning up logs older than {log_cutoff}")
    PostgresManager.delete_logs_older_than(log_cutoff)


def clean_up_jobs(
    days_delete_not_submitted=DAYS_DELETE_NOT_SUMBITTED,
    days_delete_submitted=DAYS_DELETE_SUMBITTED,
):
    """Delete jobs depending on their status and age."""
    logging.info("Start cleaning up jobs.")
    kept_jobs = []

    # Define the time thresholds
    job_end_of_life_not_submitted = date.today() - timedelta(
        days=days_delete_not_submitted
    )
    job_end_of_life_submitted = date.today() - timedelta(days=days_delete_submitted)

    for job_id, job_info in PostgresManager.list_jobs().items():
        submitted = job_info["submitted"]
        start_date = job_info["start_date"]
        logging.debug(f"Check job {job_id}.")
        if not submitted and start_date <= job_end_of_life_not_submitted:
            logging.debug(
                f"Job was not submit and is older than {days_delete_not_submitted} days."  # noqa
            )
            PostgresManager.delete_job(job_id)
        elif start_date <= job_end_of_life_submitted:
            logging.debug(f"Job older than {days_delete_submitted} days.")
            PostgresManager.delete_job(job_id)
        else:
            logging.debug("Job will be kept.")
            kept_jobs.append(job_id)

    # Delete directorys locally
    logging.debug("Clean up directorys locally.")
    for dir_name in os.listdir(WEB_WORK_DIR):
        dir_path = os.path.join(WEB_WORK_DIR, dir_name)
        if os.path.isdir(dir_path) and dir_name not in kept_jobs:
            shutil.rmtree(dir_path)


def error_response_args(e):
    """Serve required arguments for error handling for both flask and dash."""
    if isinstance(e, NotFinishedException):
        return (
            {
                "error_page": "html/errors/job_not_finished_exception.html",
                "job_id": e.job_id,
            },
            400,
            False,
        )

    if isinstance(e, NotSubmittedException):
        return (
            {
                "error_page": "html/errors/job_not_submitted_exception.html",
                "job_id": e.job_id,
            },
            400,
            False,
        )

    if isinstance(e, SubmittedException):
        return (
            {
                "error_page": "html/errors/job_submitted_exception.html",
                "job_id": e.job_id,
            },
            400,
            False,
        )

    if isinstance(e, JobNotFound):
        return (
            {
                "error_page": "html/errors/job_not_found_error.html",
                "job_id": e.job_id,
            },
            400,
            False,
        )

    if isinstance(e, InvalidJobID):
        return (
            {
                "error_page": "html/errors/job_not_found_error.html",
                "job_id": e.job_id,
            },
            400,
            False,
        )

    if isinstance(e, OperationalError):
        return (
            {
                "error_page": "html/errors/db_no_connection_error.html",
            },
            500,
            True,
        )

    if isinstance(e, ObjectStorageError):
        return (
            {
                "error_page": "html/errors/db_no_connection_error.html",
            },
            500,
            True,
        )
    if isinstance(e, NotFound):
        return (
            {
                "error_page": "html/errors/file_not_found.html",
            },
            404,
            False,
        )

    return (
        {
            "error_page": "html/errors/internal_error.html",
            "job_id": "None",
        },
        500,
        True,
    )


def log_error():
    """
    Log error with traceback.

    In production this will trigger an email, see logging.py.
    """
    route = request.url_rule
    route_function = request.endpoint

    error = traceback.format_exc()
    content = (
        f"Unexpected error in {route} using {route_function}:\n"
        f"{error}\n"
        f"PID={os.getpid()}\n"
    )
    logging.error(content)


def send_mail(recipient, subject, content):
    """Send an email using the provided details."""
    logging.debug(f"Send mail to {recipient} with subject {subject}.")
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = recipient
    msg["Subject"] = subject

    body = content
    msg.attach(MIMEText(body, "plain"))

    logging.debug(f"Connect to email server {EMAIL_SERVER}:{EMAIL_PORT}.")
    server = smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT)
    if EMAIL_PASSWORD != "test":
        server.starttls()
    server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
    server.sendmail(EMAIL_SENDER, recipient, msg.as_string())
    server.quit()


def send_finished_mail(job):
    """Send a notification email to the user that the job finished."""
    if job.model.email == "" or job.notified_end:
        return
    logging.info("Send mail about finished job.")
    url = submission_url.format(job_id=job.job_id, external_url=request.url_root)
    content = job_finished_template.format(
        job_id=job.job_id,
        status=job.status,
        url=url,
    )

    send_mail(job.model.email, f'Job "{job.job_id}" finished', content)
    job.notified_end = True
    job.save_attributes(["notified_end"])


def send_submission_mail(job):
    """Send a notification email to the user that the job was submitted."""
    if job.model.email == "":
        return
    logging.info(f"Send mail about submitted job {job.job_id}.")
    url = submission_url.format(job_id=job.job_id, external_url=request.url_root)
    content = job_submitted_template.format(
        job_id=job.job_id,
        status=job.status,
        url=url,
    )
    send_mail(job.model.email, f'Job "{job.job_id}" submitted', content)


class InvalidJobID(Exception):
    """Raised by CosmopolitanJob if init with invalid job id."""

    def __init__(self, job_id):
        """Add job id as attribute and format error message."""
        self.job_id = job_id
        super().__init__(f"{job_id} is not a valid job_id.")


class JobExists(Exception):
    """Raised by Job if a new job is created with an existing job id."""

    def __init__(self, job_id):
        """Add job id as attribute and format error message."""
        self.job_id = job_id
        super().__init__(f"{job_id} already exists.")


class SubmittedException(Exception):
    """Raised when calling a method that requires a job not to be submitted."""

    def __init__(self, job_id):
        """Add job id as attribute and format error message."""
        self.job_id = job_id
        super().__init__(f"The job {job_id} was not yet submitted.")


class NotSubmittedException(Exception):
    """Raised when calling a method that requires a job to be submitted."""

    def __init__(self, job_id):
        """Add job id as attribute and format error message."""
        self.job_id = job_id
        super().__init__(f"The job {job_id} was not yet submitted.")


class NotFinishedException(Exception):
    """Raised when calling a method that requires a job to be finished."""

    def __init__(self, job_id):
        """Add job id as attribute and format error message."""
        self.job_id = job_id
        super().__init__(f"The job {job_id} is not yet finished.")
