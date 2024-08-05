"""Setup tests."""

import logging

import pytest
from flask import Flask
from sqlalchemy.exc import OperationalError

from cosmopolitan_app.config import DB_PW, EMAIL_PASSWORD
from cosmopolitan_app.db_manager import DataBaseManager
from cosmopolitan_app.utils import send_mail

logging.basicConfig(level=logging.DEBUG)

matplotlib_logger = logging.getLogger("matplotlib")
matplotlib_logger.setLevel(logging.CRITICAL)

logging.info("Check environment")
if any(var != "test" for var in [DB_PW, EMAIL_PASSWORD]):
    logging.error("Environment variables not set")
    pytest.exit("Environment variables not set")

logging.info("Check mock server")
try:
    send_mail("Test", "Test", "Test")
except ConnectionRefusedError:
    logging.error("Mail server not available")
    pytest.exit("Mail server not available")

try:
    DataBaseManager.check_existence("test")
except OperationalError:
    logging.error("DB not available")
    pytest.exit("DB not available")


@pytest.fixture(scope="session")
def app():
    """Create a minimal Flask app for the context of CosmopolitanJobForm."""
    app = Flask(__name__)
    app.config["SERVER_NAME"] = "localhost"

    with app.app_context():
        import cosmopolitan_app.routes  # noqa

    yield app
