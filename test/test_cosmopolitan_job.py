"""Test the cosmopolitan_job module."""

from test.mock_input import valid_form_data

import pytest
from flask import Flask

from cosmopolitan_app.cosmopolitan_job import CosmopolitanJob, start_computation
from cosmopolitan_app.cosmopolitan_job_form import CosmopolitanJobForm
from cosmopolitan_app.db_manager import DataBaseManager, JobNotFound


@pytest.mark.order(-2)
def test_computation():
    """Test the complete run of the computation."""
    # Create a minimal Flask app for the context of CosmopolitanJobForm
    app = Flask(__name__)
    app.config["SERVER_NAME"] = "localhost"

    # The test job should be initialized with data base - see init.sql
    try:
        DataBaseManager.delete_job(valid_form_data["job_id"])
    except JobNotFound:
        pass
    with app.app_context():
        import cosmopolitan_app.routes  # noqa

        cosmopolitan_job_form = CosmopolitanJobForm(new=False, formdata=valid_form_data)
        cosmopolitan_job_form.validate()
        job = CosmopolitanJob(form=cosmopolitan_job_form)
        job.save()
        assert DataBaseManager.set_submitted(job.job_id) is True
        job.submitted = True
        job.status = "RUNNING"
        start_computation(job)
        del job
        job = CosmopolitanJob(job_id=cosmopolitan_job_form.job_id.data)
        assert job.submitted is True
        assert job.status == "COMPLETED", f"Job failed with logs: {job.logs}"


if __name__ == "__main__":
    test_computation()
