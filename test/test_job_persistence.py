"""Test that COSMOPOLITAN's Job persists through the framework's job_persistence.

Runs against the real Postgres and object storage. rclone calls are counted
around ``run_rclone_with_retry``, never timed.
"""

import os

import pytest
from cosmo_ecosystem import object_storage_manager
from cosmo_ecosystem.object_storage_manager import get_remote_files

from cosmopolitan_app.config import (
    JOB_WORK_DIR_TEMPLATE,
    OBJECT_STORAGE_BUCKET,
    OBJECT_STORAGE_REMOTE_NAME,
)
from cosmopolitan_app.job import Job
from cosmopolitan_app.postgres_manager import PostgresManager

FILE_NAME = "marker.txt"
STALE = "stale\n"
FRESH = "fresh\n"


@pytest.fixture
def rclone_calls(monkeypatch):
    """Count the rclone commands object_storage_manager runs."""
    calls = []
    real = object_storage_manager.run_rclone_with_retry

    def counting(params, *args, **kwargs):
        calls.append(params)
        return real(params, *args, **kwargs)

    monkeypatch.setattr(object_storage_manager, "run_rclone_with_retry", counting)
    return calls


@pytest.fixture
def job_id():
    """Yield an id whose job, files and row are gone before and after the test."""
    new_id = "test_job_persistence"
    _delete_everywhere(new_id)
    yield new_id
    _delete_everywhere(new_id)


def _delete_everywhere(job_id):
    """Delete the job if it exists; Job.delete leaves nothing behind."""
    if PostgresManager.check_existence(job_id):
        Job(job_id).delete()


def _write(job_id, content):
    """Write the marker file into job_id's local work dir."""
    work_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=job_id)
    os.makedirs(work_dir, exist_ok=True)
    with open(os.path.join(work_dir, FILE_NAME), "w", encoding="UTF-8") as f_handle:
        f_handle.write(content)


def _read(job_id):
    """Read the marker file from job_id's local work dir."""
    path = os.path.join(JOB_WORK_DIR_TEMPLATE.format(job_id=job_id), FILE_NAME)
    with open(path, encoding="UTF-8") as f_handle:
        return f_handle.read()


def _remote_files(job_id):
    """List the objects stored below job_id's remote prefix."""
    return get_remote_files(
        f"{OBJECT_STORAGE_REMOTE_NAME}:{OBJECT_STORAGE_BUCKET}/{job_id}"
    )


def test_the_status_poll_makes_no_rclone_call(job_id, rclone_calls):
    """Loading a Job, refreshing its logs and reading its ttl stays off rclone.

    This is what the 2 s submission poll does while a job runs.
    """
    Job(new_job_id=job_id)
    rclone_calls.clear()

    job = Job(job_id)
    job.reload_logs()
    job.time_to_live()
    job.save_attributes(["status"])

    assert rclone_calls == []


def test_a_reused_job_id_yields_the_new_jobs_files(job_id):
    """A leftover local file of a deleted job does not shadow the new job's file.

    Job ids are reused after a delete, and a worker keeps its work dir across
    jobs, so its copy of the old file survives the delete.
    """
    old_job = Job(new_job_id=job_id)
    _write(job_id, STALE)
    old_job.save()
    old_job.delete()

    new_job = Job(new_job_id=job_id)
    _write(job_id, FRESH)
    new_job.save()
    _write(job_id, STALE)

    assert _read_through(Job(job_id)) == FRESH


def _read_through(job):
    """Read the marker file from the job's working dir."""
    with open(os.path.join(job.working_dir, FILE_NAME), encoding="UTF-8") as f_handle:
        return f_handle.read()


def test_deleting_an_item_removes_it_locally_and_remotely(job_id):
    """delete_item leaves the file neither on disk nor in storage."""
    job = Job(new_job_id=job_id)
    _write(job_id, FRESH)
    job.save()
    assert FILE_NAME in _remote_files(job_id)

    job.delete_item(FILE_NAME)

    assert FILE_NAME not in _remote_files(job_id)
    assert not os.path.exists(os.path.join(job.working_dir, FILE_NAME))


def test_saving_a_job_that_never_touched_its_files_keeps_the_remote_files(job_id):
    """A job loaded for a status change and saved does not delete stored files."""
    job = Job(new_job_id=job_id)
    _write(job_id, FRESH)
    job.save()
    os.remove(os.path.join(JOB_WORK_DIR_TEMPLATE.format(job_id=job_id), FILE_NAME))

    poll_job = Job(job_id)
    poll_job.status = "RUNNING"
    poll_job.save()

    assert FILE_NAME in _remote_files(job_id)
    assert PostgresManager.get_job_columns(job_id)["status"] == "RUNNING"
