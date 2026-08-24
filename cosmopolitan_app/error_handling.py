"""Error handling utilities for Dash apps."""

import json
import logging
import traceback

import dash
import dash_bootstrap_components as dbc
import psycopg2
from dash import set_props
from soil_moisture_prediction.input_file_parser import FileValidationError
from sqlalchemy.exc import DatabaseError, OperationalError
from werkzeug.exceptions import NotFound

from cosmopolitan_app.constants import (
    ERROR_MESSAGE_DIV_SHARED_ID,
    ERROR_MODAL_SHARED_ID,
    ERROR_TITLE_DIV_SHARED_ID,
    LOADING_OVERLAY_MODAL_SHARED_ID,
)

# The infrastructure exceptions come from the framework, they are NOT redefined
# here. Two classes under one name is the silent failure described in
# ../cosmo-suite/docs/conventions/framework_page_imports.md: since the logs and
# worker-management pages became framework shims, cosmo_suite.db_manager raises the
# framework's JobNotFound while this module's isinstance check and
# error_responds_dict keyed the local one — so a routine "job not found" was
# treated as unexpected, mailed the maintainer, and showed a generic modal.
# Verified before the switch that all seven are structurally identical (same
# constructor, same bases).
from cosmo_suite.error_handling import (  # noqa: F401 — re-exported for call sites
    InvalidJobID,
    JobExists,
    JobNotFound,
    RedisConnectionError,
    TaskNotFoundError,
    WorkerManagementError,
    WorkerNotAvailableError,
)
from cosmo_suite.object_storage_manager import ObjectStorageError

log = logging.getLogger(__name__)

USE_ERROR_MESSAGE = "use_error_message"


class NoMeasurementPointsError(Exception):
    """Raised when no measurement points are found for the given parameters."""

    ...


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


class MapTileDownloadError(Exception):
    """Raised when map tiles cannot be downloaded from external tile provider."""

    ...


database_error_title = "Database Connection Error"
database_error_message = "Unfortunately, it is not possible to connect to the job database. Please try again later."  # noqa
error_responds_dict = {
    psycopg2.DatabaseError: (
        database_error_title,
        database_error_message,
    ),
    DatabaseError: (
        database_error_title,
        database_error_message,
    ),
    OperationalError: (
        database_error_title,
        database_error_message,
    ),
    ObjectStorageError: (
        database_error_title,
        database_error_message,
    ),
    NotFound: ("File Not Found", "The file could not be found."),
    Exception: ("Internal Error", "Ups this should not happen. An error occurred."),
    NotFinishedException: (
        "Job Not Finished",
        "The job '{job_id}' is not yet finished. Visit submission to see the progress of the job.",  # noqa
    ),
    JobNotFound: (
        "Job Not Found",
        "Could not find the job '{job_id}'. Visit input to make a new submission.",
    ),
    InvalidJobID: (
        "Job Not Found",
        "Could not find the job '{job_id}'. Visit input to make a new submission.",
    ),
    NotSubmittedException: (
        "Job Not Submitted",
        "The job '{job_id}' was not yet submitted. Visit submit to submit the job.",  # noqa
    ),
    SubmittedException: (
        "Job Already Submitted",
        "The job '{job_id}' was already submitted. Visit job to see the status of the job. Or submit a new job at input.",  # noqa
    ),
    NoMeasurementPointsError: (
        "No Measurement Points",
        "In the provided area and time range, no measurement points were found. Please adjust your input parameters. Or provide a input file with measurement points.",  # noqa
    ),
    WorkerNotAvailableError: (
        "No Workers Available",
        "No Celery workers are currently running. Please check the worker service status.",  # noqa
    ),
    TaskNotFoundError: (
        "Task Not Found",
        "The selected task could not be found. It may have already completed or been cancelled.",  # noqa
    ),
    RedisConnectionError: (
        "Background Service Unavailable",
        "The background job service is temporarily unavailable. Please try again later.",  # noqa
    ),
    JobExists: (
        "Job Already Exists",
        "A job with ID '{job_id}' already exists. Please use a different job ID.",
    ),
    MapTileDownloadError: (
        "Map Preview Unavailable",
        "Unable to download map tiles from the tile provider. The external map service may be temporarily unavailable. Please try again later.",  # noqa
    ),
    FileValidationError: (
        "Invalid input files",
        USE_ERROR_MESSAGE,
    ),
}
error_modal = dbc.Modal(
    [
        dbc.ModalHeader(
            dbc.ModalTitle("Error"),
            id=ERROR_TITLE_DIV_SHARED_ID,
            close_button=False,
            className="bg-light",
        ),
        dbc.ModalBody(id=ERROR_MESSAGE_DIV_SHARED_ID, className="text-danger bg-light"),
        dbc.ModalFooter(className="bg-light"),
    ],
    id=ERROR_MODAL_SHARED_ID,
    is_open=False,
)


def _truncate_string(value, max_length=200, head_length=100, tail_length=50):
    """Truncate a string if it exceeds max_length."""
    if not isinstance(value, str):
        return value
    if len(value) <= max_length:
        return value
    return f"{value[:head_length]}...{value[-tail_length:]}"


def _truncate_data(data):
    """Recursively truncate long strings in data structures."""
    if isinstance(data, dict):
        return {key: _truncate_data(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [_truncate_data(item) for item in data]
    elif isinstance(data, str):
        return _truncate_string(data)
    else:
        return data


def handle_error(error, *, on_unhandled=None):
    """Handle the error, show it in the modal, and optionally report it.

    Args:
        error: The exception Dash caught.
        on_unhandled: Called with the exception for errors outside the expected
            set — the same ones that get a full traceback logged. This app mails
            its maintainer from here. Keyword-only, so ``handle_error(e)`` and a
            bare ``Dash(on_error=handle_error)`` keep working; the hook is wired
            with a partial in app.py.

            This module deliberately does not import the mail service any more:
            that import edge ran error_handling -> email_service -> config and
            put a notification concern inside the error path. Mirrors
            ``cosmo_suite.error_handling.handle_error``'s seam.

    Note: this app keeps its own handler rather than adopting the framework's.
    Measured against cosmo-suite v0.6.1, the framework version treats only
    (NotFound, JobNotFound, InvalidJobID) as expected, where this app also
    expects NotFinishedException, SubmittedException and MapTileDownloadError —
    all three normal user-facing conditions that would otherwise mail the
    maintainer and log a traceback. It also has no USE_ERROR_MESSAGE sentinel,
    and its FileValidationError entry reads "Ups this should not happen" where
    this app shows the user what is actually wrong with the uploaded file.
    Framework MRs: an expected-errors parameter, and sentinel support.
    """
    log.debug(f"Error: {error}")

    if not isinstance(
        error,
        (
            NotFound,
            NotFinishedException,
            JobNotFound,
            InvalidJobID,
            SubmittedException,
            MapTileDownloadError,
        ),
    ):
        callback_context = dash.ctx
        truncated_triggered = _truncate_data(callback_context.triggered)
        email_subject = f"Error {str(error)}"
        email_body = (
            f"Traceback info: {traceback.format_exc()}\n\n"
            f"Input info: {json.dumps(truncated_triggered)}"
        )
        # Log to DB first — email may block or fail
        log.error(f"Unhandled error: {error}")
        log.error(email_body)
        if on_unhandled is not None:
            # Convention deviation (CLAUDE.md: no bare `except Exception`). The hook
            # is a notification, typically an SMTP send; it must not be able to take
            # the error modal down with it. A notification failing is no reason to
            # hide the error it was reporting from the user.
            try:
                on_unhandled(error, email_subject, email_body)
            except Exception:  # noqa — see above
                log.error("on_unhandled hook failed", exc_info=True)

    # dispatch lookup: unknown exception types fall back to the generic Exception entry
    error_title = error_responds_dict.get(type(error), error_responds_dict[Exception])[
        0
    ]
    error_message = error_responds_dict.get(
        type(error), error_responds_dict[Exception]
    )[1]

    if error_message == USE_ERROR_MESSAGE:
        error_message = str(error)

    try:
        error_message = error_message.format(job_id=error.job_id)
    except AttributeError:
        # If the error does not have a job_id attribute, we just use the message as is.
        pass

    log.error(f"{error_title}: {error_message}")
    log.error(f"Error details: {traceback.format_exc()}")
    set_props(LOADING_OVERLAY_MODAL_SHARED_ID, {"is_open": False})
    set_props(ERROR_MODAL_SHARED_ID, {"is_open": True})
    set_props(ERROR_TITLE_DIV_SHARED_ID, {"children": error_title})
    set_props(ERROR_MESSAGE_DIV_SHARED_ID, {"children": error_message})
