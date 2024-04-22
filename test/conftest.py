"""Setup tests."""

import logging

import pytest
from sqlalchemy.exc import OperationalError

from cosmopolitan_app.config import CLUSTER_TOKEN, DB_PW, EMAIL_PASSWORD
from cosmopolitan_app.db_manager import DataBaseManager

# from cosmopolitan_app.utils import send_mail

logging.basicConfig(level=logging.INFO)

logging.info("Check environment")
if any(var != "test" for var in [DB_PW, EMAIL_PASSWORD, CLUSTER_TOKEN]):
    logging.error("Environment variables not set")
    pytest.exit("Environment variables not set")

logging.info("Check mock server")
# TODO: Uncomment this when the mail server is available
# try:
#     send_mail("Test", "Test", "Test")
# except ConnectionRefusedError:
#     logging.error("Mail server not available")
#     pytest.exit("Mail server not available")
try:
    DataBaseManager.check_existence("test")
except OperationalError:
    logging.error("DB not available")
    pytest.exit("DB not available")
