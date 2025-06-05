"""Setup tests."""

import importlib.resources
import logging
import os
import shutil
import socket
import subprocess
from pathlib import Path

import pytest
from soil_moisture_prediction.create_usage_information import file_exeptions
from sqlalchemy.exc import OperationalError

from cosmopolitan_app.config import EMAIL_PASSWORD, MINIO_ALIAS, POSTGRES_PASSWORD
from cosmopolitan_app.minio_manager import MinioError, create_bucket
from cosmopolitan_app.postgres_manager import PostgresManager
from cosmopolitan_app.utils import send_mail


def create_logger():
    """Create a logger with debug level."""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logging.getLogger("matplotlib").setLevel(logging.CRITICAL)
    logging.getLogger("PIL").setLevel(logging.CRITICAL)
    logging.getLogger("osgeo").setLevel(logging.ERROR)
    logging.getLogger("rasterio").setLevel(logging.ERROR)
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    logging.getLogger("requests").setLevel(logging.ERROR)
    logging.getLogger("wcs201").setLevel(logging.ERROR)
    return logger


log = create_logger()

try:
    subprocess.run(["mc", "-v"], check=True, text=True, capture_output=True)
except FileNotFoundError:
    pytest.exit("mc command not available")

try:
    create_bucket(reset_alias=True)
    subprocess.run(["mc", "ping", "-x", MINIO_ALIAS], check=True, capture_output=True)
except MinioError:
    pytest.exit("Can not set mc alias")

if any(var != "test" for var in [POSTGRES_PASSWORD, EMAIL_PASSWORD, MINIO_ALIAS]):
    pytest.exit("Environment variables not set")

try:
    send_mail("test@example.com", "Test", "Test")
except (ConnectionRefusedError, socket.gaierror):
    pytest.exit("Mail server not available")

try:
    PostgresManager.check_existence("test")
except OperationalError:
    pytest.exit("postgres not available")


# Save the current .env file
if os.path.exists(".env"):
    shutil.copyfile(".env", "env_test_backup")


@pytest.fixture
def logger():
    """Create a logger with suppressed external sources."""
    return create_logger()


def iterate_test_data():
    """Yield the file paths of the test data.

    Yields:
        str: Full path of a file in the 'test_data' directory.
    """
    package = importlib.import_module("soil_moisture_prediction")
    test_data_dir = importlib.resources.files(package) / "test_data"

    for file_path in test_data_dir.iterdir():
        if file_path.is_file() and file_path.name not in file_exeptions:
            yield file_path


def find_test_data_by_substring(substr):
    """Get the file paths of the test data that contain a specific substring."""
    for file_path in iterate_test_data():
        if substr in file_path.name:
            return file_path
    raise FileNotFoundError(
        f"No test data file found containing substring '{substr}' in the name."
    )


@pytest.fixture
def crns_file_path():
    """Fixture that creates a local copy of the CRNS test data file."""
    original_file = find_test_data_by_substring("crn")

    local_filename = "test_crns_data.csv"
    local_file_path = Path.cwd() / local_filename

    shutil.copy2(original_file, local_file_path)

    yield local_file_path.absolute()

    if local_file_path.exists():
        local_file_path.unlink()


@pytest.fixture
def pred_file_paths():
    """Fixture that creates a local copy for all predictor test files."""
    pred_files = [
        "predictor_1.csv",
        "predictor_2.csv",
        "predictor_3.csv",
        "predictor_4.csv",
    ]

    file_paths = []
    for file_name in pred_files:
        original_file = find_test_data_by_substring(file_name)
        local_file_path = Path.cwd() / file_name
        file_paths.append(local_file_path.absolute())

        shutil.copy2(original_file, local_file_path)

    yield file_paths

    for file_name in pred_files:
        local_file_path = Path.cwd() / file_name
        if local_file_path.exists():
            local_file_path.unlink()


def pytest_sessionfinish(session, exitstatus):
    """Restore .env file."""
    if os.path.exists("env_test_backup"):
        shutil.copyfile("env_test_backup", ".env")
        os.remove("env_test_backup")
    else:
        os.remove(".env")
