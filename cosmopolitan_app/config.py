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

try:
    # s/=.*//g |'<,'> s/^.*$/& = getenv("&")/g | noh
    WEB_UPLOAD_DIR = getenv("WEB_UPLOAD_DIR")
    WEB_WORK_DIR = getenv("WEB_WORK_DIR")
    DAYS_DELETE_NOT_SUMBITTED = int(getenv("DAYS_DELETE_NOT_SUMBITTED"))
    DAYS_DELETE_SUMBITTED = int(getenv("DAYS_DELETE_SUMBITTED"))
    EMAIL_SERVER = getenv("EMAIL_SERVER")
    EMAIL_PORT = getenv("EMAIL_PORT")
    EMAIL_USERNAME = getenv("EMAIL_USERNAME")
    EMAIL_PASSWORD = getenv("EMAIL_PASSWORD")
    EMAIL_SENDER = getenv("EMAIL_SENDER")
    CLUSTER_WORK_DIR = getenv("CLUSTER_WORK_DIR")
    CLUSTER_PYTHON_ENV_PATH = getenv("CLUSTER_PYTHON_ENV_PATH")
    CLUSTER_COSMOPOLITAN_REPO = getenv("CLUSTER_COSMOPOLITAN_REPO")
    CLUSTER_SM_REPO = getenv("CLUSTER_SM_REPO")
    CLUSTER_USER = getenv("CLUSTER_USER")
    CLUSTER_MACHINE = getenv("CLUSTER_MACHINE")
    CLUSTER_TOKEN = getenv("CLUSTER_TOKEN")
    CLUSTER_BASE_URL = getenv("CLUSTER_BASE_URL")
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


slurm_default_parameters = {
    "job": {
        "name": None,
        "ntasks": 1,
        "nodes": 1,
        "partition": "rocky-9",
        "current_working_directory": CLUSTER_WORK_DIR,
        "standard_input": "/dev/null",
        "standard_output": CLUSTER_WORK_DIR,
        "standard_error": CLUSTER_WORK_DIR,
        "time_limit": "1:00:00",
        "memory_per_cpu": "1G",
        "environment": {
            "PATH": "/usr/local/bin:/usr/bin",
            "PYTHONPATH": CLUSTER_SM_REPO,
        },
    },
    "script": None,
}

slurm_header = {
    "X-SLURM-USER-NAME": CLUSTER_USER,
    "X-SLURM-USER-TOKEN": CLUSTER_TOKEN,
}


COMPUTATION_SCRIPT_TEMPLATE = f"""#!/bin/bash --login
mkdir { CLUSTER_WORK_DIR }{{job_id}}
cd { CLUSTER_WORK_DIR }{{job_id}}
module load foss/2022b Python/3.10.8
source { CLUSTER_PYTHON_ENV_PATH }/bin/activate
python3 { CLUSTER_COSMOPOLITAN_REPO }/SM_prediction_main.py -wd { CLUSTER_WORK_DIR }{{job_id}}"""  # noqa
