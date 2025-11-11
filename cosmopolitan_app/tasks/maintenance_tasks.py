"""Maintenance tasks for periodic cleanup and database updates."""

import logging
import os
import shutil
import traceback
from datetime import date, datetime, timedelta

from celery import Task

from cosmopolitan_app.config import MAINTAINER_EMAIL, WEB_WORK_DIR
from cosmopolitan_app.constants import (
    DAYS_DELETE_NOT_SUMBITTED,
    DAYS_DELETE_SUMBITTED,
    LOG_RETENTION_DAYS,
)
from cosmopolitan_app.object_storage_manager import delete_directory_from_storage
from cosmopolitan_app.postgres_manager import PostgresManager
from cosmopolitan_app.timeio_manager import update_crns_measurments
from cosmopolitan_app.utils import send_mail


def clean_up_jobs(
    days_delete_not_submitted=DAYS_DELETE_NOT_SUMBITTED,
    days_delete_submitted=DAYS_DELETE_SUMBITTED,
):
    """Delete jobs depending on their status and age."""
    logging.info("Start cleaning up jobs.", extra={"tag": "maintenance"})
    kept_jobs = []

    # Define the time thresholds
    job_end_of_life_not_submitted = date.today() - timedelta(
        days=days_delete_not_submitted
    )
    job_end_of_life_submitted = date.today() - timedelta(days=days_delete_submitted)

    for job_id, job_info in PostgresManager.list_jobs().items():
        submitted = job_info["submitted"]
        start_date = job_info["start_date"]
        logging.debug(f"Check job {job_id}.", extra={"tag": "maintenance"})
        if not submitted and start_date <= job_end_of_life_not_submitted:
            logging.debug(
                f"Job was not submit and is older than {days_delete_not_submitted} days.",  # noqa
                extra={"tag": "maintenance"},
            )
            PostgresManager.delete_job(job_id)
        elif start_date <= job_end_of_life_submitted:
            logging.debug(
                f"Job older than {days_delete_submitted} days.",
                extra={"tag": "maintenance"},
            )
            PostgresManager.delete_job(job_id)
        else:
            logging.debug("Job will be kept.", extra={"tag": "maintenance"})
            kept_jobs.append(job_id)

    # Delete directorys locally
    logging.debug("Clean up directorys locally.", extra={"tag": "maintenance"})
    for dir_name in os.listdir(WEB_WORK_DIR):
        dir_path = os.path.join(WEB_WORK_DIR, dir_name)
        if os.path.isdir(dir_path) and dir_name not in kept_jobs:
            shutil.rmtree(dir_path)
            delete_directory_from_storage(dir_name)


class MaintenanceTask(Task):
    """Base class for maintenance tasks with custom error handling."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logging.error(
            f"Maintenance task {task_id} failed: {exc}", extra={"tag": "maintenance"}
        )
        logging.error(f"Traceback: {einfo}", extra={"tag": "maintenance"})


def cleanup_task(self):
    """Celery task version of clean_up function.

    This replaces the APScheduler clean_up job.
    """
    logging.info("Start cleaning up.", extra={"tag": "maintenance"})
    clean_up_jobs()

    log_cutoff = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    logging.info(
        f"Cleaning up logs older than {log_cutoff}", extra={"tag": "maintenance"}
    )
    PostgresManager.delete_logs_older_than(log_cutoff)


def update_db_task(self):
    """Celery task version of update_db function.

    This replaces the APScheduler update_db job.
    """
    logging.info("Start updating database.", extra={"tag": "time_io"})
    try:
        update_crns_measurments()
    except Exception as error:  # noqa
        email_subject = f"Error updating database: {error}"
        email_body = f"""
        Traceback info: {traceback.format_exc()}\n\n
        """
        send_mail(MAINTAINER_EMAIL, email_subject, email_body)
        logging.error(email_subject, extra={"tag": "time_io"})
        logging.error(email_body, extra={"tag": "time_io"})
