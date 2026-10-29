"""Computation tasks for soil moisture prediction jobs.

The prediction runs through the framework's job run (``cosmo_ecosystem.job_run.run``),
which captures the job log, fetches and uploads the work dir and writes the final
status to the job row. The job row is the only source of the job's status
(cosmo-ecosystem ADR 0002): a failed run ends as FAILED in the row and as a
successful Celery task.
"""

import logging

from cosmo_ecosystem import job_log, job_run
from soil_moisture_prediction.smp_cli import main as smp_main

from cosmopolitan_app.config import MAINTAINER_EMAIL
from cosmopolitan_app.constants.general import EXCLUDED_LOG_PACKAGES
from cosmopolitan_app.email_service import (
    send_finished_mail,
    send_mail,
    send_submission_mail,
)
from cosmopolitan_app.error_handling import JobNotFound, PredictionAborted
from cosmopolitan_app.job import Job

log = logging.getLogger(__name__)

# The maintainer mail carries only this many last lines of the job log: the log is
# kept at DEBUG and can run to megabytes, and the error is at its end.
MAINTAINER_MAIL_LOG_LINES = 200


def start_computation_task(self, job_id):
    """Celery task: run the soil moisture prediction of a job.

    Runs the submission mail and the prediction as a job run, then sends the
    finished mail for either outcome, from the job's row as the run left it, and
    the maintainer mail for a failed run that was not an aborted prediction. A job
    deleted during its run gets no mails.

    Args:
        job_id: ID of the job to process
    """
    log.info(f"Starting computation for job {job_id}")

    # run swallows the compute's exception and returns only the status, so the
    # compute records an abort in this flag; an abort (smp_main returned no
    # model, usually bad input) is the user's to fix and mails no maintainer.
    aborted = False

    def compute(job_id, work_dir):
        nonlocal aborted
        # Inside the run: loading the job can fail, and only the run turns a
        # failure into FAILED; outside it the row would stay RUNNING.
        send_submission_mail(Job(job_id=job_id))
        try:
            predict(job_id, work_dir)
        except PredictionAborted:
            aborted = True
            raise

    status = job_run.run(job_id, compute, EXCLUDED_LOG_PACKAGES)
    log.info(f"Computation of job {job_id} finished with status {status}")

    try:
        job = Job(job_id=job_id)
    except JobNotFound:
        log.info(f"Job {job_id} was deleted during its run; no mails are sent.")
        return
    send_finished_mail(job)
    if status == "FAILED" and not aborted:
        send_mail(
            MAINTAINER_EMAIL,
            "Computation task failed",
            f"The job run of job {job_id} failed. {_job_log_tail(job_id)}",
        )


def _job_log_tail(job_id):
    """Return the end of the job's job log for a mail, saying if it is truncated."""
    lines = job_log.read(job_id).splitlines()
    if len(lines) <= MAINTAINER_MAIL_LOG_LINES:
        return "Its job log:\n\n" + "\n".join(lines)
    return (
        f"The last {MAINTAINER_MAIL_LOG_LINES} of {len(lines)} lines of its job "
        "log (truncated):\n\n" + "\n".join(lines[-MAINTAINER_MAIL_LOG_LINES:])
    )


def predict(job_id, work_dir):
    """Run the soil moisture prediction on the job's work dir.

    The ``compute`` of the job run: it signals failure only by raising and writes
    no status; the run uploads the work dir and writes the status.

    Raises:
        PredictionAborted: If the prediction returns no model.
    """
    rfo_model = smp_main(verbosity="debug", work_dir=work_dir)
    if rfo_model is None:
        raise PredictionAborted(job_id)
    log.info("Computation finished.")
