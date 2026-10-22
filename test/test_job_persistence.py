"""Test that COSMOPOLITAN's Job persists through the framework's job_persistence.

Runs against the real Postgres and object storage. rclone calls are counted
around ``run_rclone_with_retry``, never timed.
"""

import json
import os
import sys

import dash
import pytest
from cosmo_ecosystem import job_persistence, object_storage_manager
from cosmo_ecosystem.db_manager import DbManager
from cosmo_ecosystem.object_storage_manager import get_remote_files

from soil_moisture_prediction.plot_functions import CONSTANT_TIME_STEP, SCALE_FILE_NAME

from cosmopolitan_app.background_job_manager import background_job_manager
from cosmopolitan_app.config import (
    JOB_WORK_DIR_TEMPLATE,
    OBJECT_STORAGE_BUCKET,
    OBJECT_STORAGE_REMOTE_NAME,
)
from cosmopolitan_app.job import Job
from cosmopolitan_app.app import app  # noqa: F401 - registers the pages first
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


@pytest.fixture(scope="module")
def results():
    """Return the results page module Dash registered.

    Importing it by its package path would load a second copy that registers
    every callback twice, so the module is looked up by the name Dash used.
    """
    page = next(
        page
        for page in dash.page_registry.values()
        if page["path_template"] == "/results/<job_id>"
    )
    return sys.modules[page["module"]]


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

    job_persistence.work_dir(job_id)
    assert _read(job_id) == FRESH


def test_deleting_an_item_removes_it_locally_and_remotely(job_id):
    """delete_item leaves the file neither on disk nor in storage."""
    job = Job(new_job_id=job_id)
    _write(job_id, FRESH)
    job.save()
    assert FILE_NAME in _remote_files(job_id)

    job.delete_item(FILE_NAME)

    assert FILE_NAME not in _remote_files(job_id)
    assert not os.path.exists(
        os.path.join(JOB_WORK_DIR_TEMPLATE.format(job_id=job_id), FILE_NAME)
    )


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
    assert DbManager.get_job_columns(job_id)["status"] == "RUNNING"


DATE = "2025-01-01"
CSV_TIME_STEP = f"time_step,feature,a\n{CONSTANT_TIME_STEP},a,1.0\n"


@pytest.fixture
def completed_job(job_id):
    """Yield the id of a saved COMPLETED job holding the files the results page reads."""
    job = Job(new_job_id=job_id)
    work_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=job_id)
    files = {
        f"measurements_{DATE}.geojson": "{}",
        SCALE_FILE_NAME: json.dumps(
            {
                f"prediction_distance_{DATE}": [-1, 1, "m"],
                f"dispersion_coefficient_{DATE}": [0, 1, "m"],
                "a": [0, 1, "m"],
            }
        ),
        "correlation_matrix.csv": CSV_TIME_STEP,
        "predictor_importance.csv": (
            "time_step,predictor,importance,5th_percentile,95th_percentile\n"
            f"{DATE},a,0.5,0.4,0.6\n"
        ),
    }
    for name, content in files.items():
        with open(os.path.join(work_dir, name), "w", encoding="UTF-8") as f_handle:
            f_handle.write(content)
    job.status = "COMPLETED"
    job.save()
    return job_id


def test_a_results_page_load_pulls_the_files_once(results, completed_job, rclone_calls):
    """The page load costs exactly one work_dir pull, however many helpers read."""
    job_persistence.work_dir(completed_job)
    calls_of_one_pull = len(rclone_calls)
    rclone_calls.clear()

    results.load_results_content(completed_job, "")

    assert len(rclone_calls) == calls_of_one_pull


@pytest.mark.parametrize(
    "map_type", ["prediction", "prediction_distance", "dispersion_coefficient", "a"]
)
@pytest.mark.parametrize("opacity", [0.2, 0.9])
def test_changing_the_map_runs_no_rclone(
    results, completed_job, rclone_calls, map_type, opacity
):
    """A slider, opacity or map-type change builds paths only and stays off rclone."""
    scale_path = os.path.join(
        JOB_WORK_DIR_TEMPLATE.format(job_id=completed_job), SCALE_FILE_NAME
    )
    with open(scale_path, encoding="UTF-8") as f_handle:
        color_bar_info = json.load(f_handle)
    rclone_calls.clear()

    results.update_map(
        1, map_type, True, opacity, completed_job, [], color_bar_info, [DATE]
    )

    assert rclone_calls == []


def test_submit_syncs_nothing_after_the_enqueue(job_id, rclone_calls, monkeypatch):
    """After the enqueue only columns are written: no rclone, files stay as they are.

    A worker on the shared disk may already be writing files by then, so a pull or
    an upload after the enqueue could overwrite or delete its output.
    """
    job = Job(new_job_id=job_id)
    calls_at_enqueue = []

    def enqueue(submitted_job):
        calls_at_enqueue.append(len(rclone_calls))
        _write(job_id, FRESH)  # the worker's first output
        return "task-id", False

    monkeypatch.setattr(background_job_manager, "submit_computation_job", enqueue)

    job.submit()

    assert len(rclone_calls) == calls_at_enqueue[0]
    assert _read(job_id) == FRESH
    assert DbManager.get_job_columns(job_id)["status"] == "RUNNING"
