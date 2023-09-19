"""This module defines variables, dir structure and includes widely used functions."""

import os
import subprocess
from time import sleep

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


class SshError(Exception):
    """Raised if ssh call repetidly failed."""

    pass


def ssh_call(call_str):
    """
    Execute an SSH command multiple times with retry logic and capture its output.

    Raises:
    SshError: If the SSH command fails after three attempts, an SshError is
    raised. The error message includes details about the command, stdout, and
    stderr of the last failed attempt.
    """
    ssh_dir = "cluster_api"
    if not os.path.isdir(ssh_dir):
        raise FileNotFoundError(
            f"Directory for ssh-scripts { ssh_dir } is not available"
        )
    call_str = os.path.join(ssh_dir, call_str)

    for i in range(1, 4):
        try:
            completed_process = subprocess.run(
                call_str.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            break
        except subprocess.CalledProcessError as exc:
            if i < 3:
                sleep(2)
                continue
            error_str = (
                f"ERROR ssh call\nCommand\n{call_str}\nstdout:\n"
                f"{exc.stdout.decode('UTF8')}\nstderr:\n{exc.stderr.decode('UTF8')}"
            )
            raise SshError(error_str)

    return completed_process.stdout.decode("UTF8")


DEV_MODE = True

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
except ValueError as error:
    print("Can not start flask")
    print(error)
    exit(1)
