"""Dash form for the cosmopolitan job."""

import logging
from datetime import datetime
from typing import Annotated, ClassVar, Dict, List, Literal, Tuple

from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError
from soil_moisture_prediction.input_data import stream_dic
from soil_moisture_prediction.pydantic_models import InputParameters

# validate_job_id is re-exported: job.py and pages/new_job.py call it from here, and
# the rule (8-50 chars, ^\w+$) belongs to the framework's job-id contract now.
from cosmo_suite.pydantic_models import BaseJobConfig, validate_job_id  # noqa: F401

log = logging.getLogger(__name__)


def check_email(email: str) -> str:
    """Validate an email address using the email-validator library allow empty email."""
    if email == "":
        return email
    try:
        # Checks syntax and domain
        validate_email(email, check_deliverability=True)
        return email  # Return email if valid
    except EmailNotValidError as e:
        raise ValueError(f"Invalid email: {e}")


class ModelWebsite(InputParameters, BaseJobConfig):
    """Model for the website form.

    BaseJobConfig contributes the framework's job-id contract (and the generic
    upload_file_name field); InputParameters contributes the prediction
    parameters. The two field sets are disjoint.
    """

    email: Annotated[
        str,
        Field(
            "",
            description="Email address to be notified when job submission is complete.",
            title="Email",
            json_schema_extra={"type": "email"},
        ),
        AfterValidator(check_email),
    ]

    date_range: Annotated[
        Tuple[str, str],
        Field(
            ("2025-06-01", "2025-06-28"),
            description="Choose a date range for the CRNS measurements.",
            title="Date range",
            json_schema_extra={"type": "date-picker"},
        ),
    ]

    stream_choices: ClassVar[List[str]] = list(stream_dic.keys())
    pred_streams: Annotated[
        List[Literal[tuple(stream_choices)]],
        Field(
            ["elevation_bkg", "bdod_5-15cm"],
            description=("Select which the predictor source should to be used"),
            title="Predictor streams",
            json_schema_extra={"type": "dropdown-checklist"},
        ),
    ]

    predictor_upload: Annotated[
        Dict[str, Dict],
        Field(
            {},
            description=("Upload a files with the predictor data"),
            title="Predictor upload",
            json_schema_extra={"type": "multiple-file-upload"},
        ),
    ]

    crns_upload: Annotated[
        Dict[str, Dict],
        Field(
            {},
            description=("Upload a file with the crns data"),
            title="Crns upload",
            json_schema_extra={"type": "file-upload"},
        ),
    ]
    train_data: Annotated[
        bool,
        Field(
            True,
            description="Use measurements from the CRNS devices on trains for the prediction.",  # noqa
            title="Train data",
            json_schema_extra={"type": "checkbox"},
        ),
    ]
    station_data: Annotated[
        bool,
        Field(
            True,
            description="Use measurements from the stationary CRNS devices for the prediction.",  # noqa
            title="Station data",
            json_schema_extra={"type": "checkbox"},
        ),
    ]
    rover_data: Annotated[
        bool,
        Field(
            True,
            description="Use measurements from rover CRNS devices for the prediction.",
            title="Rover data",
            json_schema_extra={"type": "checkbox"},
        ),
    ]

    @model_validator(mode="after")
    def check_soil_moisture_data(self):
        """Ensure that eiterh crns data stations are selected or uploaded."""
        if (
            not any([self.train_data, self.station_data, self.rover_data])
            and len(self.crns_upload) == 0
        ):
            # Need to raise a custom error. Any validation error should be associated
            # with the field that caused it.
            raise PydanticCustomError(
                "value_error",
                "Either select a CRNS data source or upload CRNS data.",
                {
                    "loc_tuple": (
                        "crns_upload",
                        "train_data",
                        "station_data",
                        "rover_data",
                    )
                },
            )
        if (
            any(
                [
                    self.train_data,
                    self.station_data,
                    self.rover_data,
                ]
            )
            and len(self.crns_upload) > 0
        ):
            raise PydanticCustomError(
                "value_error",
                "Either select a CRNS data source or upload CRNS data, not both.",
                {
                    "loc_tuple": (
                        "crns_upload",
                        "train_data",
                        "station_data",
                        "rover_data",
                    )
                },
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

    # Security feature: No model can have an invalid job_id
    model_config = ConfigDict(validate_assignment=True)
