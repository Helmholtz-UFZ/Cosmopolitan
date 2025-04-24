"""Dash form for the cosmopolitan job."""

import logging
import os
import re
from datetime import datetime
from typing import Annotated, ClassVar, Dict, List, Literal, Tuple

from coolname import generate
from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError
from soil_moisture_prediction.input_data import stream_dic
from soil_moisture_prediction.pydantic_models import InputParameters

from cosmopolitan_app.config import JOB_WORK_DIR_TEMPLATE
from cosmopolitan_app.postgres_manager import PostgresManager


def test_model():
    """Test the model."""
    while True:
        job_id = "_".join(generate(3))
        if not PostgresManager.check_existence(job_id):
            break

    default_model = ModelWebsite()
    default_model.job_id = job_id
    default_values = default_model.model_dump()

    ModelWebsite(**default_values)


def validate_job_id(job_id):
    """Validate job id.

    The function further creates input dir for the job. If the job id was
    changed the function and moves all previously uploaded files into the
    new input dir.
    """
    logging.debug(f"Check job id {job_id}")

    job_id_regex = r"^\w+$"
    if not re.match(job_id_regex, job_id):
        raise ValueError("Username must contain only letters numbers or underscore")

    min_job_id_length = 8
    max_job_id_length = 50

    if len(job_id) < min_job_id_length or len(job_id) > max_job_id_length:
        raise ValueError(
            f"Job id must be between {min_job_id_length} and {max_job_id_length} characters"  # noqa
        )

    input_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=job_id)
    os.makedirs(input_dir, exist_ok=True)


def check_email(email: str) -> str:
    """Validate an email address using the email-validator library allow empty email."""
    if email == "":
        return email
    try:
        validate_email(email, check_deliverability=True)  # Checks syntax and domain
        return email  # Return email if valid
    except EmailNotValidError as e:
        raise ValueError(f"Invalid email: {e}")


class ModelWebsite(InputParameters):
    """Model for the website form."""

    email: Annotated[
        str,
        Field(
            "test@test.com",
            description="Email address to be notified when job submission is complete.",
            title="Email",
            type="email",
        ),
        AfterValidator(check_email),
    ]

    job_id: Annotated[
        str,
        Field(
            "poised_python_of_wonder",
            description='Identifier for your submission. Only letters, numbers and "_".',  # noqa
            title="Job ID",
            type="text",
        ),
        AfterValidator(validate_job_id),
    ]

    date_range: Annotated[
        Tuple[str, str],
        Field(
            ("2021-01-01", "2021-01-31"),
            description="Choose a date range for the CRNS measurements.",
            title="Date range",
            type="date-picker",
        ),
    ]

    stream_choices: ClassVar[List[str]] = list(stream_dic.keys())
    pred_streams: Annotated[
        List[Literal[tuple(stream_choices)]],
        Field(
            ["elevation_bkg", "bdod_5-15cm"],
            description=("Select which the predictor source should to be used"),
            title="Predictor streams",
            type="dropdown-checklist",
        ),
    ]

    predictor_upload: Annotated[
        Dict[str, Dict],
        Field(
            {},
            description=("Upload a files with the predictor data"),
            title="Predictor upload",
            type="multiple-file-upload",
        ),
    ]

    crns_upload: Annotated[
        Dict[str, Dict],
        Field(
            {},
            description=("Upload a file with the crns data"),
            title="Crns upload",
            type="file-upload",
        ),
    ]
    train_data: Annotated[
        bool,
        Field(
            True,
            description="Use measurements from the CRNS devices on trains for the prediction.",  # noqa
            title="Train data",
            type="checkbox",
        ),
    ]
    station_data: Annotated[
        bool,
        Field(
            True,
            description="Use measurements from the stationary CRNS devices for the prediction.",  # noqa
            title="Station data",
            type="checkbox",
        ),
    ]
    rover_data: Annotated[
        bool,
        Field(
            True,
            description="Use measurements from rover CRNS devices for the prediction.",
            title="Rover data",
            type="checkbox",
        ),
    ]

    @model_validator(mode="after")
    def check_soil_moisture_data(self):
        """Ensure that eiterh crns data stations are selected or uploaded."""
        if (
            not any([self.train_data, self.station_data, self.rover_data])
            and self.soil_moisture_data == ""
        ):
            # Need to raise a custom error. Any validation error should be associated
            # with the field that caused it.
            raise PydanticCustomError(
                "value_error",
                "Either select a CRNS data source or upload CRNS data.",
                {"loc_tuple": ("soil_moisture_data",)},
            )
        return self

    @field_validator("date_range")
    @classmethod
    def check_date_range(cls, date_range):
        """Ensure both dates are in YYYY-MM-DD format and the start date is before the end date."""  # noqa
        date_format = "%Y-%m-%d"

        try:
            start_date = datetime.strptime(date_range[0], date_format)
            end_date = datetime.strptime(date_range[1], date_format)
        except ValueError:
            raise ValueError(
                f"Both dates must be in the format YYYY-MM-DD. Got {date_range}"
            )

        if start_date > end_date:
            raise ValueError(
                f"Start date {date_range[0]} must be before end date {date_range[1]}."
            )

        return date_range
