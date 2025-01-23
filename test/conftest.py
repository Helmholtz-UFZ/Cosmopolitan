"""Setup tests."""

import socket
import subprocess

import pytest
from flask import Flask
from sqlalchemy.exc import OperationalError

from cosmopolitan_app.config import EMAIL_PASSWORD, MINIO_ALIAS, POSTGRES_PW
from cosmopolitan_app.minio_manager import MinioError, set_alias
from cosmopolitan_app.postgres_manager import PostgresManager
from cosmopolitan_app.utils import send_mail

try:
    subprocess.run(["mc", "-v"], check=True)
except FileNotFoundError:
    pytest.exit("mc command not available")

try:
    set_alias("test")
    subprocess.run(["mc", "ping", "-x", MINIO_ALIAS], check=True)
except MinioError:
    pytest.exit("Can not set mc alias")

if any(var != "test" for var in [POSTGRES_PW, EMAIL_PASSWORD, MINIO_ALIAS]):
    pytest.exit("Environment variables not set")

try:
    send_mail("Test", "Test", "Test")
except (ConnectionRefusedError, socket.gaierror):
    pytest.exit("Mail server not available")

try:
    PostgresManager.check_existence("test")
except OperationalError:
    pytest.exit("postgres not available")


@pytest.fixture(scope="session")
def app():
    """Create a minimal Flask app for the context of CosmopolitanJobForm."""
    app = Flask(__name__)
    app.config["SERVER_NAME"] = "localhost"

    with app.app_context():
        import cosmopolitan_app.routes  # noqa

    yield app
