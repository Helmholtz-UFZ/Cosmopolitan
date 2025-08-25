"""Maintenance tasks for periodic cleanup and database updates."""

import logging
import traceback
from datetime import datetime, timedelta

from celery import Task

from cosmopolitan_app.config import MAINTAINER_EMAIL
from cosmopolitan_app.constants import LOG_RETENTION_DAYS
from cosmopolitan_app.postgres_manager import PostgresManager
from cosmopolitan_app.timeio_manager import update_crns_measurments
from cosmopolitan_app.utils import clean_up_jobs, send_mail


class MaintenanceTask(Task):
    """Base class for maintenance tasks with custom error handling."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logging.error(f"Maintenance task {task_id} failed: {exc}")
        logging.error(f"Traceback: {einfo}")


def cleanup_task(self):
    """Celery task version of clean_up function.

    This replaces the APScheduler clean_up job.
    """
    logging.info("Start cleaning up.")
    clean_up_jobs()

    log_cutoff = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    logging.info(f"Cleaning up logs older than {log_cutoff}")
    PostgresManager.delete_logs_older_than(log_cutoff)


def update_db_task(self):
    """Celery task version of update_db function.

    This replaces the APScheduler update_db job.
    """
    logging.info("Start updating database.")
    try:
        update_crns_measurments()
    except Exception as error:  # noqa
        email_subject = f"Error updating database: {error}"
        email_body = f"""
        Traceback info: {traceback.format_exc()}\n\n
        """
        send_mail(MAINTAINER_EMAIL, email_subject, email_body)
        logging.error(email_subject)
        logging.error(email_body)
