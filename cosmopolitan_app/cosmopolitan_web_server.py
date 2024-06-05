"""Flask app that handles the Cosmopolitan Webserver."""

import logging
import os
from logging.config import dictConfig

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template
from werkzeug.exceptions import HTTPException

from cosmopolitan_app.config import DEBUG, PORT
from cosmopolitan_app.cosmopolitan_job_form import json_load_4_jinja
from cosmopolitan_app.dash_component import dynamic_plots
from cosmopolitan_app.dash_component.dash_component import init_dash
from cosmopolitan_app.logger import get_logger_config_web
from cosmopolitan_app.utils import clean_up, error_response_args, log_error

# TODO Dash
# from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)

with app.app_context():
    # Only import for loading routes
    import cosmopolitan_app.routes  # noqa

app = init_dash(
    app,
    dynamic_plots.callbacks,
    dynamic_plots.app_layout,
    dynamic_plots.css_route,
    dynamic_plots.base_path,
)

# TODO Dash
# csrf = CSRFProtect(app)
dictConfig(get_logger_config_web(DEBUG))
app.config["SECRET_KEY"] = os.urandom(32)

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024 * 1024  # 5 Gb limit

app.jinja_env.globals.update(json_loads=json_load_4_jinja)

scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(clean_up, "interval", hours=24)
scheduler.start()


def error_response_flask(e):
    """Handle standard errors on flask site."""
    template_kwargs, html_error_code, log_it = error_response_args(e)
    app.logger.info(f"Handle { e.__class__.__name__ }")
    if log_it:
        log_error()

    return (
        render_template(
            "html/errors/error_skeleton.html",
            **template_kwargs,
        ),
        html_error_code,
    )


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
    handled_response = error_response_args(e)

    if handled_response:
        return error_response_flask(e)

    if app.debug:
        raise e

    if isinstance(e, HTTPException):
        return e

    log_error()
    return (
        render_template(
            "html/errors/error_skeleton.html",
            error_page="html/errors/internal_error.html",
        ),
        500,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=app.debug, port=PORT)
elif __name__ == "app":
    # Assumes if not main is run by gunicorn
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
