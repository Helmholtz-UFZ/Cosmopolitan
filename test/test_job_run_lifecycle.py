"""Test the computation job's run lifecycle: status in the job row, log in the job log.

The job row is the only source of a job's status (cosmo-ecosystem ADR 0002); the
log of the latest run is the job log in the database (``cosmo_ecosystem.job_log``),
readable from any pod. Runs against real Postgres and object storage. Only the
prediction itself (``smp_main``) is replaced, and only where a test needs a
prediction outcome; mails are observed through the test-mode mail log.
"""

import json
import logging
import os

import pytest
from cosmo_ecosystem import job_log, job_persistence
from cosmo_ecosystem.db_manager import DbManager
from cosmo_ecosystem.job_log import JobLogHandler
from cosmo_ecosystem.object_storage_manager import get_remote_files

from cosmopolitan_app.background_job_manager import background_job_manager
from cosmopolitan_app.config import (
    MAINTAINER_EMAIL,
    OBJECT_STORAGE_BUCKET,
    OBJECT_STORAGE_REMOTE_NAME,
)
from cosmopolitan_app.constants.general import LOG_FILE_NAME
from cosmopolitan_app.job import Job
from cosmopolitan_app.postgres_manager import PostgresManager
from cosmopolitan_app.tasks import computation_tasks

JOB_ID = "test_job_run_lifecycle"
USER_EMAIL = "test@ufz.de"
OUTPUT_FILE = "prediction_output.txt"
MAIL_LOG_PREFIX = "Test mode — email not sent."


def _delete_everywhere(job_id):
    """Delete the job if it exists, job log included, even if its row cannot load."""
    if PostgresManager.check_existence(job_id):
        job_persistence.delete_job(job_id)
    job_log.clear(job_id)


@pytest.fixture
def job_id():
    """Yield the id of a new, unsubmitted job; it is gone before and after the test."""
    _delete_everywhere(JOB_ID)
    Job(new_job_id=JOB_ID)
    yield JOB_ID
    _delete_everywhere(JOB_ID)


@pytest.fixture
def submitted_job_id(job_id):
    """Return the id of a job as submit leaves it: RUNNING, with a user email."""
    job = Job(job_id)
    job.model.email = USER_EMAIL
    job.submitted = True
    job.status = "RUNNING"
    job.save()
    return job_id


def _prediction_returning(model):
    """Return a stand-in for smp_main that writes an output and returns model."""

    def prediction(verbosity, work_dir):
        with open(os.path.join(work_dir, OUTPUT_FILE), "w", encoding="UTF-8") as f:
            f.write("prediction\n")
        return model

    return prediction


def _messages(caplog):
    """Return the captured log messages in order."""
    return [record.getMessage() for record in caplog.records]


def _mails(caplog):
    """Return the test-mode mails in order, as their logged message."""
    return [m for m in _messages(caplog) if m.startswith(MAIL_LOG_PREFIX)]


def _index_of(messages, fragment):
    """Return the index of the first message containing fragment."""
    return next(i for i, message in enumerate(messages) if fragment in message)


def test_a_prediction_without_a_model_ends_failed_with_the_reason_in_the_job_log(
    submitted_job_id, monkeypatch
):
    monkeypatch.setattr(computation_tasks, "smp_main", _prediction_returning(None))

    computation_tasks.start_computation_task(None, submitted_job_id)

    assert DbManager.get_job_columns(submitted_job_id)["status"] == "FAILED"
    assert "returned no model" in job_log.read(submitted_job_id)


def _prediction_raising(error):
    """Return a stand-in for smp_main that raises error."""

    def prediction(verbosity, work_dir):
        raise error

    return prediction


def test_a_crashed_run_mails_user_and_maintainer_after_the_run(
    submitted_job_id, monkeypatch, caplog
):
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(
        computation_tasks,
        "smp_main",
        _prediction_raising(ValueError("covariate raster missing")),
    )

    computation_tasks.start_computation_task(None, submitted_job_id)

    messages = _messages(caplog)
    run_end = _index_of(messages, f"Job run of job {submitted_job_id} failed")
    finished = _index_of(messages, f'Subject: Job "{submitted_job_id}" failed')
    maintainer = _index_of(messages, f"To: {MAINTAINER_EMAIL}")
    assert run_end < finished
    assert run_end < maintainer
    assert "covariate raster missing" in messages[maintainer]
    assert Job(submitted_job_id).notified_end is True


def test_an_aborted_prediction_mails_only_the_user(
    submitted_job_id, monkeypatch, caplog
):
    """smp_main returning no model usually means bad input: not the maintainer's."""
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(computation_tasks, "smp_main", _prediction_returning(None))

    computation_tasks.start_computation_task(None, submitted_job_id)

    mails = _mails(caplog)
    assert [m for m in mails if f"To: {MAINTAINER_EMAIL}" in m] == []
    assert len([m for m in mails if f"To: {USER_EMAIL}" in m]) == 2
    assert Job(submitted_job_id).notified_end is True


def test_the_users_mail_on_a_failed_run_says_it_failed(
    submitted_job_id, monkeypatch, caplog
):
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(computation_tasks, "smp_main", _prediction_returning(None))

    computation_tasks.start_computation_task(None, submitted_job_id)

    (mail,) = [
        m
        for m in _mails(caplog)
        if f'Subject: Job "{submitted_job_id}" ' in m and "submitted" not in m
    ]
    assert f'Subject: Job "{submitted_job_id}" failed' in mail
    assert f"The job {submitted_job_id} failed." in mail
    assert "finished" not in mail


def test_a_job_that_cannot_be_loaded_ends_failed_with_the_reason_in_the_job_log(
    submitted_job_id,
):
    """The submission mail loads the job too: its failure must not leave RUNNING."""
    job_persistence.update_columns(submitted_job_id, {"input_data": "not json"})

    # The finished mail after the run needs the job as well; that failure is the
    # task's (worker log), the row and the job log already tell the user.
    with pytest.raises(json.JSONDecodeError):
        computation_tasks.start_computation_task(None, submitted_job_id)

    assert DbManager.get_job_columns(submitted_job_id)["status"] == "FAILED"
    assert "JSONDecodeError" in job_log.read(submitted_job_id)


def _prediction_deleting_the_job(verbosity, work_dir):
    """Stand in for smp_main while the user deletes the job."""
    job_persistence.delete_job(JOB_ID)
    return "model"


def test_a_job_deleted_during_its_run_ends_the_task_without_mails(
    submitted_job_id, monkeypatch, caplog
):
    """ADR 0002: the task does not fail for its job's outcome; a deleted job has none."""
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(computation_tasks, "smp_main", _prediction_deleting_the_job)

    computation_tasks.start_computation_task(None, submitted_job_id)

    mails = _mails(caplog)
    assert [m for m in mails if "submitted" not in m] == []
    assert any(
        record.levelno == logging.INFO
        and submitted_job_id in record.getMessage()
        and "deleted" in record.getMessage()
        for record in caplog.records
    )


def _prediction_logging_then_raising(verbosity, work_dir):
    """Stand in for smp_main: a long DEBUG log, then a crash."""
    logger = logging.getLogger("test.prediction")
    for number in range(500):
        logger.debug(f"record {number:04d}")
    raise ValueError("covariate raster missing")


def test_the_maintainer_mail_holds_only_the_tail_of_the_job_log(
    submitted_job_id, monkeypatch, caplog
):
    """A DEBUG job log can run to megabytes; the end holds the error."""
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(computation_tasks, "smp_main", _prediction_logging_then_raising)

    computation_tasks.start_computation_task(None, submitted_job_id)

    (mail,) = [m for m in _mails(caplog) if f"To: {MAINTAINER_EMAIL}" in m]
    assert "covariate raster missing" in mail
    assert "record 0499" in mail
    assert "record 0000" not in mail
    assert "truncated" in mail


def test_a_successful_run_stores_its_outputs_and_mails_after_the_run(
    submitted_job_id, monkeypatch, caplog
):
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(computation_tasks, "smp_main", _prediction_returning("model"))

    computation_tasks.start_computation_task(None, submitted_job_id)

    assert DbManager.get_job_columns(submitted_job_id)["status"] == "COMPLETED"
    assert OUTPUT_FILE in get_remote_files(
        f"{OBJECT_STORAGE_REMOTE_NAME}:{OBJECT_STORAGE_BUCKET}/{submitted_job_id}"
    )
    messages = _messages(caplog)
    run_end = _index_of(messages, f"Job {submitted_job_id} completed")
    finished = _index_of(messages, f'Subject: Job "{submitted_job_id}" finished')
    assert run_end < finished
    assert "The exit status was COMPLETED" in messages[finished]
    assert [m for m in _mails(caplog) if f"To: {MAINTAINER_EMAIL}" in m] == []


def test_reload_logs_shows_the_job_log_on_a_pod_without_the_jobs_files(job_id):
    """A running worker writes only to the job log; the web reads it from there."""
    logger = logging.getLogger("test.worker.job_run")
    handler = JobLogHandler(job_id)
    logger.addHandler(handler)
    try:
        logger.info("Random Forest Mean Absolute Error: 0.04")
    finally:
        logger.removeHandler(handler)
        handler.close()
    job = Job(job_id)
    assert not os.path.exists(os.path.join(job.working_dir, LOG_FILE_NAME))

    job.reload_logs()

    assert "Random Forest Mean Absolute Error: 0.04" in job.logs


def test_submit_writes_running_before_the_enqueue(job_id, monkeypatch):
    """A fast worker's final status must not be overwritten by a late RUNNING."""
    status_at_enqueue = []

    def enqueue(submitted_job):
        status_at_enqueue.append(DbManager.get_job_columns(job_id)["status"])
        job_persistence.update_columns(job_id, {"status": "COMPLETED"})
        return "task-id", False

    monkeypatch.setattr(background_job_manager, "submit_computation_job", enqueue)

    Job(job_id).submit()

    assert status_at_enqueue == ["RUNNING"]
    assert DbManager.get_job_columns(job_id)["status"] == "COMPLETED"


def test_a_failed_enqueue_ends_failed_with_the_reason_in_the_job_log(
    job_id, monkeypatch
):
    def enqueue(submitted_job):
        raise ConnectionError("Error -3 connecting to redis")

    monkeypatch.setattr(background_job_manager, "submit_computation_job", enqueue)

    Job(job_id).submit()

    assert DbManager.get_job_columns(job_id)["status"] == "FAILED"
    assert f"Cannot start job {job_id}." in job_log.read(job_id)


def test_an_enqueue_reporting_failure_ends_failed_with_the_reason_in_the_job_log(
    job_id, monkeypatch
):
    """The enqueue can also report failure without raising."""

    def enqueue(submitted_job):
        return None, True

    monkeypatch.setattr(background_job_manager, "submit_computation_job", enqueue)

    Job(job_id).submit()

    assert DbManager.get_job_columns(job_id)["status"] == "FAILED"
    assert f"Cannot start job {job_id}." in job_log.read(job_id)
