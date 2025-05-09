"""Error handling utilities for Dash apps."""

import json
import logging
import traceback

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, set_props
from sqlalchemy.exc import OperationalError
from werkzeug.exceptions import NotFound

from cosmopolitan_app.minio_manager import MinioError
from cosmopolitan_app.postgres_manager import JobNotFound


class InvalidJobID(Exception):
    """Raised by CosmopolitanJob if init with invalid job id."""

    def __init__(self, job_id):
        """Add job id as attribute and format error message."""
        self.job_id = job_id
        super().__init__(f"{job_id} is not a valid job_id.")


class SubmittedException(Exception):
    """Raised when calling a method that requires a job not to be submitted."""

    def __init__(self, job_id):
        """Add job id as attribute and format error message."""
        self.job_id = job_id
        super().__init__(f"The job {job_id} was not yet submitted.")


class NotSubmittedException(Exception):
    """Raised when calling a method that requires a job to be submitted."""

    def __init__(self, job_id):
        """Add job id as attribute and format error message."""
        self.job_id = job_id
        super().__init__(f"The job {job_id} was not yet submitted.")


class NotFinishedException(Exception):
    """Raised when calling a method that requires a job to be finished."""

    def __init__(self, job_id):
        """Add job id as attribute and format error message."""
        self.job_id = job_id
        super().__init__(f"The job {job_id} is not yet finished.")


error_responds_dict = {
    OperationalError: (
        "Database Connection Error",
        "Unfortunately, it is not possible to connect to the job database. Please try again later.",  # noqa
    ),
    MinioError: (
        "Database Connection Error",
        "Unfortunately, it is not possible to connect to the job database. Please try again later.",  # noqa
    ),
    NotFound: ("File Not Found", "The file could not be found."),
    Exception: ("Internal Error", "Ups this should not happen. An error occurred."),
    NotFinishedException: (
        "Job Not Finished",
        "The job '{{ job_id }}' is not yet finished. Visit submission to see the progress of the job.",  # noqa
    ),
    JobNotFound: (
        "Job Not Found",
        "Could not find the job '{{ job_id }}'. Visit input to make a new submission.",
    ),
    InvalidJobID: (
        "Job Not Found",
        "Could not find the job '{{ job_id }}'. Visit input to make a new submission.",
    ),
    NotSubmittedException: (
        "Job Not Submitted",
        "The job '{{ job_id }}' was not yet submitted. Visit submit to submit the job.",  # noqa
    ),
    SubmittedException: (
        "Job Already Submitted",
        "The job '{{ job_id }}' was already submitted. Visit job to see the status of the job. Or submit a new job at input.",  # noqa
    ),
}
error_modal = dbc.Modal(
    [
        dbc.ModalHeader(
            dbc.ModalTitle("Error"),
            id="error-title",
            close_button=False,
            className="bg-light",
        ),
        dbc.ModalBody(id="error-message", className="text-danger bg-light"),
        dbc.ModalFooter(
            dbc.Button(
                "Close",
                id="close-error",
                color="danger",
                className="ms-auto",
                n_clicks=0,
            ),
            className="bg-light",
        ),
    ],
    id="error-modal",
    is_open=False,
    backdrop="static",  # Prevent closing by clicking outside
)
error_toast = dbc.Toast(
    id="error-toast",
    header="",
    is_open=False,
    dismissable=False,
    icon="danger",
    # top: 66 positions the toast below the navbar
    style={"position": "fixed", "top": 82, "right": 10, "width": 200},
    body_style={"display": "none"},
)


def register_error_modal(app):
    """Register the error modal with the app."""

    @callback(
        Output("error-modal", "is_open", allow_duplicate=True),
        Input("close-error", "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_modal(n_clicks):
        """Toggle the error modal."""
        if n_clicks:
            return False
        return False


def handle_error(error):
    """Handle the error and return a formatted message."""
    logging.debug(f"Error: {error}")

    callback_context = dash.ctx
    email_subject = f"Error {str(error)}"
    email_body = f"""
    Traceback info: {traceback.format_exc()}\n\n
    Input info: {json.dumps(callback_context.triggered)}
    """
    logging.debug(f"Send email: {email_subject}\n{email_body}")
    error_title = error_responds_dict.get(type(error), error_responds_dict[Exception])[
        0
    ]
    error_message = error_responds_dict.get(
        type(error), error_responds_dict[Exception]
    )[1]
    set_props("error-toast", {"is_open": True, "header": error_title})
    set_props("error-modal", {"is_open": True})
    set_props("error-title", {"children": error_title})
    set_props("error-message", {"children": error_message})
