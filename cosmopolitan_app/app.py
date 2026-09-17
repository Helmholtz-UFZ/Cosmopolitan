"""Dash app with multiple pages."""

import logging
import logging.config
import traceback
from functools import partial

from dash import Dash

from cosmo_suite.files_route import serve_files
from cosmo_suite.logger import get_logger_config_web

from cosmopolitan_app.constants.general import EXCLUDED_LOG_PACKAGES
from cosmopolitan_app.config import DEBUG, MAINTAINER_EMAIL, PORT
from cosmopolitan_app.email_service import send_mail
from cosmopolitan_app.error_handling import handle_error
from cosmopolitan_app.job import Job
from cosmopolitan_app.layouts import app_layout
from cosmo_suite.object_storage_manager import create_bucket, setup_remote

# Configure logging early — before Dash() triggers page-module imports.
logging.config.dictConfig(get_logger_config_web(DEBUG, EXCLUDED_LOG_PACKAGES))
log = logging.getLogger(__name__)
log.debug("Web application logging configured.")


def notify_maintainer(error):
    """Mail the maintainer about an unhandled callback error.

    Wired into `handle_error` as its `on_unhandled` hook rather than imported by
    error_handling, so the error path carries no mail dependency. The handler
    guards this call: if the send fails, the user still gets the error modal.

    cosmo-suite v0.7.0's handle_error calls this hook with only the exception —
    it logs the traceback and triggered inputs itself but no longer hands them
    to the hook — so the mail's subject and body are built here instead.
    """
    subject = f"Error {error}"
    body = f"Traceback info: {traceback.format_exc()}"
    log.error(f"Reporting unhandled error to {MAINTAINER_EMAIL}: {error}")
    send_mail(MAINTAINER_EMAIL, subject, body)


# Initialize the Dash app
app = Dash(
    __name__,
    use_pages=True,
    prevent_initial_callbacks=True,
    suppress_callback_exceptions=True,
    on_error=partial(handle_error, on_unhandled=notify_maintainer),
)
server = app.server
setup_remote()
create_bucket()

# No Celery Beat here: it runs embedded in the worker (docker/worker.Dockerfile).
# Gunicorn with --preload imports this module once and then forks its workers; a
# thread started at import can hold one of Celery's internal locks at that moment,
# and the forked worker then blocks forever on its first task submission. Without
# --preload every worker would start its own Beat instead, and every scheduled task
# would run once per worker. See docs/conventions/celery_beat.md in cosmo-suite.

# Serve files
# job_class is this app's Job, not the framework's: serve_files needs a class
# it can construct as Job(job_id) and that exposes working_dir, both of which
# the BaseJob contract plus that one extra member now guarantee.
serve_files(app, job_class=Job)

# Main app layout
app.layout = app_layout()

if __name__ == "__main__":
    app.run(debug=DEBUG, port=PORT, host="0.0.0.0")
