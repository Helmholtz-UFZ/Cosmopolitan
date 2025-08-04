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


load_dotenv()

# Needed for the test_env.py. Update!
env_vars = [
    "WEB_WORK_DIR",
    "WEB_OUTSIDE_URL",
    "FLASK_PORT",
    "EMAIL_SERVER",
    "EMAIL_PORT",
    "EMAIL_USERNAME",
    "EMAIL_PASSWORD",
    "EMAIL_SENDER",
    "POSTGRES_DB",
    "POSTGRES_HOST_NAME",
    "POSTGRES_PORT",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "FLASK_DEBUG",
    "OBJECT_STORAGE_HOST",
    "OBJECT_STORAGE_ACCESS_KEY",
    "OBJECT_STORAGE_SECRET_KEY",
    "OBJECT_STORAGE_BUCKET",
    "OBJECT_STORAGE_REMOTE_NAME",
    "MAINTAINER_EMAIL",
]

# s/=.*//g |'<,'> s/^.*$/& = getenv("&")/g | noh
WEB_WORK_DIR = getenv("WEB_WORK_DIR")
WEB_OUTSIDE_URL = getenv("WEB_OUTSIDE_URL")
PORT = getenv("FLASK_PORT")
EMAIL_SERVER = getenv("EMAIL_SERVER")
EMAIL_PORT = getenv("EMAIL_PORT")
EMAIL_USERNAME = getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = getenv("EMAIL_PASSWORD")
EMAIL_SENDER = getenv("EMAIL_SENDER")
POSTGRES_DB = getenv("POSTGRES_DB")
POSTGRES_HOST_NAME = getenv("POSTGRES_HOST_NAME")
POSTGRES_PORT = getenv("POSTGRES_PORT")
POSTGRES_USER = getenv("POSTGRES_USER")
POSTGRES_PASSWORD = getenv("POSTGRES_PASSWORD")
DEBUG = getenv("FLASK_DEBUG") == "1"
OBJECT_STORAGE_HOST = getenv("OBJECT_STORAGE_HOST")
OBJECT_STORAGE_ACCESS_KEY = getenv("OBJECT_STORAGE_ACCESS_KEY")
OBJECT_STORAGE_SECRET_KEY = getenv("OBJECT_STORAGE_SECRET_KEY")
OBJECT_STORAGE_BUCKET = getenv("OBJECT_STORAGE_BUCKET")
OBJECT_STORAGE_REMOTE_NAME = getenv("OBJECT_STORAGE_REMOTE_NAME")
MAINTAINER_EMAIL = getenv("MAINTAINER_EMAIL")

JOB_WORK_DIR_TEMPLATE = os.path.join(WEB_WORK_DIR, "{job_id}")
