"""Test the cosmopolitan_job module."""

import logging
from test.mock_input import valid_form_data
from time import sleep

import pytest

from cosmopolitan_app.cosmopolitan_job import CosmopolitanJob, start_computation
from cosmopolitan_app.cosmopolitan_job_form import CosmopolitanJobForm
from cosmopolitan_app.postgres_manager import JobNotFound, PostgresManager


@pytest.mark.order(-2)
def test_computation_valid(app):
    """Test the complete run of the computation of an valid input."""
    # Set up logger inside the test function so pytest only show logs of failed tests
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    try:
        PostgresManager.delete_job(valid_form_data["job_id"])
    except JobNotFound:
        pass

    with app.app_context():
        import cosmopolitan_app.routes  # noqa

        cosmopolitan_job_form = CosmopolitanJobForm(new=False, formdata=valid_form_data)
        assert cosmopolitan_job_form.validate(), "Invalid form"
        job = CosmopolitanJob(form=cosmopolitan_job_form)
        job.save()
        assert PostgresManager.set_submitted(job.job_id) is True
        job.submitted = True
        job.status = "RUNNING"
        start_computation(job)
        del job
        for _ in range(10):
            sleep(1)
            job = CosmopolitanJob(job_id=cosmopolitan_job_form.job_id.data)
            logging.debug(f"Job status: {job.status}")
            if job.status in ["COMPLETED", "FAILED"]:
                break
        else:
            assert False, "Job did not finish in time."

        job = CosmopolitanJob(job_id=cosmopolitan_job_form.job_id.data)
        assert job.submitted is True
        if job.status == "FAILED":
            logging.info("Logs:")
            logging.info(job.logs)
        assert job.status == "COMPLETED", "Job failed."

        # Test if the job can be loaded from the database
        job.delete(delete_db=False)
        del job
        job = CosmopolitanJob(job_id=cosmopolitan_job_form.job_id.data)
        assert job.status == "COMPLETED", "Job did not relaod."


@pytest.mark.order(-3)
def test_computation_invalid(app):
    """Test the complete run of the computation of an invalid form.

    This test should fail due to the fact that the argument comput slope is given but
    the elevation data from `predictor_1.csv` is missing.
    """
    # Set up logger inside the test function so pytest only show logs of failed tests
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    form_data = valid_form_data.copy()
    form_data["job_id"] = "test_computation_invalid"
    # Delete elevation data, MultiDict are weird
    form_data.setlist(
        "pred_files",
        [f for f in form_data.getlist("pred_files") if f.filename != "predictor_1.csv"],
    )

    try:
        PostgresManager.delete_job(form_data["job_id"])
    except JobNotFound:
        pass

    with app.app_context():
        cosmopolitan_job_form = CosmopolitanJobForm(new=False, formdata=form_data)
        cosmopolitan_job_form.validate()
        job = CosmopolitanJob(form=cosmopolitan_job_form)
        job.save()
        assert PostgresManager.set_submitted(job.job_id) is True
        job.submitted = True
        job.status = "RUNNING"
        start_computation(job)
        del job
        for _ in range(10):
            sleep(1)
            job = CosmopolitanJob(job_id=cosmopolitan_job_form.job_id.data)
            logging.debug(f"Job status: {job.status}")
            if job.status in ["COMPLETED", "FAILED"]:
                break
        else:
            assert False, "Job did not finish in time."

        assert job.submitted is True
        assert job.status == "FAILED", f"Job did not fail: {job.logs}"
