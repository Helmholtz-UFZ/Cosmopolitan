"""Test cosmopolitan job form."""

from test.mock_input import (
    post_invalid_form_data,
    pre_invalid_form_data,
    valid_form_data,
)

import pytest
from pydantic import ValidationError
from soil_moisture_prediction.pydantic_models import InputParameters
from soil_moisture_prediction.smp_cli import pprint_pydantic_validation_error

from cosmopolitan_app.cosmopolitan_job import CosmopolitanJob
from cosmopolitan_app.cosmopolitan_job_form import CosmopolitanJobForm
from cosmopolitan_app.db_manager import JobNotFound


def test_consistency_between_test_form_data():
    """Test consistency between the test form data."""
    for key in valid_form_data:
        assert (
            key in pre_invalid_form_data
        ), f"Key {key} not found in pre_invalid_form_data."
        assert (
            key in post_invalid_form_data
        ), f"Key {key} not found in post_invalid_form_data."

    for key in pre_invalid_form_data:
        assert key in valid_form_data, f"Key {key} not found in valid_form_data."
        assert (
            key in post_invalid_form_data
        ), f"Key {key} not found in post_invalid_form_data."

    for key in post_invalid_form_data:
        assert key in valid_form_data, f"Key {key} not found in valid_form_data."
        assert (
            key in pre_invalid_form_data
        ), f"Key {key} not found in pre_invalid_form_data."


def test_consistency_between_form_and_package(app):
    """Test consistency between wtform and test data from soil_moisture_prediction."""
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


def test_post_invalid_form_data(app):
    """Test a invalid form which is invalid between fields."""
    with app.app_context():
        cosmopolitan_job_form = CosmopolitanJobForm(formdata=post_invalid_form_data)
        cosmopolitan_job_form.validate()
        assert cosmopolitan_job_form._fields["area_y1"].errors == [
            "Y1 cannot be higher or equal than Y2."
        ]
        assert cosmopolitan_job_form._fields["pred_files"].errors == [
            "Chose one or more predictor files."
        ]


def test_pre_invalid_form_data(app):
    """Test a simple invalid form."""
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


def test_changes_in_parameters(app):
    """Test if the parameters have changed."""
    with app.app_context():
        try:
            job = CosmopolitanJob(job_id=valid_form_data["job_id"])
            job.delete()
        except JobNotFound:
            pass
        cosmopolitan_job_form = CosmopolitanJobForm(formdata=valid_form_data, new=False)

    assert cosmopolitan_job_form.validate() is True, "Form is not valid."

    parameters_form = cosmopolitan_job_form._input_parameters(write=False)
    try:
        input_parameters = InputParameters(**parameters_form)
    except ValidationError as validation_error:
        pytest.fail(
            "Input parameter are not cohesive with pydantic mocdel:\n"
            + pprint_pydantic_validation_error(validation_error)
        )
    assert (
        type(input_parameters) is InputParameters
    ), "Input parameters are not correct."
