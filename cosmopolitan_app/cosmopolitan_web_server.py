"""Flask app that handles the Cosmopolitan Webserver."""

import os
import traceback
from logging.config import dictConfig

from flask import Flask, render_template, request
from werkzeug.exceptions import HTTPException

# TODO Dash
# from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)

with app.app_context():
    # Only import for loading routes
    import cosmopolitan_app.routes  # noqa
    from cosmopolitan_app.config import DEBUG
    from cosmopolitan_app.cosmopolitan_job_form import json_load_4_jinja

    # Dash components
    from cosmopolitan_app.dash_component import dynamic_plots
    from cosmopolitan_app.dash_component.dash_component import init_dash
    from cosmopolitan_app.db_manager import JobNotFound
    from cosmopolitan_app.logger import get_logger_config

    app = init_dash(app, dynamic_plots.globals_module(), dynamic_plots.app_layout)

# TODO Dash
# csrf = CSRFProtect(app)

dictConfig(get_logger_config(DEBUG))
app.config["SECRET_KEY"] = os.urandom(32)

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024 * 1024  # 5 Gb limit

app.jinja_env.globals.update(json_loads=json_load_4_jinja)


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
        template and a 500 status code.

    Note:
        This function should be registered as an error handler in the Flask app
        using `@app.errorhandler(Exception)`.
    """
    if isinstance(e, JobNotFound):
        return render_template("html/errors/job_not_found_error.html", job_id="a"), 500

    if app.debug:
        raise e

    if isinstance(e, HTTPException):
        return e

    route = request.url_rule
    route_function = request.endpoint

    app.logger.info("Handle exception")
    error = traceback.format_exc()
    content = (
        f"Unexpected error in { route } using { route_function }:\n"
        f"{error}\n"
        f"PID={os.getpid()}\n"
    )
    app.logger.error(content)
    return render_template("html/errors/internal_error.html"), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=app.debug, port=8080)
