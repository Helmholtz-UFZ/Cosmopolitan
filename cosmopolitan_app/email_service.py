"""Email service for sending notifications via SMTP."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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
    try:
        with smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, recipient, msg.as_string())
        log.info(f"Email sent to {recipient}: {subject}")
    except smtplib.SMTPException:
        log.error(f"Failed to send email to {recipient}: {subject}", exc_info=True)


def send_finished_mail(job):
    """Send a notification email to the user that the job finished."""
    if job.model.email == "" or job.notified_end:
        return
    log.info("Send mail about finished job.")

    # Try to get URL from Flask request context (when called from webserver)
    try:
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

    # Try to get URL from Flask request context (when called from webserver)
    try:
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
