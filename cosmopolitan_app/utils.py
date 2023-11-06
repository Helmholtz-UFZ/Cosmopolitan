"""Utility functions for the web service."""

import logging
import os
import shutil
import smtplib
import subprocess
import traceback
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from time import sleep

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
    WEB_UPLOAD_DIR,
    WEB_WORK_DIR,
)
from cosmopolitan_app.db_manager import DataBaseManager, JobNotFound


def error_response_args(e):
    """Serve required arguments for error handling for both flask and dash."""
    if isinstance(e, NotFinishedException):
        return (
            {
                "error_page": "html/errors/job_not_finished_exception.html",
                "job_id": e.job_id,
            },
            500,
            False,
        )

    if isinstance(e, NotSubmittedException):
        return (
            {
                "error_page": "html/errors/job_not_submitted_exception.html",
                "job_id": e.job_id,
            },
            500,
            False,
        )

    if isinstance(e, SubmittedException):
        return (
            {
                "error_page": "html/errors/job_submitted_exception.html",
                "job_id": e.job_id,
            },
            500,
            False,
        )

    if isinstance(e, JobNotFound):
        return (
            {
                "error_page": "html/errors/job_not_found_error.html",
                "job_id": e.job_id,
            },
            500,
            False,
        )

    if isinstance(e, InvalidJobID):
        return (
            {
                "error_page": "html/errors/job_not_found_error.html",
                "job_id": e.job_id,
            },
            500,
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


def clean_up():
    """Delete jobs older than a day and older than two months and their directories."""
    logging.info("Start cleaning up.")
    db_manager = DataBaseManager()

    # Define the time thresholds
    two_day_ago = date.today() - timedelta(days=DAYS_DELETE_NOT_SUMBITTED)
    two_months_ago = date.today() - timedelta(days=DAYS_DELETE_SUMBITTED)

    jobs = db_manager.list_jobs()
    kept_jobs = []

    for job_id, (start_date, submitted) in jobs.items():
        logging.debug(f"Check job {job_id}.")
        if not submitted and start_date < two_day_ago:
            logging.debug("Job was not submit and is older than two days.")
            db_manager.delete_job(job_id)
        elif start_date < two_months_ago:
            logging.debug("Job older than two month.")
            db_manager.delete_job(job_id)
        else:
            logging.debug("Job will be kept.")
            kept_jobs.append(job_id)

    # Delete directories locally
    logging.info("Clean up directorys locally.")
    for directory in [WEB_WORK_DIR, WEB_UPLOAD_DIR]:
        for dir_name in os.listdir(directory):
            dir_path = os.path.join(directory, dir_name)
            if os.path.isdir(dir_path) and dir_name not in kept_jobs:
                shutil.rmtree(dir_path)

    # Delete work directories on cluster
    logging.debug("Clean up directorys on cluster.")
    old_jobs = [
        job_id
        for job_id in ssh_call("list_work_dir.sh").split()
        if job_id not in kept_jobs
    ]

    if len(old_jobs) > 0:
        ssh_call(f"delete_work_dir.sh { ' '.join(old_jobs) }")


def send_mail(recipient, subject, content):
    """Send an email using the provided details."""
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = recipient
    msg["Subject"] = subject

    body = content
    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT)
    server.starttls()
    server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
    server.sendmail(EMAIL_SENDER, recipient, msg.as_string())
    server.quit()


def send_submission_mail(job):
    """Send a notification email to the user that the job was submitted."""
    url = url_for("submission", job_id=job.job_id, _external=True)
    with open(
        "cosmopolitan_app/templates/emails/submission_email.txt", "r", encoding="UTF-8"
    ) as f_handle:
        content = f_handle.read().format(job_id=job.job_id, url=url)
    if job.email != "":
        send_mail(job.email, f'Job "{ job.job_id }" submitted', content)


class SshError(Exception):
    """Raised if ssh call repetidly failed."""

    pass


def ssh_call(call_str):
    """
    Execute an SSH command multiple times with retry logic and capture its output.

    Raises:
    SshError: If the SSH command fails after three attempts, an SshError is
    raised. The error message includes details about the command, stdout, and
    stderr of the last failed attempt.
    """
    ssh_dir = "cosmopolitan_app/cluster_api"
    if not os.path.isdir(ssh_dir):
        raise FileNotFoundError(
            f"Directory for ssh-scripts { ssh_dir } is not available"
        )
    call_str = os.path.join(ssh_dir, call_str)
    logging.info(f"SSH call:\n{ call_str }")

    for i in range(1, 4):
        try:
            completed_process = subprocess.run(
                call_str.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            break
        except subprocess.CalledProcessError as exc:
            logging.debug(f"SSH call failed:\n{ exc }")
            if i < 3:
                sleep(2)
                continue
            error_str = (
                f"ERROR ssh call\nCommand\n{call_str}\nstdout:\n"
                f"{exc.stdout.decode('UTF8')}\nstderr:\n{exc.stderr.decode('UTF8')}"
            )
            raise SshError(error_str)

    out = completed_process.stdout.decode("UTF8")
    logging.debug(f"SSH call succesfull:\n{ out }")
    return out


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
