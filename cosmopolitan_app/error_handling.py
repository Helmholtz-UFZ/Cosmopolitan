"""Error handling utilities for Dash apps."""

import logging

import dash_bootstrap_components as dbc
from cosmo_suite.error_handling import USE_ERROR_MESSAGE  # noqa: F401 — re-exported
from cosmo_suite.error_handling import handle_error as _framework_handle_error
from soil_moisture_prediction.input_file_parser import FileValidationError
from werkzeug.exceptions import NotFound

from cosmopolitan_app.constants import (
    ERROR_MESSAGE_DIV_SHARED_ID,
    ERROR_MODAL_SHARED_ID,
    ERROR_TITLE_DIV_SHARED_ID,
)

# The infrastructure exceptions come from the framework, they are NOT redefined
# here. Two classes under one name is the silent failure described in
# ../cosmo-suite/docs/conventions/framework_page_imports.md: since the logs and
# worker-management pages became framework shims, cosmo_suite.db_manager raises the
# framework's JobNotFound while this module's isinstance check and
# error_responds_dict keyed the local one — so a routine "job not found" was
# treated as unexpected, mailed the maintainer, and showed a generic modal.
from cosmo_suite.error_handling import (  # noqa: F401 — re-exported for call sites
    InvalidJobID,
    JobExists,
    JobNotFound,
    RedisConnectionError,
)

log = logging.getLogger(__name__)


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


# Deliberately NOT in error_responds_dict: this is raised inside the nightly
# Celery maintenance task, never inside a callback, so it can never reach the
# error modal. maintenance_tasks.update_db_task handles it instead.
class TimeIOUnavailableError(Exception):
    """Raised when the TimeIO STA API stays unreachable after every retry."""

    def __init__(self, query):
        """Add the failing query as attribute and format error message."""
        self.query = query
        super().__init__(f"TimeIO STA API unreachable after all retries: {query}")


# Laid over cosmo_suite.error_handling.error_responds_dict for this app's calls
# only (see handle_error below). Entries identical to the framework's default —
# the database errors, JobExists, WorkerNotAvailableError, ... — are left out;
# the framework already covers them.
#
# JobNotFound/InvalidJobID still need an entry here even though the framework
# has one too: this app's nav has an "input" page, not the framework's generic
# "job submission" one, and the message names the page to visit.
error_responses = {
    JobNotFound: (
        "Job Not Found",
        "Could not find the job '{job_id}'. Visit input to make a new submission.",
    ),
    InvalidJobID: (
        "Job Not Found",
        "Could not find the job '{job_id}'. Visit input to make a new submission.",
    ),
    NotFinishedException: (
        "Job Not Finished",
        "The job '{job_id}' is not yet finished. Visit submission to see the progress of the job.",  # noqa
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
    MapTileDownloadError: (
        "Map Preview Unavailable",
        "Unable to download map tiles from the tile provider. The external map service may be temporarily unavailable. Please try again later.",  # noqa
    ),
    # A different class from cosmo_suite.error_handling.FileValidationError:
    # this one comes from soil_moisture_prediction.input_file_parser and keeps
    # its own entry, since the framework's table can't match a class it has
    # never imported.
    FileValidationError: (
        "Invalid input files",
        USE_ERROR_MESSAGE,
    ),
}

# Replaces the framework's EXPECTED_ERRORS for this app's calls: three ordinary
# user states (NotFinishedException, SubmittedException, MapTileDownloadError)
# that the framework's default omits, which would otherwise mail the
# maintainer on every occurrence. NotSubmittedException is deliberately absent
# — it was never treated as expected, and still isn't.
EXPECTED_ERRORS = (
    NotFound,
    NotFinishedException,
    JobNotFound,
    InvalidJobID,
    SubmittedException,
    MapTileDownloadError,
)

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


def handle_error(error, *, on_unhandled=None):
    """Handle the error, show it in the modal, and optionally report it.

    Delegates to ``cosmo_suite.error_handling.handle_error``, laying this app's
    own response table and expected-error set over the framework's defaults —
    see ``error_responses`` and ``EXPECTED_ERRORS`` above for why they differ.

    Args:
        error: The exception Dash caught.
        on_unhandled: Forwarded to the framework's handler, which calls it with
            just the exception (no subject/body — build those from ``error`` in
            the hook itself). Keyword-only, so ``handle_error(e)`` and a bare
            ``Dash(on_error=handle_error)`` keep working; the hook is wired
            with a partial in app.py.
    """
    _framework_handle_error(
        error,
        on_unhandled=on_unhandled,
        error_responses=error_responses,
        expected_errors=EXPECTED_ERRORS,
    )
