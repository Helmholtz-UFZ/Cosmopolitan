"""Logging configuration for Cosmopolitan App."""

import datetime
import logging

from psycopg2 import pool

from cosmopolitan_app.config import (
    POSTGRES_DB,
    POSTGRES_HOST_NAME,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)


class PostgreSQLHandler(logging.Handler):
    """A log handler that writes log records to a PostgreSQL database."""

    def __init__(self, connection_params):
        """Initialize the handler with PostgreSQL connection parameters.

        Args:
            connection_params (dict): Connection parameters for PostgreSQL
                                     (dbname, user, password, host, port)
        """
        super().__init__()
        self.connection_params = connection_params
        # Create a connection pool for better performance
        self.connection_pool = pool.SimpleConnectionPool(
            1,
            10,  # min and max connections
            **connection_params,
        )

    def emit(self, record):
        """
        Write the log record to the database.

        Args:
            record: The log record to write
        """
        # Get a connection from the pool
        connection = self.connection_pool.getconn()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO logs
                    (timestamp, pid, level, module, message)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        datetime.datetime.fromtimestamp(record.created),
                        record.process,
                        record.levelname,
                        record.module,
                        self.format(record),
                    ),
                )
                connection.commit()
        except Exception as e:  # noqa
            # Handle any errors that may occur
            self.handleError(record)
            print(f"Error writing to PostgreSQL: {e}")
        finally:
            # Return the connection to the pool
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
        excluded_modules = ["matplotlib", "PIL", "rasterio"]
        return not any(record.name.startswith(module) for module in excluded_modules)


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


def get_logger_config_web(debug):
    """Get the config dic for the webservice logger."""
    postgres_params = {
        "dbname": POSTGRES_DB,
        "user": POSTGRES_USER,
        "password": POSTGRES_PASSWORD,
        "host": POSTGRES_HOST_NAME,
        "port": POSTGRES_PORT,
    }

    logging_config = {
        "version": 1,
        "disable_existing_loggers": True,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] [PID:%(process)d] %(levelname)s in %(module)s: %(message)s",  # noqa
            },
            "message_only": {
                "format": "%(message)s",
            },
        },
        "filters": {"exclude_submodules": {"()": ExcludeSubmodulesFilter}},
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "default",
                "filters": ["exclude_submodules"],
            },
            "postgres": {
                "class": __name__ + ".PostgreSQLHandler",
                "level": "DEBUG",
                "formatter": "message_only",
                "filters": ["exclude_submodules"],
                "connection_params": postgres_params,
            },
        },
        "root": {
            "handlers": ["wsgi"],
            "level": "DEBUG",
            "filters": ["exclude_submodules"],
        },
        "loggers": {
            "cosmopolitan_app": {
                "level": "DEBUG",
                "handlers": ["wsgi"],
                "propagate": False,
            },
            "matplotlib": {
                "level": "WARNING",
                "handlers": [],
                "propagate": False,
            },
            "rasterio": {
                "level": "WARNING",
                "handlers": [],
                "propagate": False,
            },
        },
    }

    # if not debug:
    #     logging_config["root"]["handlers"].append("postgres")
    #     logging_config["loggers"]["cosmopolitan_app"]["handlers"].append("postgres")
    logging_config["root"]["handlers"].append("postgres")
    logging_config["loggers"]["cosmopolitan_app"]["handlers"].append("postgres")
    return logging_config
