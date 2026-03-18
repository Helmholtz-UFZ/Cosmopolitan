"""Maintenance tasks for periodic cleanup and database updates."""

import logging
import os
import shutil
import traceback
from datetime import date, datetime, timedelta

from celery import Task

from cosmopolitan_app.config import MAINTAINER_EMAIL, WEB_WORK_DIR
from cosmopolitan_app.constants import (
    DAYS_DELETE_NOT_SUBMITTED,
    DAYS_DELETE_SUBMITTED,
    LOG_RETENTION_DAYS,
)
from cosmopolitan_app.object_storage_manager import delete_directory_from_storage
from cosmopolitan_app.postgres_manager import PostgresManager
from cosmopolitan_app.timeio_manager import update_crns_measurments
from cosmopolitan_app.utils import send_mail

log = logging.getLogger(__name__)


def clean_up_jobs(
    days_delete_not_submitted=DAYS_DELETE_NOT_SUBMITTED,
    days_delete_submitted=DAYS_DELETE_SUBMITTED,
):
    """Delete jobs depending on their status and age."""
    log.info("Start cleaning up jobs.")
    kept_jobs = []

    # Define the time thresholds
    job_end_of_life_not_submitted = date.today() - timedelta(
        days=days_delete_not_submitted
    )
    job_end_of_life_submitted = date.today() - timedelta(days=days_delete_submitted)

    for job_id, job_info in PostgresManager.list_jobs().items():
        submitted = job_info["submitted"]
        start_date = job_info["start_date"]
        log.debug(f"Check job {job_id}.")
        if not submitted and start_date <= job_end_of_life_not_submitted:
            log.debug(
                f"Job was not submit and is older than {days_delete_not_submitted} days.",  # noqa
            )
            PostgresManager.delete_job(job_id)
        elif start_date <= job_end_of_life_submitted:
            log.debug(
                f"Job older than {days_delete_submitted} days.",
            )
            PostgresManager.delete_job(job_id)
        else:
            log.debug("Job will be kept.")
            kept_jobs.append(job_id)

    # Delete directorys locally
    log.debug("Clean up directorys locally.")
    for dir_name in os.listdir(WEB_WORK_DIR):
        dir_path = os.path.join(WEB_WORK_DIR, dir_name)
        if os.path.isdir(dir_path) and dir_name not in kept_jobs:
            shutil.rmtree(dir_path)
            delete_directory_from_storage(dir_name)


class MaintenanceTask(Task):
    """Base class for maintenance tasks with custom error handling."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        log.error(f"Maintenance task {task_id} failed: {exc}")
        log.error(f"Traceback: {einfo}")


def cleanup_task(self):
    """Celery task version of clean_up function.

    This replaces the APScheduler clean_up job.
    """
    log.info("Start cleaning up.")
    clean_up_jobs()

    log_cutoff = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    log.info(f"Cleaning up logs older than {log_cutoff}")
    PostgresManager.delete_logs_older_than(log_cutoff)


def update_db_task(self):
    """Celery task version of update_db function.

    This replaces the APScheduler update_db job.
    Tracks run progress in update_db_runs table for log filtering.
    """
    log.info("Start updating database.")

    # Create run record with current PID for log filtering
    pid = os.getpid()
    run_id = PostgresManager.create_update_run(pid)
    log.info(f"Created update run {run_id} with PID {pid}")

    try:
        update_crns_measurments()
        PostgresManager.complete_update_run(run_id, "completed")
        log.info(f"Update run {run_id} completed successfully")
    except Exception as error:  # catch-all: must log and email all failures  # noqa
        PostgresManager.complete_update_run(run_id, "failed")
        email_subject = f"Error updating database: {error}"
        email_body = f"""
        Traceback info: {traceback.format_exc()}\n\n
        """
        try:
            send_mail(MAINTAINER_EMAIL, email_subject, email_body)
        except Exception:  # noqa - must not let email failure crash maintenance error path
            log.error(
                "Failed to send maintenance error email",
                exc_info=True,
            )
        log.error(email_subject)
        log.error(email_body)
