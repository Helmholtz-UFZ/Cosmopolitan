"""Utility functions for the web service."""

import logging
import os
import re
import smtplib
import time
import zipfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import BytesIO

from flask import request

from cosmopolitan_app.config import (
    EMAIL_PASSWORD,
    EMAIL_PORT,
    EMAIL_SENDER,
    EMAIL_SERVER,
    EMAIL_USERNAME,
    WEB_OUTSIDE_URL,
)

log = logging.getLogger(__name__)

submission_url = "{external_url}/submission/{job_id}"


job_finished_template = """The job {job_id} finished.
The exit status was {status}.
To see further results visit:
{url}"""

job_submitted_template = """The job {job_id} was submitted.
To see the progress go to:
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


def send_mail(recipient, subject, content):
    """Send an email via SMTP with STARTTLS.

    In test/dev environments (EMAIL_SERVER == "test"), logs the email
    instead of sending it.
    """
    if EMAIL_SERVER == "test":
        log.info(
            f"Test mode — email not sent. "
            f"To: {recipient}, Subject: {subject}, Body: {content}",
        )
        return

    log.debug(
        f"Send mail to {recipient} with subject {subject}.",
    )
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = recipient
    msg["Subject"] = subject

    msg.attach(MIMEText(content, "plain"))

    log.debug(
        f"Connect to email server {EMAIL_SERVER}:{EMAIL_PORT}.",
    )
    server = smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT)
    server.starttls()
    server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
    server.sendmail(EMAIL_SENDER, recipient, msg.as_string())
    server.quit()


def send_finished_mail(job):
    """Send a notification email to the user that the job finished."""
    if job.model.email == "" or job.notified_end:
        return
    log.info("Send mail about finished job.")

    # Use configured external URL instead of Flask request context
    try:
        # Try to get URL from Flask request context (when called from webserver)
        external_url = request.url_root
    except RuntimeError:
        # Fallback to configured URL (when called from Celery worker)
        external_url = WEB_OUTSIDE_URL

    url = submission_url.format(job_id=job.job_id, external_url=external_url)
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
    log.info(f"Send mail about submitted job {job.job_id}.")

    # Use configured external URL instead of Flask request context
    try:
        # Try to get URL from Flask request context (when called from webserver)
        external_url = request.url_root
    except RuntimeError:
        # Fallback to configured URL (when called from Celery worker)
        external_url = WEB_OUTSIDE_URL

    url = submission_url.format(job_id=job.job_id, external_url=external_url)
    content = job_submitted_template.format(
        job_id=job.job_id,
        status=job.status,
        url=url,
    )
    send_mail(job.model.email, f'Job "{job.job_id}" submitted', content)


def wait_for_all_images_loaded(driver, timeout=5):
    """Wait for all images on the page to be loaded.

    Args:
        driver: Selenium WebDriver instance
        timeout: Maximum time to wait in seconds (default: 5)

    Returns:
        bool: True if all images loaded within timeout, False otherwise
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        all_loaded = driver.execute_script(
            """
            return Array.from(document.images).every(img => img.complete);
        """
        )
        if all_loaded:
            return True
        time.sleep(0.1)
    return False
