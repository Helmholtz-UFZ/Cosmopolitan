"""Test cosmopolitan job form."""

from test.mock_input import (
    post_invalid_form_data,
    pre_invalid_form_data,
    valid_form_data,
)

from flask import Flask
from soil_moisture_prediction.pydantic_models import InputParamaters

from cosmopolitan_app.cosmopolitan_job import CosmopolitanJob
from cosmopolitan_app.cosmopolitan_job_form import CosmopolitanJobForm
from cosmopolitan_app.db_manager import JobNotFound


def test_consistency_between_test_form_data():
    """Test consistency between the test form data."""
    assert (
        valid_form_data.keys() == pre_invalid_form_data.keys()
    ), "Test form data inconsistent."
    assert (
        valid_form_data.keys() == post_invalid_form_data.keys()
    ), "Test form data inconsistent."


def test_consistency_between_form_and_package():
    """Test consistency between wtform and test data from soil_moisture_prediction."""
    # Create a minimal Flask app for the context of CosmopolitanJobForm
    app = Flask(__name__)
    with app.app_context():
        cosmopolitan_job_form = CosmopolitanJobForm(formdata=valid_form_data)
        cosmopolitan_job_form.validate()
        for field in cosmopolitan_job_form._fields:
            assert (
                field in valid_form_data.keys()
            ), f"Field {field} from webserver is not in test form."
        for field in valid_form_data:
            assert (
                field in cosmopolitan_job_form._fields.keys()
            ), f"Field {field} from test form is not found in form from webserver."
        for field in cosmopolitan_job_form._fields:
            assert (
                getattr(cosmopolitan_job_form, field).errors == []
            ), "Parameter do not create validt form data."


def test_post_invalid_form_data():
    """Test a invalid form which is invalid between fields."""
    app = Flask(__name__)
    with app.app_context():
        cosmopolitan_job_form = CosmopolitanJobForm(formdata=post_invalid_form_data)
        cosmopolitan_job_form.validate()
        assert cosmopolitan_job_form._fields["area_y1"].errors == [
            "Y1 cannot be higher or equal than Y2."
        ]
        assert cosmopolitan_job_form._fields["pred_files"].errors == [
            "Chose one or more predictor files."
        ]


def test_pre_invalid_form_data():
    """Test a simple invalid form."""
    app = Flask(__name__)
    with app.app_context():
        cosmopolitan_job_form = CosmopolitanJobForm(formdata=pre_invalid_form_data)
        cosmopolitan_job_form.validate()
        assert cosmopolitan_job_form._fields["email"].errors == [
            "Invalid email address."
        ]
        assert "File is not a UTF-8 file" in str(
            cosmopolitan_job_form._fields["pred_files"].errors[0]
        )
        assert cosmopolitan_job_form._fields["monte_carlo_iterations"].errors == [
            "Number must be between 1 and 100."
        ]


def test_changes_in_parameters():
    """Test if the parameters have changed."""
    app = Flask(__name__)
    with app.app_context():
        try:
            job = CosmopolitanJob(job_id=valid_form_data["job_id"])
            job.delete()
        except JobNotFound:
            pass
        cosmopolitan_job_form = CosmopolitanJobForm(formdata=valid_form_data, new=False)

    assert cosmopolitan_job_form.validate() is True, "Form is not valid."

    parameters_form = cosmopolitan_job_form._input_parameters(write=False)
    input_parameters = InputParamaters(**parameters_form)
    assert (
        type(input_parameters) is InputParamaters
    ), "Input parameters are not correct."

    # Save the job again as currently test_if_test_job_exists looks for the job in the
    # database and will fail if the job does not exist. The test job should always exist
    # as it used to test the webserver in production.
    job = CosmopolitanJob(form=cosmopolitan_job_form)
    job.save()
