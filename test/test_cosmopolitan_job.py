"""Test the cosmopolitan_job module."""

from test.mock_input import valid_form_data

from flask import Flask

from cosmopolitan_app.cosmopolitan_job import CosmopolitanJob, start_computation
from cosmopolitan_app.cosmopolitan_job_form import CosmopolitanJobForm
from cosmopolitan_app.db_manager import DataBaseManager


def test_computation():
    """Test consistency between wtform and test data from soil_moisture_prediction."""
    # Create a minimal Flask app for the context of CosmopolitanJobForm
    app = Flask(__name__)
    app.config["SERVER_NAME"] = "localhost"

    # The test job should be initialized with data base - see init.sql
    DataBaseManager.delete_job(valid_form_data["job_id"])
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
        assert job.status == "COMPLETED"


if __name__ == "__main__":
    test_computation()
