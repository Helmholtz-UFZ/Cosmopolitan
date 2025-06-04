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
    "MINIO_URL",
    "MINIO_ACCESS_KEY",
    "MINIO_SECRET_KEY",
    "MINIO_BUCKET",
    "MINIO_ALIAS",
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
DEBUG = getenv("FLASK_DEBUG")
MINIO_URL = getenv("MINIO_URL")
MINIO_ACCESS_KEY = getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = getenv("MINIO_SECRET_KEY")
MINIO_BUCKET = getenv("MINIO_BUCKET")
MINIO_ALIAS = getenv("MINIO_ALIAS")

JOB_WORK_DIR_TEMPLATE = os.path.join(WEB_WORK_DIR, "{job_id}")
