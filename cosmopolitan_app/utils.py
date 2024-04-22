"""Utility functions for the web service."""

import logging
import os
import shutil
import smtplib
import traceback
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import request, url_for
from sqlalchemy.exc import OperationalError
from werkzeug.exceptions import NotFound

from cosmopolitan_app.config import (
    DAYS_DELETE_NOT_SUMBITTED,
    DAYS_DELETE_SUMBITTED,
    EMAIL_PASSWORD,
    EMAIL_PORT,
    EMAIL_SENDER,
    EMAIL_SERVER,
    EMAIL_USERNAME,
    WEB_WORK_DIR,
)
from cosmopolitan_app.db_manager import DataBaseManager, JobNotFound


def clean_up():
    """Delete jobs older than a day and older than two months and their directories."""
    logging.info("Start cleaning up.")
    kept_jobs = []

    # Define the time thresholds
    job_end_of_life_not_submitted = date.today() - timedelta(
        days=DAYS_DELETE_NOT_SUMBITTED
    )
    job_end_of_life_submitted = date.today() - timedelta(days=DAYS_DELETE_SUMBITTED)

    for job_id, (start_date, submitted) in DataBaseManager.list_jobs().items():
        logging.debug(f"Check job {job_id}.")
        if not submitted and start_date < job_end_of_life_not_submitted:
            logging.debug("Job was not submit and is older than two days.")
            DataBaseManager.delete_job(job_id)
        elif start_date < job_end_of_life_submitted:
            logging.debug("Job older than two month.")
            DataBaseManager.delete_job(job_id)
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
    if isinstance(e, NoSlurmConnectionException):
        return (
            {
                "error_page": "html/errors/no_slurm_connection.html",
                "job_id": e.job_id,
            },
            500,
            False,
        )

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
        f"Unexpected error in { route } using { route_function }:\n"
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

    server = smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT)
    if EMAIL_PASSWORD != "test":
        server.starttls()
    server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
    server.sendmail(EMAIL_SENDER, recipient, msg.as_string())
    server.quit()


def send_finished_mail(job):
    """Send a notification email to the user that the job finished."""
    if job.email == "" or job.notified_end:
        return
    logging.info("Send mail about finished job.")
    url = url_for("submission", job_id=job.job_id, _external=True)
    with open(
        "cosmopolitan_app/templates/emails/job_finished_email.txt",
        "r",
        encoding="UTF-8",
    ) as f_handle:
        content = f_handle.read().format(job_id=job.job_id, url=url, status=job.status)

    send_mail(job.email, f'Job "{ job.job_id }" finished', content)
    job.notified_end = True
    job.save_attributes(["notified_end"])


def send_submission_mail(job):
    """Send a notification email to the user that the job was submitted."""
    if job.email == "":
        return
    logging.info("Send mail about submitted job.")
    url = url_for("submission", job_id=job.job_id, _external=True)
    with open(
        "cosmopolitan_app/templates/emails/submission_email.txt", "r", encoding="UTF-8"
    ) as f_handle:
        content = f_handle.read().format(job_id=job.job_id, url=url)
    send_mail(job.email, f'Job "{ job.job_id }" submitted', content)


class InvalidJobID(Exception):
    """Raised by CosmopolitanJob if init with invalid job id."""

    def __init__(self, job_id):
        """Add job id as attribute and format error message."""
        self.job_id = job_id
        super().__init__(f"{job_id} is not a valid job_id.")


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


class NoSlurmConnectionException(Exception):
    """Raised if no connection to the cluster can be established."""

    def __init__(self, job_id):
        """Add job id as attribute and format error message."""
        self.job_id = job_id
        super().__init__(
            (
                "Can not establish a connection to Cluster."
                f"Job {job_id} could not be submitted."
            )
        )
