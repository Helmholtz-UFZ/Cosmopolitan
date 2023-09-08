import datetime
import os
import json
import subprocess
from time import sleep

DEV_MODE = True
# 0 means silence, 3 is highest level of verbosity
VERBOSE_LEVEL = 3

WORK_DIR = "./"
# Directory where files are first uploaded and then checked
UPLOAD_DIR = os.path.join(WORK_DIR, "upload")
# The directory for the input files that have been validated.
INPUT_DIR = os.path.join(WORK_DIR, "input")
# The directory for the result files.
OUTPUT_DIR = os.path.join(WORK_DIR, "output")

with open("./parameters_email_local.json", "r", encoding="UTF-8") as f_handle:
    PARAMETERS_EMAIL = json.load(f_handle)

SMTP_SERVER = PARAMETERS_EMAIL["smtp_server"]
SMTP_PORT = PARAMETERS_EMAIL["smtp_port"]
SMTP_USERNAME = PARAMETERS_EMAIL["smtp_username"]
SMTP_PASSWORD = PARAMETERS_EMAIL["smtp_password"]
SENDER_EMAIL = PARAMETERS_EMAIL["sender_email"]

with open("./parameters_db_local.json", "r", encoding="UTF-8") as f_handle:
    PARAMETERS_DB = json.load(f_handle)

DB_NAME = PARAMETERS_DB["db_name"]
DB_HOST_NAME = PARAMETERS_DB["db_host_name"]
DB_PORT = PARAMETERS_DB["db_port"]
DB_USER = PARAMETERS_DB["db_user"]
DB_PW = PARAMETERS_DB["db_pw"]

with open("./parameters_cluster_local.json", "r", encoding="UTF-8") as f_handle:
    PARAMETERS_CLUSTER = json.load(f_handle)

WORK_DIR_CLUSTER = PARAMETERS_CLUSTER["work_dir"]
PYTHON_ENV_PATH_CLUSTER = PARAMETERS_CLUSTER["python_env_path"]
REPO_DIR_CLUSTER = PARAMETERS_CLUSTER["repo_dir"]
USER_CLUSTER = PARAMETERS_CLUSTER["user"]
MACHINE_CLUSTER = PARAMETERS_CLUSTER["machine"]


def check_verbose_level(verbose_level):
    """Check if verbose level is in correct form."""
    if not isinstance(verbose_level, int):
        raise ValueError("verbose level must be an integer")
    if 0 > verbose_level > 3:
        raise ValueError("verbose level must be between 0 and 3")


def vprint(msg, verbose_level=0):
    """Print to verbose."""
    check_verbose_level(verbose_level)
    msg = datetime.datetime.today().strftime("[%d/%b/%Y %H:%M:%S] - - ") + str(msg)
    if verbose_level <= VERBOSE_LEVEL:
        if DEV_MODE:
            print(msg)
        else:
            # TODO Logging
            raise NotImplementedError


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
        raise FileNotFoundError(f"Directory for ssh-scripts { ssh_dir } is not available")
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
