"""Error handling utilities for Dash apps."""

import functools
import logging
import traceback
from copy import deepcopy

import dash_bootstrap_components as dbc
from dash import Input, Output, callback, no_update
from dash.exceptions import PreventUpdate
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

    @app.callback(
        Output("error-modal", "is_open", allow_duplicate=True),
        Input("close-error", "n_clicks"),
    )
    def toggle_modal(n_clicks):
        """Toggle the error modal."""
        if n_clicks:
            return False
        return False


def create_callback_with_error_handling(*args, **kwargs):
    """Create a callback with error handling."""

    def set_args(args, kwargs):
        error_outputs_dict = {
            "is_open-toast": Output("error-toast", "is_open", allow_duplicate=True),
            "header-toast": Output("error-toast", "header", allow_duplicate=True),
            "is_open-modal": Output("error-modal", "is_open", allow_duplicate=True),
            "title-modal": Output("error-title", "children", allow_duplicate=True),
            "message-modal": Output("error-message", "children", allow_duplicate=True),
        }
        if len(args) != 0:
            if not isinstance(args, tuple):
                raise NotImplementedError("Only Tuple is supported")
            num_original_outputs = sum(1 for item in args if isinstance(item, Output))
            error_outputs = tuple((output for output in error_outputs_dict.values()))
            new_kwargs = deepcopy(kwargs)
            new_args = error_outputs + args
        else:
            new_args = ()
            new_kwargs = deepcopy(kwargs)
            num_original_outputs = len(kwargs["output"])
            if isinstance(new_kwargs["output"], list):
                new_kwargs["output"] = list(error_outputs_dict.values())
            else:
                new_kwargs["output"].update(error_outputs_dict)

        new_kwargs["prevent_initial_call"] = True

        return new_args, num_original_outputs, new_kwargs

    def decorator(func):
        logging.debug(f"Decorator func: {func.__name__}")
        new_args, num_original_outputs, new_kwargs = set_args(args, kwargs)

        @callback(*new_args, **new_kwargs)
        @functools.wraps(func)
        def wrapper(*func_args, **func_kwargs):
            try:
                result = func(*func_args, **func_kwargs)

                if not isinstance(result, tuple) and len(args) != 0:
                    result = (result,)
                if len(args) == 0 and result is None:
                    result = {}
                if len(args) != 0 and result is None:
                    result = ()
                if len(args) == 0 and not isinstance(result, dict):
                    logging.warning(f"Args: {args}")
                    logging.warning(f"Kwargs: {kwargs}")
                    logging.warning(f"Result: {result}")
                    raise ValueError(
                        (
                            f"Callback {func.__name__} returned not a dict, it should have a keyword based return. "  # noqa
                            f"Returnded type {type(result)} with length {len(result)}."
                        )
                    )
                if len(result) != num_original_outputs:
                    logging.warning(f"Args: {args}")
                    logging.warning(f"Kwargs: {kwargs}")
                    logging.warning(f"Result: {result}")
                    raise ValueError(
                        (
                            f"Callback {func.__name__} returned not the correct number of outputs. "  # noqa
                            f"Expected {num_original_outputs}, got {len(result)}."
                        )
                    )

                if len(args) == 0:
                    result.update(
                        {
                            "is_open-toast": False,
                            "header-toast": no_update,
                            "is_open-modal": False,
                            "title-modal": no_update,
                            "message-modal": no_update,
                        }
                    )
                else:
                    result = (False, no_update, False, no_update, no_update) + result
                return result

            except PreventUpdate:
                raise

            except Exception as e:  # noqa
                error_traceback = traceback.format_exc()

                # Log the error
                logging.warning(
                    f"Callback error in {func.__name__}: {str(e)}\n{error_traceback}"
                )
                error_title = error_responds_dict.get(
                    type(e), error_responds_dict[Exception]
                )[0]
                error_message = error_responds_dict.get(
                    type(e), error_responds_dict[Exception]
                )[1]

                if len(args) == 0:
                    updates = {key: no_update for key in kwargs["output"].keys()}
                    updates.update(
                        {
                            "is_open-toast": True,
                            "header-toast": error_title,
                            "is_open-modal": True,
                            "title-modal": error_title,
                            "message-modal": error_message,
                        }
                    )
                else:
                    updates = tuple(no_update for _ in range(num_original_outputs))
                    updates = (
                        True,
                        error_title,
                        True,
                        error_title,
                        error_message,
                    ) + updates

                return updates

        return wrapper

    return decorator
