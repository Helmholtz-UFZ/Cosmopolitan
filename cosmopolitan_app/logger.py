"""Logging configuration for Cosmopolitan App."""

import datetime
import logging
import sys

import psycopg2
from psycopg2 import pool

from cosmopolitan_app.config import (
    POSTGRES_DB,
    POSTGRES_HOST_NAME,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)

format_string = (
    "[%(asctime)s] [PID:%(process)d] %(levelname)s in %(module)s: %(message)s"
)
postgres_params = {
    "dbname": POSTGRES_DB,
    "user": POSTGRES_USER,
    "password": POSTGRES_PASSWORD,
    "host": POSTGRES_HOST_NAME,
    "port": POSTGRES_PORT,
}

log_categories = {
    "Core Areas": ["webserver", "worker", "scheduler"],
    "User Areas": ["job_submission", "frontend"],
    "System Areas": [
        "time_io",
        "database",
        "object_storage",
        "email_service",
        "maintenance",
    ],
    "unknown": ["unknown"],
}


class PostgreSQLHandler(logging.Handler):
    """A log handler that writes log records to a PostgreSQL database.

    This handler supports a tag-based logging system where log records can include
    a 'tag' attribute via the extra parameter to categorize messages by functional area.

    The tag system uses the following approved categories:
    - Core Areas: webserver, worker, scheduler
    - User Areas: job_submission, frontend
    - System Areas: time_io, database, object_storage, email_service, maintenance

    Usage:
        logging.info("Database query completed", extra={"tag": "database"})
        logging.error("TimeIO API failed", extra={"tag": "time_io"})
    """

    def __init__(self, connection_params, tag="unknown"):
        """Initialize the handler with PostgreSQL connection parameters.

        Args:
            connection_params (dict): Connection parameters for PostgreSQL
                                     (dbname, user, password, host, port)
            tag (str): Default tag identifier for logs that don't specify their own tag
            via the extra parameter. Common values: 'webserver', 'worker', 'scheduler'
        """
        available_tags = [tag for tags in log_categories.values() for tag in tags]
        if tag not in available_tags:
            raise ValueError(f"Invalid tag '{tag}'. Must be one of {available_tags}")
        super().__init__()
        self.connection_params = connection_params
        self.tag = tag
        # Create a connection pool for better performance
        # Add keepalive settings to prevent connections from going stale
        pool_params = {
            **connection_params,
            "keepalives": 1,
            "keepalives_idle": 30,  # Start keepalive after 30s idle
            "keepalives_interval": 10,  # Send keepalive every 10s
            "keepalives_count": 5,  # 5 failed keepalives = dead connection
        }
        self.connection_pool = pool.SimpleConnectionPool(
            1,
            10,  # min and max connections
            **pool_params,
        )

    def emit(self, record):
        """
        Write the log record to the database.

        The tag for the log record is determined in this order:
        1. If the record has a 'tag' attribute (from extra={"tag": "value"}), use that
        2. Otherwise, use the handler's default tag set during initialization

        This allows for dynamic tagging on a per-log basis while maintaining
        a reasonable default for the handler instance.

        Args:
            record: The log record to write. May contain 'tag' attribute from extra
            parameter.
        """
        # Get a connection from the pool
        connection = self.connection_pool.getconn()
        connection_is_bad = False

        try:
            with connection.cursor() as cursor:
                # Check if record has extra 'tag' attribute, otherwise use handler
                # default
                tag = getattr(record, "tag", self.tag)

                cursor.execute(
                    """
                    INSERT INTO logs
                    (timestamp, pid, level, module, message, tag)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        datetime.datetime.fromtimestamp(record.created),
                        record.process,
                        record.levelname,
                        record.module,
                        self.format(record),
                        tag,
                    ),
                )
                connection.commit()
        except psycopg2.OperationalError as e:
            # Connection is bad (timeout, network issue, etc.)
            # Mark it as bad so it's not returned to the pool
            connection_is_bad = True
            print(f"Database connection error (will retry with new connection): {e}")

            # Try once more with a fresh connection
            try:
                new_connection = self.connection_pool.getconn()
                try:
                    with new_connection.cursor() as cursor:
                        tag = getattr(record, "tag", self.tag)
                        cursor.execute(
                            """
                            INSERT INTO logs
                            (timestamp, pid, level, module, message, tag)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (
                                datetime.datetime.fromtimestamp(record.created),
                                record.process,
                                record.levelname,
                                record.module,
                                self.format(record),
                                tag,
                            ),
                        )
                        new_connection.commit()
                finally:
                    self.connection_pool.putconn(new_connection)
            except (
                Exception
            ) as retry_error:  # retry can fail for any DB reason; fatal  # noqa
                print(
                    f"FATAL: Database logging failed after retry. "
                    f"Worker cannot continue without logging capability: {retry_error}"
                )
                # Re-raise to fail the worker - logging is critical
                raise
        except (
            Exception
        ) as e:  # any DB error is fatal — worker cannot operate without logging
            # Any other database error is also fatal
            print(f"FATAL: Error writing to PostgreSQL: {e}")
            # Re-raise to fail the worker
            raise
        finally:
            # Return the connection to the pool, or close it if it's bad
            if connection_is_bad:
                try:
                    connection.close()
                except (
                    Exception
                ):  # close can fail on broken connection; safe to ignore  # noqa
                    pass
                # putconn with close=True tells the pool this connection is bad
                self.connection_pool.putconn(connection, close=True)
            else:
                self.connection_pool.putconn(connection)

    def close(self):
        """Close all database connections when the handler is closed."""
        if hasattr(self, "connection_pool") and self.connection_pool:
            self.connection_pool.closeall()
        super().close()


class ExcludeSubmodulesFilter(logging.Filter):
    """Exclude submodules."""

    def filter(self, record):
        """Filter."""
        # print("NAME:", record.name, "MODULE:", record.module)
        excluded_packages = [
            "matplotlib",
            "PIL",
            "rasterio",
            "watchdog",
            "selenium",
        ]
        excluded_modules = [
            "_internal",
        ]
        return (
            not any(record.name.startswith(package) for package in excluded_packages)
            and record.module not in excluded_modules
        )


def get_logger_config_compuation(log_file_path):
    """Get the config dic for the computation logger."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {"exclude_submodules": {"()": ExcludeSubmodulesFilter}},
        "handlers": {
            "file": {
                "class": "logging.FileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": log_file_path,
                "mode": "w",
                "filters": ["exclude_submodules"],
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
            "filters": ["exclude_submodules"],
        },
    }


def _build_stream_config(stream, disable_existing_loggers, tag="webserver"):
    """Build a logging config that writes to a stream and PostgreSQL.

    Args:
        stream: The stream ext:// URI for the StreamHandler
            (e.g. "ext://sys.stderr" or "ext://sys.__stderr__")
        disable_existing_loggers: Whether to disable loggers not in the config.
            False preserves Celery's own handlers; True is the default for the
            web process in production.
        tag: Default tag for the PostgreSQLHandler.

    Returns:
        dict: Logging configuration dictionary for use with dictConfig()
    """
    return {
        "version": 1,
        "disable_existing_loggers": disable_existing_loggers,
        "formatters": {
            "default": {"format": format_string},
            "message_only": {"format": "%(message)s"},
        },
        "filters": {"exclude_submodules": {"()": ExcludeSubmodulesFilter}},
        "handlers": {
            "stream": {
                "class": "logging.StreamHandler",
                "stream": stream,
                "formatter": "default",
                "filters": ["exclude_submodules"],
                "level": "DEBUG",
            },
            "postgres": {
                "class": __name__ + ".PostgreSQLHandler",
                "level": "DEBUG",
                "formatter": "message_only",
                "filters": ["exclude_submodules"],
                "connection_params": postgres_params,
                "tag": tag,
            },
        },
        "root": {
            "handlers": ["stream", "postgres"],
            "level": "DEBUG",
            "filters": ["exclude_submodules"],
        },
    }


def get_logger_config_web(debug, tag="webserver"):
    """Get the logging configuration for the web process (Dash/Flask).

    Writes to sys.stderr and PostgreSQL.

    Args:
        debug (bool): Whether to enable debug mode logging
        tag (str): Default tag for the PostgreSQLHandler.

    Returns:
        dict: Logging configuration dictionary for use with dictConfig()
    """
    in_tests = "pytest" in sys.modules
    return _build_stream_config(
        stream="ext://sys.stderr",
        disable_existing_loggers=not in_tests,
        tag=tag,
    )


def get_logger_config_worker(tag="worker"):
    """Get the logging configuration for use inside a Celery worker task.

    Writes to sys.__stderr__ (the real stderr fd) instead of sys.stderr.
    This is necessary because Celery's prefork pool replaces sys.stderr
    with a LoggingProxy, and writing to it from a StreamHandler causes
    circular recursion.

    disable_existing_loggers is always False to preserve Celery's own
    logging handlers.

    Args:
        tag (str): Default tag for the PostgreSQLHandler.

    Returns:
        dict: Logging configuration dictionary for use with dictConfig()
    """
    return _build_stream_config(
        stream="ext://sys.__stderr__",
        disable_existing_loggers=False,
        tag=tag,
    )
