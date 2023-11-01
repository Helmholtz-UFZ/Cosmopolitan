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


DAYS_DELETE_SUMBITTED = 2
DAYS_DELETE_NOT_SUMBITTED = 60

load_dotenv()

try:
    # s/=.*//g |'<,'> s/^.*$/& = getenv("&")/g | noh
    WEB_UPLOAD_DIR = getenv("WEB_UPLOAD_DIR")
    WEB_INPUT_DIR = getenv("WEB_INPUT_DIR")
    EMAIL_SERVER = getenv("EMAIL_SERVER")
    EMAIL_PORT = getenv("EMAIL_PORT")
    EMAIL_USERNAME = getenv("EMAIL_USERNAME")
    EMAIL_PASSWORD = getenv("EMAIL_PASSWORD")
    EMAIL_SENDER = getenv("EMAIL_SENDER")
    CLUSTER_WORK_DIR = getenv("CLUSTER_WORK_DIR")
    CLUSTER_PYTHON_ENV_PATH = getenv("CLUSTER_PYTHON_ENV_PATH")
    CLUSTER_REPO_DIR = getenv("CLUSTER_REPO_DIR")
    CLUSTER_USER = getenv("CLUSTER_USER")
    CLUSTER_MACHINE = getenv("CLUSTER_MACHINE")
    DB_NAME = getenv("DB_NAME")
    DB_HOST_NAME = getenv("DB_HOST_NAME")
    DB_PORT = getenv("DB_PORT")
    DB_USER = getenv("DB_USER")
    DB_PW = getenv("DB_PW")
    DEBUG = getenv("FLASK_DEBUG")
except ValueError as error:
    print("Can not start flask")
    print(error)
    exit(1)
