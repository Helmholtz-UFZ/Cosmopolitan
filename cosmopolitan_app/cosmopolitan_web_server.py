"""Flask app that handles the Cosmopolitan Webserver."""

import os
import traceback
from logging.config import dictConfig

import sqlalchemy
from flask import Flask, render_template, request
from werkzeug.exceptions import HTTPException, NotFound

from cosmopolitan_app.config import DEBUG
from cosmopolitan_app.cosmopolitan_job import InvalidJobID
from cosmopolitan_app.cosmopolitan_job_form import json_load_4_jinja
from cosmopolitan_app.dash_component import dynamic_plots
from cosmopolitan_app.dash_component.dash_component import init_dash
from cosmopolitan_app.db_manager import JobNotFound
from cosmopolitan_app.logger import get_logger_config

# TODO Dash
# from flask_wtf.csrf import CSRFProtect


app = Flask(__name__)

with app.app_context():
    # Only import for loading routes
    import cosmopolitan_app.routes  # noqa

app = init_dash(app, dynamic_plots.callbacks, dynamic_plots.app_layout)

# TODO Dash
# csrf = CSRFProtect(app)

dictConfig(get_logger_config(DEBUG))
app.config["SECRET_KEY"] = os.urandom(32)

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024 * 1024  # 5 Gb limit

app.jinja_env.globals.update(json_loads=json_load_4_jinja)


def error_response(e):
    """Handle standard errors."""
    if isinstance(e, JobNotFound):
        app.logger.info("Handle JobNotFound exception")
        return (
            render_template("html/errors/job_not_found_error.html", job_id=e.job_id),
            500,
        )

    if isinstance(e, InvalidJobID):
        app.logger.info("Handle InvalidJobID exception")
        return (
            render_template("html/errors/job_not_found_error.html", job_id=e.job_id),
            500,
        )

    if isinstance(e, sqlalchemy.exc.OperationalError):
        app.logger.info("Handle sqlalchemy.exc.OperationalError exception")
        log_error()
        return render_template("html/errors/db_no_connection_error.html"), 500

    if isinstance(e, NotFound):
        app.logger.info("Handle NotFound exception")
        return render_template("html/errors/file_not_found.html"), 404


def log_error():
    """
    Log error with traceback.

    In production this will trigger an email, see logger.py.
    """
    route = request.url_rule
    route_function = request.endpoint

    error = traceback.format_exc()
    content = (
        f"Unexpected error in { route } using { route_function }:\n"
        f"{error}\n"
        f"PID={os.getpid()}\n"
    )
    app.logger.error(content)


@app.errorhandler(Exception)
def handle_exception(e):
    """
    Handle exceptions gracefully within the Flask application.

    This function is an error handler for Exception types and takes appropriate action
    based on the type of exception encountered. It logs the error and returns an HTTP
    response accordingly. In depug mode it simply reraises the error and allows
    werkzeuge to handle the error.


    Parameters:
        e (Exception): The exception that triggered this handler.

    Returns:
        HTTPException or tuple: Depending on the type of exception, this function
        returns an appropriate HTTPException or a tuple containing a rendered error
        template and a status code.

    Note:
        This function should be registered as an error handler in the Flask app
        using `@app.errorhandler(Exception)`.
    """
    app.logger.info("Handle exception")
    handled_response = error_response(e)

    if handled_response:
        return handled_response

    if app.debug:
        raise e

    if isinstance(e, HTTPException):
        return e

    log_error()
    return render_template("html/errors/internal_error.html"), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=app.debug, port=8080)
