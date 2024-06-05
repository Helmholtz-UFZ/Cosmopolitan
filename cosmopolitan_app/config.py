"""This module defines variables, dir structure and includes widely used functions."""

import os

from dotenv import load_dotenv


def getenv(name):
    """
    Retrieve the value of an environment variable.

    This function is a wrapper around the `os.getenv` function and provides additional
    error handling by raising a `ValueError` if the requested environment variable is
    not set.
    """
    value = os.getenv(name)

    if value is None:
        raise ValueError(f"Enviroment variable {name} not set.")
    return value


# Number of days to keep a submitted job entries in the database
DAYS_DELETE_SUMBITTED = 60
# Number of days to keep an unsubmitted job entries in the database
DAYS_DELETE_NOT_SUMBITTED = 2
load_dotenv()

# s/=.*//g |'<,'> s/^.*$/& = getenv("&")/g | noh
WEB_WORK_DIR = getenv("WEB_WORK_DIR")
WEB_OUTSIDE_URL = getenv("WEB_OUTSIDE_URL")
PORT = getenv("FLASK_PORT")
EMAIL_SERVER = getenv("EMAIL_SERVER")
EMAIL_PORT = getenv("EMAIL_PORT")
EMAIL_USERNAME = getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = getenv("EMAIL_PASSWORD")
EMAIL_SENDER = getenv("EMAIL_SENDER")
DB_NAME = getenv("DB_NAME")
DB_HOST_NAME = getenv("DB_HOST_NAME")
DB_PORT = getenv("DB_PORT")
DB_USER = getenv("DB_USER")
DB_PW = getenv("DB_PW")
DEBUG = getenv("FLASK_DEBUG")
