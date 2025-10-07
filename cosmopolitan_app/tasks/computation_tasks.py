"""Computation tasks for soil moisture prediction jobs."""

import logging
import os
import traceback
from logging.config import dictConfig
from smtplib import SMTPAuthenticationError
from time import sleep

from celery import Task

from cosmopolitan_app.config import DEBUG
from cosmopolitan_app.job import LOG_FILE_NAME
from cosmopolitan_app.logger import get_logger_config_compuation, get_logger_config_web
from cosmopolitan_app.utils import send_finished_mail, send_submission_mail


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
        logging.error(f"Task {task_id} failed: {exc}", extra={"tag": "job_submission"})
        logging.error(f"Traceback: {einfo}", extra={"tag": "job_submission"})


def start_computation_task(self, job_id):
    """Celery task version of start_computation function.

    Args:
        job_id: ID of the job to process

    This replaces the original start_computation function from job.py
    with a Celery-compatible version.
    """
    # Import here to avoid circular imports
    from cosmopolitan_app.job import Job

    # Reconstruct the job object from the job_id
    job = Job(job_id=job_id)
    try:
        try:
            send_submission_mail(job)
        except SMTPAuthenticationError:
            logging.error(
                "Failed to send submission mail.", extra={"tag": "email_service"}
            )

        dictConfig(
            get_logger_config_compuation(os.path.join(job.working_dir, LOG_FILE_NAME))
        )

        try:
            # Import here to avoid circular imports
            from soil_moisture_prediction.smp_cli import main

            rfo_model = main(verbosity="debug", work_dir=job.working_dir)
            if rfo_model is None:
                job.status = "FAILED"
            else:
                job.status = "COMPLETED"
        except Exception as e:  # noqa
            # Log error to log file
            logging.error("An error occurred", extra={"tag": "job_submission"})
            logging.error(traceback.format_exc(), extra={"tag": "job_submission"})
            # Ensure all log buffers are flushed before switching config
            flush_all_handlers()
            # Log error to web logs
            dictConfig(get_logger_config_web(DEBUG))
            job.status = "FAILED"
            logging.error(
                f"Computation failed:\n{repr(e)}\n\n{traceback.format_exc()}",
                extra={"tag": "job_submission"},
            )

        sleep(1)
        # Ensure all log buffers are flushed before switching config
        flush_all_handlers()
        dictConfig(get_logger_config_web(DEBUG))
        logging.info("Computation finished.", extra={"tag": "job_submission"})

        job.save()
        try:
            send_finished_mail(job)
        except SMTPAuthenticationError:
            logging.error(
                "Failed to send finished mail.", extra={"tag": "email_service"}
            )

    except Exception as e:  # noqa
        # Ensure all log buffers are flushed before switching config
        flush_all_handlers()
        dictConfig(get_logger_config_web(DEBUG))
        job.status = "FAILED"
        logging.error(
            f"Job {job.job_id} failed:\n{repr(e)}\n\n{traceback.format_exc()}"
        )
        job.save()
        try:
            send_finished_mail(job)
        except SMTPAuthenticationError:
            logging.error(
                "Failed to send finished mail.", extra={"tag": "email_service"}
            )
