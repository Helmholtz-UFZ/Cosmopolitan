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
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from cosmopolitan_app.config import (
    DB_HOST_NAME,
    DB_NAME,
    DB_PORT,
    DB_PW,
    DB_USER,
    EMAIL_PASSWORD,
    EMAIL_PORT,
    EMAIL_SENDER,
    EMAIL_SERVER,
    EMAIL_USERNAME,
)


class Base(DeclarativeBase):
    """Base class for all declarative classes in the application."""

    pass


class Logs(DeclarativeBase):
    """Represents a log entry in the database.

    Attributes:
        id (int): The unique identifier for the log entry.
        timestamp (DateTime): The timestamp when the log entry was created.
        level (str): The log level (e.g., 'INFO', 'ERROR').
        message (str): The log message.

    """

    __tablename__ = "logs"

    log_id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True))
    level = Column(String(10))
    message = Column(String)


class SQLAlchemyHandler(logging.Handler):
    """
    Custom logging handler that stores log entries in a SQLAlchemy database.

    Attributes:
        db_url (str): The database connection URL.
    """

    def __init__(self, db_url):
        """
        Initialize the SQLAlchemyHandler.

        Args:
            db_url (str): The database connection URL.
        """
        super().__init__()
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)

    def emit(self, record):
        """
        Emit a log record to the database.

        Args:
            record (LogRecord): The log record to be emitted.
        """
        message = self.format(record)
        level = record.levelname
        timestamp = datetime.utcfromtimestamp(record.created).isoformat()

        with self.Session() as session:
            log_entry = Logs(level=level, message=message, timestamp=timestamp)
            session.add(log_entry)
            session.commit()


class ExcludeDebugMatplotLibFilter(logging.Filter):
    """Exclude debug logs from font manager."""

    def filter(self, record):
        """Filter."""
        return not (
            record.name.startswith("matplotlib") and record.levelno == logging.DEBUG
        )


def get_logger_config(debug):
    """
    Get the config dic for the flask logger.

    Set debug to True to enable debugging mode, which logs to console; False to
    log to a database and sends error to email.

    Returns:
        dic: Dictinoray for dictConfig.
    """
    database_url = (
        f"postgresql+psycopg2://{ DB_USER }:{ DB_PW }@"
        f"{ DB_HOST_NAME }:{ DB_PORT }/{ DB_NAME }"
    )

    # Log some messages
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            },
        },
        "handlers": {
            "sqlalchemy": {
                "class": "cosmopolitan_app.logger.SQLAlchemyHandler",
                "db_url": database_url,
                "level": "INFO",
                "formatter": "default",
                "filters": ["exclude_debug_matplotlib"],
            },
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "default",
                "filters": ["exclude_debug_matplotlib"],
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
                "filters": ["exclude_debug_matplotlib"],
            },
        },
        "root": {
            "handlers": [],
            "level": "DEBUG",
            "filters": ["exclude_debug_matplotlib"],
        },
        "filters": {"exclude_debug_matplotlib": {"()": ExcludeDebugMatplotLibFilter}},
    }

    logging_config["root"]["handlers"] = ["wsgi", "mail_handler"]

    # Mockup cant handle ttls
    if EMAIL_PASSWORD == "test":
        logging_config["handlers"]["mail_handler"]["secure"] = None

    # TODO remove sql alchemy handle and this code below
    # if debug == "1":
    #     # logging_config["root"]["handlers"] = ["wsgi"]
    #     # logging_config["root"]["handlers"] = ["wsgi", "mail_handler"]
    # else:
    #     logging_config["root"]["handlers"] = ["wsgi", "mail_handler"]
    #     # logging_config["root"]["handlers"] = ["sqlalchemy", "mail_handler"]

    return logging_config
