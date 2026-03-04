"""Computation tasks for soil moisture prediction jobs."""

import logging
import os
import traceback
from logging.config import dictConfig
from smtplib import SMTPAuthenticationError

from celery import Task

from cosmopolitan_app.config import MAINTAINER_EMAIL
from cosmopolitan_app.job import LOG_FILE_NAME
from cosmopolitan_app.logger import (
    get_logger_config_compuation,
    get_logger_config_worker,
)
from cosmopolitan_app.utils import send_finished_mail, send_mail, send_submission_mail

log = logging.getLogger(__name__)


def flush_all_handlers():
    """Flush all logging handlers."""
    logger = logging.getLogger()
    for handler in logger.handlers:
        try:
            handler.flush()
        except (
            Exception
        ):  # flush can fail on any handler (file, DB, network); must not disrupt caller
            pass


class ComputationTask(Task):
    """Base class for computation tasks with custom error handling."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        log.error(f"Task {task_id} failed: {exc}", extra={"tag": "worker"})
        log.error(f"Traceback: {einfo}", extra={"tag": "worker"})


def start_computation_task(self, job_id):
    """Celery task version of start_computation function.

    Args:
        job_id: ID of the job to process

    This replaces the original start_computation function from job.py
    with a Celery-compatible version.
    """
    log.info(f"Starting computation for job {job_id}", extra={"tag": "worker"})
    try:
        # Import here to avoid circular imports
        from soil_moisture_prediction.smp_cli import main

        from cosmopolitan_app.job import Job

        log.debug("Modules imported", extra={"tag": "worker"})

        job = Job(job_id=job_id)
        log.debug("Job loaded", extra={"tag": "worker"})

        dictConfig(get_logger_config_worker())

        try:
            send_submission_mail(job)
        except SMTPAuthenticationError:
            log.error("Failed to send submission mail.", extra={"tag": "worker"})

        dictConfig(
            get_logger_config_compuation(os.path.join(job.working_dir, LOG_FILE_NAME))
        )

        rfo_model = main(verbosity="debug", work_dir=job.working_dir)
        if rfo_model is None:
            job.status = "FAILED"
        else:
            job.status = "COMPLETED"

        flush_all_handlers()
        dictConfig(get_logger_config_worker())
        log.info("Computation finished.", extra={"tag": "worker"})

        job.save()
        try:
            send_finished_mail(job)
        except SMTPAuthenticationError:
            log.error("Failed to send finished mail.", extra={"tag": "worker"})
    except Exception as e:  # catch-all: must log, email, and mark job FAILED  # noqa
        # Log error to log file
        log.error("An error occurred", extra={"tag": "worker"})
        log.error(traceback.format_exc(), extra={"tag": "worker"})
        # Ensure all log buffers are flushed before switching config
        flush_all_handlers()
        # Log error to web logs
        dictConfig(get_logger_config_worker())
        email_subject = "Computation task failed"
        email_body = f"""
        Error: {str(e)}\n\n
        Traceback info: {traceback.format_exc()}\n\n
        """
        try:
            send_mail(MAINTAINER_EMAIL, email_subject, email_body)
        except Exception:  # noqa - must not let email failure crash task error path
            log.error(
                "Failed to send task failure email",
                exc_info=True,
                extra={"tag": "worker"},
            )
        job.status = "FAILED"
        job.save()
