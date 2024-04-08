"""Setup tests."""

import logging
import os
import shutil

import pytest
from sqlalchemy.exc import OperationalError

from cosmopolitan_app.db_manager import DataBaseManager

# from cosmopolitan_app.utils import send_mail

logging.basicConfig(level=logging.INFO)


@pytest.fixture(scope="session", autouse=True)
def check_availibility_mock():
    """See if the mock server are availabel."""
    logging.info("Check mock server")
    # TODO: Uncomment this when the mail server is available
    # try:
    #     send_mail("Test", "Test", "Test")
    # except ConnectionRefusedError:
    #     logging.error("Mail server not available")
    #     pytest.exit("Mail server not available")
    db_manager = DataBaseManager()
    try:
        db_manager.check_existence("test")
    except OperationalError:
        logging.error("DB not available")
        pytest.exit("DB not available")


@pytest.fixture(scope="session", autouse=True)
def set_up_env():
    """Set up env file.

    Save the current .env file and copy .env_dev_mock to .env.
    """
    logging.info("Setting up env file")
    if os.path.exists(".env"):
        shutil.copyfile(".env", ".env_bak")
    shutil.copyfile(".env_test", ".env")

    yield

    logging.info("Tearing down env file")
    if os.path.exists(".env_bak"):
        shutil.copyfile(".env_bak", ".env")
        os.remove(".env_bak")
    else:
        os.remove(".env")
