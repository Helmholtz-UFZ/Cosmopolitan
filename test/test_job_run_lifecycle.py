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
from datetime import date

import pytest
from sqlalchemy import text

from cosmo_ecosystem import job_log, job_persistence, job_run
from cosmo_ecosystem.db_manager import DbManager
from cosmo_ecosystem.job_log import JobLogHandler
from cosmo_ecosystem.object_storage_manager import (
    ObjectStorageError,
    get_remote_files,
)

from cosmopolitan_app import submissions
from cosmopolitan_app.config import (
    MAINTAINER_EMAIL,
    OBJECT_STORAGE_BUCKET,
    OBJECT_STORAGE_REMOTE_NAME,
)
from cosmopolitan_app.constants.general import LOG_FILE_NAME
from cosmopolitan_app.error_handling import JobExists
from cosmopolitan_app.job import Job
from cosmopolitan_app.tasks import computation_tasks
from test.help_functions_tests import remove_job, set_row_columns

JOB_ID = "test_job_run_lifecycle"
USER_EMAIL = "test@ufz.de"
OUTPUT_FILE = "prediction_output.txt"
MAIL_LOG_PREFIX = "Test mode — email not sent."


@pytest.fixture
def job_id():
    """Yield the id of a new, unsubmitted job; it is gone before and after the test."""
    remove_job(JOB_ID)
    Job(new_job_id=JOB_ID)
    yield JOB_ID
    remove_job(JOB_ID)


@pytest.fixture
def submitted_job_id(job_id):
    """Return the id of a job as submit leaves it: RUNNING, with a user email."""
    job = Job(job_id)
    job.model.email = USER_EMAIL
    job.save()
    assert job_run.mark_queued(job_id)
    return job_id


def _set_heartbeat(job_id):
    """Give job_id's row a heartbeat, as a claimed run has: the database's now()."""
    with DbManager.session_scope() as session:
        session.execute(
            text("UPDATE jobs SET heartbeat_at = now() WHERE job_id = :job_id"),
            {"job_id": job_id},
        )


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
    """Stand in for smp_main while the run is swept and the job deleted.

    A RUNNING job cannot be deleted (ADR 0005); a lost run that was swept to
    FAILED can, while the run itself is still alive.
    """
    set_row_columns(JOB_ID, status="FAILED")
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
        set_row_columns(job_id, status="COMPLETED")
        return "task-id", False

    monkeypatch.setattr(submissions, "submit_computation_job", enqueue)

    Job(job_id).submit()

    assert status_at_enqueue == ["RUNNING"]
    assert DbManager.get_job_columns(job_id)["status"] == "COMPLETED"


def test_a_failed_enqueue_ends_failed_with_the_reason_in_the_job_log(
    job_id, monkeypatch
):
    def enqueue(submitted_job):
        raise ConnectionError("Error -3 connecting to redis")

    monkeypatch.setattr(submissions, "submit_computation_job", enqueue)

    Job(job_id).submit()

    assert DbManager.get_job_columns(job_id)["status"] == "FAILED"
    assert f"Cannot start job {job_id}." in job_log.read(job_id)


def test_an_enqueue_reporting_failure_ends_failed_with_the_reason_in_the_job_log(
    job_id, monkeypatch
):
    """The enqueue can also report failure without raising."""

    def enqueue(submitted_job):
        return None, True

    monkeypatch.setattr(submissions, "submit_computation_job", enqueue)

    Job(job_id).submit()

    assert DbManager.get_job_columns(job_id)["status"] == "FAILED"
    assert f"Cannot start job {job_id}." in job_log.read(job_id)


def test_submit_queues_the_run_with_no_heartbeat(job_id, monkeypatch):
    """A resubmitted job's old heartbeat is gone before the worker sees the message."""
    _set_heartbeat(job_id)
    row_at_enqueue = []

    def enqueue(submitted_job):
        row = DbManager.get_job_columns(job_id)
        row_at_enqueue.append((row["status"], row["heartbeat_at"]))
        return "task-id", False

    monkeypatch.setattr(submissions, "submit_computation_job", enqueue)

    Job(job_id).submit()

    assert row_at_enqueue == [("RUNNING", None)]


def test_a_resubmitted_job_is_queued_with_its_end_mail_pending(job_id, monkeypatch):
    """A failed run has sent its end mail; the next run must send its own."""
    set_row_columns(job_id, status="FAILED", notified_end=True)
    notified_at_enqueue = []

    def enqueue(submitted_job):
        notified_at_enqueue.append(DbManager.get_job_columns(job_id)["notified_end"])
        return "task-id", False

    monkeypatch.setattr(submissions, "submit_computation_job", enqueue)

    Job(job_id).submit()

    assert notified_at_enqueue == [False]


def test_saving_a_job_keeps_its_runs_heartbeat(submitted_job_id):
    """A page that saves the job during a run does not write the heartbeat back."""
    job = Job(submitted_job_id)
    _set_heartbeat(submitted_job_id)
    beat = DbManager.get_job_columns(submitted_job_id)["heartbeat_at"]

    job.save()

    assert DbManager.get_job_columns(submitted_job_id)["heartbeat_at"] == beat


def test_a_dropped_delivery_sends_no_mails_and_leaves_the_row(
    submitted_job_id, monkeypatch, caplog
):
    """A redelivery of a claimed run is dropped: no computation, no end mail."""
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(
        computation_tasks,
        "smp_main",
        _prediction_raising(AssertionError("a dropped delivery must not compute")),
    )
    _set_heartbeat(submitted_job_id)

    computation_tasks.start_computation_task(None, submitted_job_id)

    row = DbManager.get_job_columns(submitted_job_id)
    assert (row["status"], row["notified_end"]) == ("RUNNING", False)
    assert _mails(caplog) == []


def test_a_second_submit_queues_nothing(job_id, monkeypatch):
    """Two clicks, two tabs: exactly one submit queues a run and enqueues it."""
    enqueued = []

    def enqueue(submitted_job):
        enqueued.append(submitted_job.job_id)
        return "task-id", False

    monkeypatch.setattr(submissions, "submit_computation_job", enqueue)

    first = Job(job_id).submit()
    second = Job(job_id).submit()

    assert (first, second) == (True, False)
    assert enqueued == [job_id]
    assert DbManager.get_job_columns(job_id)["status"] == "RUNNING"


def test_a_lost_submit_keeps_the_job_log_and_the_end_mail_flag(job_id, monkeypatch):
    """A submit that loses the guard has no side effect, not even notified_end."""
    set_row_columns(job_id, status="COMPLETED", notified_end=True)
    job_log.append(job_id, "the live log line")
    monkeypatch.setattr(
        submissions,
        "submit_computation_job",
        _prediction_raising(AssertionError("a lost submit must not enqueue")),
    )

    assert Job(job_id).submit() is False

    row = DbManager.get_job_columns(job_id)
    assert (row["status"], row["notified_end"]) == ("COMPLETED", True)
    assert "the live log line" in job_log.read(job_id)


def test_a_failure_in_the_pull_after_the_guard_ends_failed(job_id, monkeypatch):
    """The queued run has no message to run it: the row must not stay RUNNING."""

    def pull(job_id):
        raise ObjectStorageError("object storage is down")

    monkeypatch.setattr(job_persistence, "work_dir", pull)

    with pytest.raises(ObjectStorageError):
        Job(job_id).submit()

    assert DbManager.get_job_columns(job_id)["status"] == "FAILED"
    assert f"Cannot start job {job_id}." in job_log.read(job_id)


def test_a_failure_in_the_save_after_the_guard_ends_failed(job_id, monkeypatch):
    def save(job_id, row):
        raise ObjectStorageError("object storage is down")

    monkeypatch.setattr(job_persistence, "save", save)

    with pytest.raises(ObjectStorageError):
        Job(job_id).submit()

    assert DbManager.get_job_columns(job_id)["status"] == "FAILED"


def test_saving_a_stale_job_never_writes_its_status(job_id):
    """A page that loaded the job before a run ended must not put PENDING back."""
    stale = Job(job_id)
    set_row_columns(job_id, status="COMPLETED", submitted=True)

    stale.save()

    row = DbManager.get_job_columns(job_id)
    assert (row["status"], row["submitted"]) == ("COMPLETED", True)


def _model_with_email(job_id, email):
    """Return a valid model for job_id that differs from a new job's in its email."""
    model = Job(job_id).model
    model.email = email
    return model


def test_update_input_on_a_pending_job_writes_only_the_input(job_id):
    start_date = DbManager.get_job_columns(job_id)["start_date"]
    set_row_columns(job_id, start_date=date(2020, 1, 1))
    model = _model_with_email(job_id, USER_EMAIL)

    applied = Job(job_id).update_input(model)

    row = DbManager.get_job_columns(job_id)
    assert applied is True
    assert json.loads(row["input_data"])["email"] == USER_EMAIL
    assert (row["status"], row["submitted"]) == ("PENDING", False)
    assert row["start_date"] == date(2020, 1, 1) != start_date


@pytest.mark.parametrize("status", ["RUNNING", "COMPLETED"])
def test_update_input_on_a_job_that_is_not_pending_changes_nothing(job_id, status):
    """A stale tab's preview or check input must not rewrite a run's input."""
    stale = Job(job_id)
    set_row_columns(job_id, status=status, submitted=True)
    before = DbManager.get_job_columns(job_id)
    model = _model_with_email(job_id, USER_EMAIL)

    applied = stale.update_input(model)

    assert applied is False
    assert DbManager.get_job_columns(job_id) == before


def test_create_inserts_a_new_pending_job_and_refuses_an_existing_id(job_id):
    set_row_columns(job_id, status="COMPLETED", submitted=True)
    model = _model_with_email(job_id, USER_EMAIL)

    with pytest.raises(JobExists):
        Job.create(model)

    remove_job(job_id)
    created = Job.create(model)

    row = DbManager.get_job_columns(job_id)
    assert created.job_id == job_id
    assert (row["status"], row["submitted"]) == ("PENDING", False)
    assert row["start_date"] == date.today()
    assert json.loads(row["input_data"])["email"] == USER_EMAIL


def test_change_input_on_a_running_job_is_refused_and_deletes_nothing(job_id):
    job = Job(job_id)
    job.save()
    assert job_run.mark_queued(job_id)
    with open(os.path.join(job.working_dir, OUTPUT_FILE), "w", encoding="UTF-8") as f:
        f.write("a file the run uses\n")
    job.save()
    before = DbManager.get_job_columns(job_id)

    cleaned = Job(job_id).clean_work_dir()

    assert cleaned is False
    assert DbManager.get_job_columns(job_id) == before
    assert OUTPUT_FILE in get_remote_files(
        f"{OBJECT_STORAGE_REMOTE_NAME}:{OBJECT_STORAGE_BUCKET}/{job_id}"
    )


def test_change_input_on_a_failed_job_resets_it_to_pending(job_id):
    set_row_columns(job_id, status="FAILED", submitted=True)

    cleaned = Job(job_id).clean_work_dir()

    row = DbManager.get_job_columns(job_id)
    assert cleaned is True
    assert (row["status"], row["submitted"]) == ("PENDING", True)


def test_deleting_a_running_job_is_refused_and_says_so(job_id):
    assert job_run.mark_queued(job_id)

    deleted = Job(job_id).delete()

    assert deleted is False
    assert DbManager.get_job_columns(job_id)["status"] == "RUNNING"


def test_deleting_a_pending_job_reports_it(job_id):
    assert Job(job_id).delete() is True
