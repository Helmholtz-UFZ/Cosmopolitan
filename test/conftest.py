"""Setup tests."""

import logging
import os
import shutil
import socket
import subprocess

import pytest
from flask import Flask
from sqlalchemy.exc import OperationalError

from cosmopolitan_app.config import EMAIL_PASSWORD, MINIO_ALIAS, POSTGRES_PW
from cosmopolitan_app.minio_manager import MinioError, create_bucket
from cosmopolitan_app.postgres_manager import PostgresManager
from cosmopolitan_app.utils import send_mail


def create_logger():
    """Create a logger with debug level."""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logging.getLogger("matplotlib").setLevel(logging.CRITICAL)
    logging.getLogger("PIL").setLevel(logging.CRITICAL)
    logging.getLogger("osgeo").setLevel(logging.ERROR)
    logging.getLogger("rasterio").setLevel(logging.ERROR)
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    logging.getLogger("requests").setLevel(logging.ERROR)
    logging.getLogger("wcs201").setLevel(logging.ERROR)
    return logger


log = create_logger()

try:
    subprocess.run(["mc", "-v"], check=True, text=True, capture_output=True)
except FileNotFoundError:
    pytest.exit("mc command not available")

try:
    create_bucket(reset_alias=True)
    subprocess.run(["mc", "ping", "-x", MINIO_ALIAS], check=True, capture_output=True)
except MinioError:
    pytest.exit("Can not set mc alias")

if any(var != "test" for var in [POSTGRES_PW, EMAIL_PASSWORD, MINIO_ALIAS]):
    pytest.exit("Environment variables not set")

try:
    send_mail("test@example.com", "Test", "Test")
except (ConnectionRefusedError, socket.gaierror):
    pytest.exit("Mail server not available")

try:
    PostgresManager.check_existence("test")
except OperationalError:
    pytest.exit("postgres not available")


# Save the current .env file
if os.path.exists(".env"):
    shutil.copyfile(".env", ".env_test_backup")


@pytest.fixture(scope="session")
def app():
    """Create a minimal Flask app for the context of CosmopolitanJobForm."""
    app = Flask(__name__)
    app.config["SERVER_NAME"] = "localhost"

    with app.app_context():
        import cosmopolitan_app.routes  # noqa

    yield app


@pytest.fixture
def logger():
    """Create a logger with suppressed external sources."""
    return create_logger()


def pytest_sessionfinish(session, exitstatus):
    """Restore .env file."""
    if os.path.exists(".env_test_backup"):
        shutil.copyfile(".env_test_backup", ".env")
        os.remove(".env_test_backup")
    else:
        os.remove(".env")
