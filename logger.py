"""
This module defines a logging system for recording application events in a database.

It includes the following components:

1. `Logs` class: Represents a log entry in the database.

2. `SQLAlchemyHandler` class: A custom logging handler that stores log entries in a
   SQLAlchemy database.

3. `get_logger` function: Retrieves a logger instance for logging application events.
     - `debug` (bool): Set to True to enable debugging mode (logs to console), False to
       log to a database and send errors via email.

Note: Configure the database connection and email settings in 'config.py' for proper
functionality.
"""


import logging
from datetime import datetime
from logging.config import dictConfig

from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import (
    DB_HOST_NAME,
    DB_NAME,
    DB_PORT,
    DB_PW,
    DB_USER,
    SENDER_EMAIL,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_SERVER,
    SMTP_USERNAME,
)

Base = declarative_base()


class Logs(Base):
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


def get_logger(debug):
    """
    Get a logger instance for logging application events.

    Set debug to True to enable debugging mode, which logs to console; False to
    log to a database and sends error to email.

    Returns:
        logging.Logger: A logger instance configured based on the input.
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
                "class": "logger.SQLAlchemyHandler",
                "db_url": database_url,
                "level": "INFO",
                "formatter": "default",
            },
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "default",
            },
            "mail_handler": {
                "class": "logging.handlers.SMTPHandler",
                "level": "ERROR",
                "mailhost": (SMTP_SERVER, SMTP_PORT),
                "fromaddr": SENDER_EMAIL,
                "credentials": (SMTP_USERNAME, SMTP_PASSWORD),
                "toaddrs": ["john-eric.anders@ufz.de"],
                "subject": "Application Error",
                "secure": (),
                "formatter": "default",
            },
        },
        "root": {
            "handlers": [],
            "level": "DEBUG",
        },
    }

    if debug:
        logging_config["root"]["handlers"] = ["wsgi"]
    else:
        logging_config["root"]["handlers"] = ["sqlalchemy", "mail_handler"]

    dictConfig(logging_config)
    return logging.getLogger()
