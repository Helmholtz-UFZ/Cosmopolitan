"""Dash app with multiple pages."""

import logging
import logging.config
from threading import Thread

from dash import Dash

from cosmopolitan_app.background_job_manager import background_job_manager
from cosmopolitan_app.config import DEBUG, PORT
from cosmopolitan_app.error_handling import handle_error
from cosmopolitan_app.files_route import serve_files
from cosmopolitan_app.layouts import app_layout
from cosmopolitan_app.logger import get_logger_config_web
from cosmo_suite.object_storage_manager import create_bucket, setup_remote

# Configure logging early — before Dash() triggers page-module imports.
logging.config.dictConfig(get_logger_config_web(DEBUG))
log = logging.getLogger(__name__)
log.debug("Web application logging configured.")

# Initialize the Dash app
app = Dash(
    __name__,
    use_pages=True,
    prevent_initial_callbacks=True,
    suppress_callback_exceptions=True,
    on_error=handle_error,
)
server = app.server
# Start Celery Beat scheduler for periodic maintenance tasks
setup_remote()
create_bucket()


def start_beat_scheduler():
    """Start Celery Beat scheduler with thread-specific logging."""
    # The loglevel sets the level globally for the entire app.
    beat = background_job_manager.app.Beat(loglevel="DEBUG")
    beat.run()


# Start Beat scheduler as daemon thread
beat_thread = Thread(target=start_beat_scheduler, daemon=True)
beat_thread.start()
log.info("Celery Beat scheduler started in background thread")

# Serve files
serve_files(app)

# Main app layout
app.layout = app_layout()

if __name__ == "__main__":
    app.run(debug=DEBUG, port=PORT, host="0.0.0.0")
