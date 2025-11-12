"""Computation tasks for soil moisture prediction jobs."""

import logging
import os
import traceback
from logging.config import dictConfig
from smtplib import SMTPAuthenticationError

from celery import Task

from cosmopolitan_app.config import DEBUG, MAINTAINER_EMAIL
from cosmopolitan_app.job import LOG_FILE_NAME
from cosmopolitan_app.logger import get_logger_config_compuation, get_logger_config_web
from cosmopolitan_app.utils import send_finished_mail, send_mail, send_submission_mail


def flush_all_handlers():
    """Flush all logging handlers."""
    logger = logging.getLogger()
    for handler in logger.handlers:
        try:
            handler.flush()
        except Exception:  # noqa
            # Silently ignore flush errors to avoid disrupting the main flow
            pass


class ComputationTask(Task):
    """Base class for computation tasks with custom error handling."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logging.error(f"Task {task_id} failed: {exc}", extra={"tag": "worker"})
        logging.error(f"Traceback: {einfo}", extra={"tag": "worker"})


def start_computation_task(self, job_id):
    """Celery task version of start_computation function.

    Args:
        job_id: ID of the job to process

    This replaces the original start_computation function from job.py
    with a Celery-compatible version.
    """
    logging.info(f"Starting computation for job {job_id}", extra={"tag": "worker"})
    try:
        # Import here to avoid circular imports
        from soil_moisture_prediction.smp_cli import main

        from cosmopolitan_app.job import Job

        logging.debug("Modules imported", extra={"tag": "worker"})

        job = Job(job_id=job_id)
        logging.debug("Job loaded", extra={"tag": "worker"})

        try:
            send_submission_mail(job)
        except SMTPAuthenticationError:
            logging.error("Failed to send submission mail.", extra={"tag": "worker"})

        dictConfig(
            get_logger_config_compuation(os.path.join(job.working_dir, LOG_FILE_NAME))
        )

        rfo_model = main(verbosity="debug", work_dir=job.working_dir)
        if rfo_model is None:
            job.status = "FAILED"
        else:
            job.status = "COMPLETED"

        flush_all_handlers()
        dictConfig(get_logger_config_web(DEBUG))
        logging.info("Computation finished.", extra={"tag": "worker"})

        job.save()
        try:
            send_finished_mail(job)
        except SMTPAuthenticationError:
            logging.error("Failed to send finished mail.", extra={"tag": "worker"})
    except Exception as e:  # noqa
        # Log error to log file
        logging.error("An error occurred", extra={"tag": "worker"})
        logging.error(traceback.format_exc(), extra={"tag": "worker"})
        # Ensure all log buffers are flushed before switching config
        flush_all_handlers()
        # Log error to web logs
        dictConfig(get_logger_config_web(DEBUG))
        email_subject = "Computation task failed"
        email_body = f"""
        Error: {str(e)}\n\n
        Traceback info: {traceback.format_exc()}\n\n
        """
        send_mail(MAINTAINER_EMAIL, email_subject, email_body)
        job.status = "FAILED"
        job.save()
