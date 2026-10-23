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
from cosmopolitan_app.error_handling import PredictionAborted
from cosmopolitan_app.job import Job

log = logging.getLogger(__name__)


def start_computation_task(self, job_id):
    """Celery task: run the soil moisture prediction of a job.

    Sends the submission mail, runs the prediction as a job run, then sends the
    finished mail for either outcome, from the job's row as the run left it, and
    the maintainer mail for a failed run that was not an aborted prediction.

    Args:
        job_id: ID of the job to process
    """
    log.info(f"Starting computation for job {job_id}")
    send_submission_mail(Job(job_id=job_id))

    # run swallows the compute's exception and returns only the status, so the
    # compute records an abort in this flag; an abort (smp_main returned no
    # model, usually bad input) is the user's to fix and mails no maintainer.
    aborted = False

    def compute(job_id, work_dir):
        nonlocal aborted
        try:
            predict(job_id, work_dir)
        except PredictionAborted:
            aborted = True
            raise

    status = job_run.run(job_id, compute, EXCLUDED_LOG_PACKAGES)
    log.info(f"Computation of job {job_id} finished with status {status}")

    send_finished_mail(Job(job_id=job_id))
    if status == "FAILED" and not aborted:
        send_mail(
            MAINTAINER_EMAIL,
            "Computation task failed",
            f"The job run of job {job_id} failed. Its job log:\n\n"
            f"{job_log.read(job_id)}",
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
