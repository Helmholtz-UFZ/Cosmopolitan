"""Maintenance tasks: the nightly CRNS database update.

The nightly cleanup of old jobs and logs is the framework's
(``cosmo_ecosystem.tasks.maintenance_tasks``), scheduled by its Celery assembly.
"""

import logging
import os
import traceback

from cosmopolitan_app.config import MAINTAINER_EMAIL
from cosmopolitan_app.constants import CONSECUTIVE_FAILURES_BEFORE_MAIL
from cosmopolitan_app.postgres_manager import PostgresManager
from cosmopolitan_app.timeio_manager import update_crns_measurments
from cosmopolitan_app.email_service import send_mail

log = logging.getLogger(__name__)


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
        log.error(email_subject)
        log.error(email_body)

        # Always logged, but only mailed once the failure has persisted. The
        # upstream STA goes away for a few minutes during its own maintenance,
        # which is exactly when the nightly run hits it — one mail per night for
        # a self-healing outage trains the maintainer to ignore the mails.
        failures = PostgresManager.count_consecutive_failed_update_runs()
        if failures < CONSECUTIVE_FAILURES_BEFORE_MAIL:
            log.warning(
                f"Update run {run_id} failed ({failures} in a row). Not mailing "
                f"until {CONSECUTIVE_FAILURES_BEFORE_MAIL} consecutive failures.",
            )
            return

        email_subject = f"{email_subject} ({failures} nights in a row)"
        try:
            send_mail(MAINTAINER_EMAIL, email_subject, email_body)
        except Exception:  # noqa - must not let email failure crash maintenance error path
            log.error(
                "Failed to send maintenance error email",
                exc_info=True,
            )
