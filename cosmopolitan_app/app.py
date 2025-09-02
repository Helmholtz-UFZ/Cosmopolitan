"""Dash app with multiple pages."""

import logging
from logging.config import dictConfig
from threading import Thread

import dash
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html

from cosmopolitan_app.background_job_manager import get_background_job_manager
from cosmopolitan_app.config import DEBUG, PORT
from cosmopolitan_app.error_handling import error_modal, handle_error
from cosmopolitan_app.files_route import serve_files
from cosmopolitan_app.layouts import (
    create_navbar,
    loading_overlay,
    register_navbar_callbacks,
)
from cosmopolitan_app.logger import get_logger_config_web

# Initialize the Dash app
app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.FLATLY, dbc.icons.BOOTSTRAP],
    prevent_initial_callbacks="initial_duplicate",
    suppress_callback_exceptions=True,
    on_error=handle_error,
)
server = app.server

# Real server logging configuration
dictConfig(get_logger_config_web(DEBUG))
server.logger.setLevel(logging.DEBUG)
logging.debug("Web application logging configured.")
# Start Celery Beat scheduler for periodic maintenance tasks


def start_beat_scheduler():
    """Start Celery Beat scheduler with thread-specific logging."""
    job_manager = get_background_job_manager()
    # The loglevel sets the level globally for the entire app.
    beat = job_manager.app.Beat(loglevel="DEBUG")
    beat.run()


# Start Beat scheduler as daemon thread
beat_thread = Thread(target=start_beat_scheduler, daemon=True)
beat_thread.start()
logging.info(
    "Celery Beat scheduler started in background thread", extra={"tag": "scheduler"}
)

# Serve static files
serve_files(app)

# Layout components
nav_bar = create_navbar(dash.page_registry)
register_navbar_callbacks(app)

# Content layout
class_names_content = (
    "col-md-11 col-lg-10 col-xl-9 bg-white border border-dark rounded p-0"
)
content = dbc.Row(
    dbc.Col(
        className="d-flex justify-content-center pb-4 pt-2",
        children=[
            html.Div(
                className=class_names_content,
                children=[
                    dash.page_container,
                ],
            )
        ],
    )
)

# Main app layout
app.layout = html.Div(
    className="d-flex flex-column min-vh-100 bg-light",
    children=[
        dcc.Location(id="url", refresh=True),
        error_modal,
        nav_bar,
        content,
        loading_overlay,
    ],
)

if __name__ == "__main__":
    app.run(debug=DEBUG, port=PORT, host="0.0.0.0")
