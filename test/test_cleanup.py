"""Test the app's nightly cleanup against the real Postgres and object storage."""

import datetime
import os
import shutil

from cosmo_ecosystem.constants import DAYS_DELETE_SUBMITTED
from cosmo_ecosystem.object_storage_manager import (
    delete_directory_from_storage,
    get_remote_files,
    save_files,
)

from cosmopolitan_app.background_job_manager import NAME_CLEANUP_TASK
from cosmopolitan_app.celery_app import celery
from cosmopolitan_app.config import (
    JOB_WORK_DIR_TEMPLATE,
    OBJECT_STORAGE_BUCKET,
    OBJECT_STORAGE_REMOTE_NAME,
)
from cosmopolitan_app.postgres_manager import PostgresManager

FILE_NAME = "result.csv"


def _work_dir(job_id):
    """Return the local work directory of job_id."""
    return JOB_WORK_DIR_TEMPLATE.format(job_id=job_id)


def _remote_files(job_id):
    """List the objects stored below job_id's remote prefix."""
    return get_remote_files(
        f"{OBJECT_STORAGE_REMOTE_NAME}:{OBJECT_STORAGE_BUCKET}/{job_id}"
    )


def _seed(job_id, *, days_old=0):
    """Insert a submitted row for job_id and upload one file to its prefix.

    The local work dir is left in place; a test that wants a pod without it
    removes it.
    """
    PostgresManager.add_entry(
        {
            "job_id": job_id,
            "start_date": datetime.date.today() - datetime.timedelta(days=days_old),
            "input_data": {},
            "submitted": True,
            "notified_end": True,
            "logs": "",
            "status": "COMPLETED",
            "version": "0.0.0",
        }
    )
    os.makedirs(_work_dir(job_id), exist_ok=True)
    with open(
        os.path.join(_work_dir(job_id), FILE_NAME), "w", encoding="UTF-8"
    ) as f_handle:
        f_handle.write("a,b\n1,2\n")
    save_files(job_id)


def _cleanup(job_id):
    """Remove whatever a test, or an earlier failed run, left behind for job_id."""
    delete_directory_from_storage(job_id)
    shutil.rmtree(_work_dir(job_id), ignore_errors=True)
    if PostgresManager.check_existence(job_id):
        PostgresManager.delete_job(job_id)


def test_cleanup_removes_an_expired_job_that_only_exists_in_remote_storage():
    """An expired job another pod handled loses its remote prefix and its row.

    The regression for the storage leak: the cleanup used to delete remote
    objects only for job dirs on the local disk of the pod running it, so on
    Kubernetes an expired job this pod never touched kept its objects forever.
    """
    job_id = "test_cleanup_remote_only"
    try:
        _cleanup(job_id)
        _seed(job_id, days_old=DAYS_DELETE_SUBMITTED)
        # This pod never handled the job: its files exist only in remote storage.
        shutil.rmtree(_work_dir(job_id))
        assert _remote_files(job_id) == {FILE_NAME}

        # Calling the registered task runs its body in this process, the way
        # the worker runs it for the beat entry.
        celery.tasks[NAME_CLEANUP_TASK]()

        assert _remote_files(job_id) == set()
        assert not PostgresManager.check_existence(job_id)
    finally:
        _cleanup(job_id)
