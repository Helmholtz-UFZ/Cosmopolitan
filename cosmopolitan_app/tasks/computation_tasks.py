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


class ComputationTask(Task):
    """Base class for computation tasks with custom error handling."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logging.error(f"Task {task_id} failed: {exc}")
        logging.error(f"Traceback: {einfo}")


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
            logging.error("Failed to send submission mail.")

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
            logging.error("An error occurred")
            logging.error(traceback.format_exc())
            # Log error to web logs
            dictConfig(get_logger_config_web(DEBUG))
            job.status = "FAILED"
            logging.error(f"Computation failed:\n{repr(e)}\n\n{traceback.format_exc()}")

        sleep(1)
        dictConfig(get_logger_config_web(DEBUG))
        logging.info("Computation finished.")

        job.save()
        try:
            send_finished_mail(job)
        except SMTPAuthenticationError:
            logging.error("Failed to send finished mail.")

    except Exception as e:  # noqa
        dictConfig(get_logger_config_web(DEBUG))
        job.status = "FAILED"
        logging.error(
            f"Job {job.job_id} failed:\n{repr(e)}\n\n{traceback.format_exc()}"
        )
        job.save()
        try:
            send_finished_mail(job)
        except SMTPAuthenticationError:
            logging.error("Failed to send finished mail.")
