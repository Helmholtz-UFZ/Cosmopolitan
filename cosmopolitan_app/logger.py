"""
This module defines a logging system for recording application events in a database.

It includes the following components:

1. `Logs` class: Represents a log entry in the database.

2. `SQLAlchemyHandler` class: A custom logging handler that stores log entries in a
   SQLAlchemy database.

3. `get_logger` function: Get the config dic for the flask logger.
     - `debug` (bool): Set to True to enable debugging mode (logs to console), False to
       log to a database and send errors via email.

Note: Configure the database connection and email settings in 'config.py' for proper
functionality.
"""

import logging

from cosmopolitan_app.config import (
    EMAIL_PASSWORD,
    EMAIL_PORT,
    EMAIL_SENDER,
    EMAIL_SERVER,
    EMAIL_USERNAME,
)


class ExcludeSubmodulesFilter(logging.Filter):
    """Exclude submodules."""

    def filter(self, record):
        """Filter."""
        excluded_modules = ["matplotlib", "PIL"]
        return not any(record.name.startswith(module) for module in excluded_modules)


def get_logger_config_compuation(log_file_path):
    """Get the config dic for the computation logger."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "file": {
                "class": "logging.FileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": log_file_path,
                "mode": "w",
            },
        },
        "formatters": {
            "detailed": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            },
        },
        "root": {
            "level": "DEBUG",
            "handlers": ["file"],
        },
    }


def get_logger_config_web(debug):
    """
    Get the config dic for the flask logger.

    Set debug to True to enable debugging mode, which logs to console; False to
    log to a database and sends error to email.

    Returns:
        dic: Dictinoray for dictConfig.
    """
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            },
        },
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "default",
                "filters": ["exclude_submodules"],
            },
            "mail_handler": {
                "class": "logging.handlers.SMTPHandler",
                "level": "ERROR",
                "mailhost": (EMAIL_SERVER, EMAIL_PORT),
                "fromaddr": EMAIL_SENDER,
                "credentials": (EMAIL_USERNAME, EMAIL_PASSWORD),
                "toaddrs": ["john-eric.anders@ufz.de"],
                "subject": "Application Error",
                "secure": (),
                "formatter": "default",
                "filters": ["exclude_submodules"],
            },
        },
        "root": {
            "handlers": [],
            "level": "DEBUG",
            "filters": ["exclude_submodules"],
        },
        "filters": {"exclude_submodules": {"()": ExcludeSubmodulesFilter}},
    }

    logging_config["root"]["handlers"] = ["wsgi", "mail_handler"]

    # Mockup cant handle ttls
    if EMAIL_PASSWORD == "test":
        logging_config["handlers"]["mail_handler"]["secure"] = None

    return logging_config
