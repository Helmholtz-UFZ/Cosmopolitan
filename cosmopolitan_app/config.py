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
    WEB_WORK_DIR = getenv("WEB_WORK_DIR")
    PORT = getenv("FLASK_PORT")
    EMAIL_SERVER = getenv("EMAIL_SERVER")
    EMAIL_PORT = getenv("EMAIL_PORT")
    EMAIL_USERNAME = getenv("EMAIL_USERNAME")
    EMAIL_PASSWORD = getenv("EMAIL_PASSWORD")
    EMAIL_SENDER = getenv("EMAIL_SENDER")
    CLUSTER_WORK_DIR = getenv("CLUSTER_WORK_DIR")
    CLUSTER_LOG_DIR = getenv("CLUSTER_LOG_DIR")
    CLUSTER_PYTHON_ENV_PATH = getenv("CLUSTER_PYTHON_ENV_PATH")
    CLUSTER_COSMOPOLITAN_REPO = getenv("CLUSTER_COSMOPOLITAN_REPO")
    CLUSTER_SM_REPO = getenv("CLUSTER_SM_REPO")
    CLUSTER_USER = getenv("CLUSTER_USER")
    CLUSTER_TOKEN = getenv("CLUSTER_TOKEN")
    CLUSTER_HOST = getenv("CLUSTER_HOST")
    CLUSTER_PORT = getenv("CLUSTER_PORT")
    DB_NAME = getenv("DB_NAME")
    DB_HOST_NAME = getenv("DB_HOST_NAME")
    DB_PORT = getenv("DB_PORT")
    DB_USER = getenv("DB_USER")
    DB_PW = getenv("DB_PW")
    DEBUG = getenv("FLASK_DEBUG")
except ValueError as error:
    print("Can not load config")
    print(error)
    exit(1)

CLUSTER_AUTHORITY = f"{CLUSTER_HOST}:{CLUSTER_PORT}"

slurm_default_parameters = {
    "job": {
        "name": None,
        "ntasks": 1,
        "nodes": 1,
        "partition": None,
        "current_working_directory": CLUSTER_WORK_DIR,
        "standard_input": "/dev/null",
        "standard_output": CLUSTER_WORK_DIR,
        "standard_error": CLUSTER_WORK_DIR,
        "time_limit": "1:00:00",
        "memory_per_cpu": "1G",
        "environment": {
            "PATH": "/usr/local/bin:/usr/bin",
            "PYTHONPATH": f"{CLUSTER_SM_REPO}:{CLUSTER_COSMOPOLITAN_REPO}",
        },
    },
    "script": None,
}

slurm_header = {
    "X-SLURM-USER-NAME": CLUSTER_USER,
    "X-SLURM-USER-TOKEN": CLUSTER_TOKEN,
}

CLUSTER_PYTHON_ENV_TRANSFER_PATH = "/home/soncosmo/py_env_transfer"

COMPUTATION_SCRIPT_TEMPLATE = f"""#!/bin/bash --login
cd { CLUSTER_WORK_DIR }{{job_id}}
module load foss/2022b Python/3.11.2-bare PostgreSQL/15.2
source { CLUSTER_PYTHON_ENV_PATH }/bin/activate
python3 { CLUSTER_SM_REPO }/SM_prediction_main.py -wd { CLUSTER_WORK_DIR }{{job_id}}"""

LOAD_SCRIPT_TEMPLATE = f"""#!/bin/bash --login
module load foss/2022b Python/3.11.2-bare PostgreSQL/15.2
source {CLUSTER_PYTHON_ENV_PATH}/bin/activate
python3 {CLUSTER_COSMOPOLITAN_REPO}/auxilary_scripts/safe_results.py {{job_id}} {{mode}}
"""
