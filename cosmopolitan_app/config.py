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
CLUSTER_WORK_DIR = getenv("CLUSTER_WORK_DIR")
CLUSTER_LOG_DIR = getenv("CLUSTER_LOG_DIR")
CLUSTER_PYTHON_ENV_PATH = getenv("CLUSTER_PYTHON_ENV_PATH")
CLUSTER_COSMOPOLITAN_REPO = getenv("CLUSTER_COSMOPOLITAN_REPO")
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
            "PYTHONPATH": CLUSTER_COSMOPOLITAN_REPO,
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
module load foss/2022b Python/3.11.2-bare PostgreSQL/15.2
export PYTHONPATH={ CLUSTER_COSMOPOLITAN_REPO }
source { CLUSTER_PYTHON_ENV_PATH }/bin/activate
python -m soil_moisture_prediction.smp_cli -w { CLUSTER_WORK_DIR }{{job_id}}"""

transfer_script = (
    f"{CLUSTER_COSMOPOLITAN_REPO}/cosmopolitan_app/backend_util/safe_results.py"
)
LOAD_SCRIPT_TEMPLATE = f"""#!/bin/bash --login
module load foss/2022b Python/3.11.2-bare PostgreSQL/15.2
export PYTHONPATH={ CLUSTER_COSMOPOLITAN_REPO }
source {CLUSTER_PYTHON_ENV_PATH}/bin/activate
python3 {transfer_script} {{job_id}} {{mode}}
"""
