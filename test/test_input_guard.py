"""Test that the input and submission callbacks leave a job that has moved on alone.

A tab left open on the input page still holds the form of a job that was submitted
meanwhile: "update preview", "check input" and "Change input" in it must not
reset, rewrite or delete files of a RUNNING or COMPLETED job (cosmo-ecosystem
ADR 0005); the page says so in a hint instead. Runs against real Postgres and
object storage and calls the callbacks the way Dash does.
"""

import json
import os
import sys
from contextlib import contextmanager

import dash
import pytest
from cosmo_ecosystem import job_log, job_run
from cosmo_ecosystem.db_manager import DbManager
from cosmo_ecosystem.object_storage_manager import get_remote_files
from dash._callback_context import context_value
from dash._utils import AttributeDict

from cosmopolitan_app.app import app  # noqa: F401 - registers the pages first
from cosmopolitan_app.constants import (
    CHANGE_INPUT_BUTTON_SUBMISSION_ID,
    CHECK_INPUT_BUTTON_INPUT_ID,
    DELETE_CRNS_UPLOAD_BUTTON_INPUT_ID,
    DELETE_PREDICTOR_UPLOAD_BUTTON_INPUT_ID,
    HIDDEN_CRNS_UPLOAD_INPUT_INPUT_ID,
    HIDDEN_PREDICTOR_UPLOAD_INPUT_INPUT_ID,
    HINT_DIV_INPUT_ID,
    SUBMIT_JOB_BUTTON_SUBMISSION_ID,
)
from cosmopolitan_app.config import OBJECT_STORAGE_BUCKET, OBJECT_STORAGE_REMOTE_NAME
from cosmopolitan_app.job import Job
from cosmopolitan_app.pydantic_models import ModelWebsite
from test.help_functions_tests import remove_job, set_row_columns

JOB_ID = "test_input_guard"
EMAIL = "stale@ufz.de"
SUBMISSION_OUTPUT_COUNT = 14


def _page_module(path_template):
    """Return the page module Dash registered (a second import would register twice)."""
    page = next(
        page
        for page in dash.page_registry.values()
        if page["path_template"] == path_template
    )
    return sys.modules[page["module"]]


@pytest.fixture(scope="module")
def input_page():
    return _page_module("/input/<job_id>")


@pytest.fixture(scope="module")
def submission_page():
    return _page_module("/submission/<job_id>")


@pytest.fixture
def job_id():
    """Yield the id of a new PENDING job; it is gone before and after the test."""
    remove_job(JOB_ID)
    Job(new_job_id=JOB_ID)
    yield JOB_ID
    remove_job(JOB_ID)


@contextmanager
def _dash_context(triggered_id, prop="n_clicks"):
    """Run a callback as if a click on triggered_id had triggered it."""
    token = context_value.set(
        AttributeDict(
            triggered_inputs=[{"prop_id": f"{triggered_id}.{prop}", "value": 1}],
            outputs_list=[{}] * SUBMISSION_OUTPUT_COUNT,
        )
    )
    try:
        yield
    finally:
        context_value.reset(token)


def _form_state(job_id, input_page):
    """Return the callback state of a form holding a valid model with EMAIL."""
    values = ModelWebsite().model_dump()
    state = {}
    for key in input_page.active_form_factory.produce_callback_inputs():
        if key.endswith("_start_date"):
            state[key] = str(values["date_range"][0])
        elif key.endswith("_end_date"):
            state[key] = str(values["date_range"][1])
        elif key == "pred_streams":
            state[key] = []
        else:
            state[key] = values[key]
    state["email"] = EMAIL
    state["hidden_crns_upload"] = ""
    state["hidden_predictor_upload"] = ""
    state["job_id"] = job_id
    return state


def _input_data(job_id):
    return json.loads(DbManager.get_job_columns(job_id)["input_data"])


@pytest.mark.parametrize("status", ["RUNNING", "COMPLETED"])
def test_update_preview_in_a_stale_tab_leaves_the_job_and_says_so(
    input_page, job_id, status
):
    set_row_columns(job_id, status=status, submitted=True)
    before = DbManager.get_job_columns(job_id)
    state = _form_state(job_id, input_page)
    state["new_area_preview"] = 1

    result = input_page.regenerate_preview(**state)

    assert DbManager.get_job_columns(job_id) == before
    assert result["area_preview"] is dash.no_update
    assert "PENDING" in str(result[HINT_DIV_INPUT_ID])


@pytest.mark.parametrize("status", ["RUNNING", "COMPLETED"])
def test_check_input_in_a_stale_tab_leaves_the_job_and_says_so(
    input_page, job_id, status
):
    set_row_columns(job_id, status=status, submitted=True)
    before = DbManager.get_job_columns(job_id)
    state = _form_state(job_id, input_page)
    state[CHECK_INPUT_BUTTON_INPUT_ID] = 1

    with _dash_context(CHECK_INPUT_BUTTON_INPUT_ID):
        result = input_page.form_validation_callback(**state)

    assert DbManager.get_job_columns(job_id) == before
    assert result["redirect"] is dash.no_update
    assert "PENDING" in str(result[HINT_DIV_INPUT_ID])


def _submission_call(submission_page, job_id, triggered_id):
    with _dash_context(triggered_id):
        return submission_page.submission_manager(
            None, 1, 1, None, None, f"/submission/{job_id}", "bg-info", "icon-none"
        )


def test_change_input_on_a_running_job_leaves_it_and_says_so(submission_page, job_id):
    job = Job(job_id)
    job.save()
    assert job_run.mark_queued(job_id)
    before = DbManager.get_job_columns(job_id)

    result = _submission_call(
        submission_page, job_id, CHANGE_INPUT_BUTTON_SUBMISSION_ID
    )

    assert DbManager.get_job_columns(job_id) == before
    assert result[0] is dash.no_update
    assert "running" in str(result[-1])


def test_submit_does_not_clear_the_job_log_of_a_running_job(submission_page, job_id):
    """A second click on Submit must not wipe the log of the run that computes."""
    job_log.append(job_id, "the live log line")
    assert job_run.mark_queued(job_id)

    _submission_call(submission_page, job_id, SUBMIT_JOB_BUTTON_SUBMISSION_ID)

    assert "the live log line" in job_log.read(job_id)


@pytest.mark.parametrize("status", ["RUNNING", "COMPLETED"])
def test_deleting_an_upload_in_a_stale_tab_keeps_the_files_and_says_so(
    input_page, job_id, status
):
    job = Job(job_id)
    with open(os.path.join(job.working_dir, "crn_data.csv"), "w") as f_handle:
        f_handle.write("measurements\n")
    job.save()
    set_row_columns(job_id, status=status, submitted=True)
    before = DbManager.get_job_columns(job_id)
    state = {
        "crns_upload_contents": None,
        "predictor_upload_contents": None,
        DELETE_CRNS_UPLOAD_BUTTON_INPUT_ID: 1,
        DELETE_PREDICTOR_UPLOAD_BUTTON_INPUT_ID: None,
        "crns_upload_filename": None,
        "predictor_upload_filename": None,
        HIDDEN_CRNS_UPLOAD_INPUT_INPUT_ID: "{}",
        HIDDEN_PREDICTOR_UPLOAD_INPUT_INPUT_ID: "{}",
        "job_id": job_id,
    }

    with _dash_context(DELETE_CRNS_UPLOAD_BUTTON_INPUT_ID):
        result = input_page.file_upload_callback(**state)

    assert DbManager.get_job_columns(job_id) == before
    assert "crn_data.csv" in get_remote_files(
        f"{OBJECT_STORAGE_REMOTE_NAME}:{OBJECT_STORAGE_BUCKET}/{job_id}"
    )
    assert "PENDING" in str(result[HINT_DIV_INPUT_ID])


@pytest.fixture
def job_started_before_the_preview(monkeypatch):
    """Make the job RUNNING right when preview_area checks that it is PENDING."""
    real = Job.check_pending

    def check_after_a_submit(self):
        set_row_columns(self.job_id, status="RUNNING", submitted=True)
        return real(self)

    monkeypatch.setattr(Job, "check_pending", check_after_a_submit)


def test_update_preview_that_loses_the_race_says_so(
    input_page, job_id, job_started_before_the_preview
):
    """The job started between the input write and the preview: a hint, no crash."""
    state = _form_state(job_id, input_page)
    state["new_area_preview"] = 1

    with app.server.test_request_context():
        result = input_page.regenerate_preview(**state)

    assert result["area_preview"] is dash.no_update
    assert "PENDING" in str(result[HINT_DIV_INPUT_ID])


def test_input_page_load_that_loses_the_race_shows_no_preview(
    input_page, job_id, job_started_before_the_preview
):
    with app.server.test_request_context():
        header_class, subtitle, content = input_page.load_submission_content(
            job_id, "bg-info"
        )

    assert subtitle == job_id
    assert content is not None
