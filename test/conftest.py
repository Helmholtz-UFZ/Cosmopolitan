"""Setup tests."""

import importlib.resources
import logging
import os
import shutil
import signal
import socket
import subprocess
import time
from pathlib import Path

import pytest
from soil_moisture_prediction.create_usage_information import file_exeptions
from sqlalchemy.exc import OperationalError

from cosmopolitan_app.config import (
    EMAIL_PASSWORD,
    OBJECT_STORAGE_REMOTE_NAME,
    OBJECT_STORAGE_SECRET_KEY,
    POSTGRES_PASSWORD,
)
from cosmopolitan_app.object_storage_manager import (
    ObjectStorageError,
    create_bucket,
    setup_remote,
)
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
    subprocess.run(["rclone", "--version"], check=True, text=True, capture_output=True)
except FileNotFoundError:
    pytest.exit("rclone command not available")

try:
    setup_remote()
    subprocess.run(
        ["rclone", "listremotes", OBJECT_STORAGE_REMOTE_NAME + ":"],
        check=True,
        capture_output=True,
    )
    create_bucket()
except ObjectStorageError:
    pytest.exit("Can not set rclone config")

if (
    POSTGRES_PASSWORD != "test"
    or EMAIL_PASSWORD != "test"
    or OBJECT_STORAGE_SECRET_KEY != "secretkey"
):
    pytest.exit("Environment variables not set")

try:
    send_mail("test@example.com", "Test", "Test")
except (ConnectionRefusedError, socket.gaierror, OSError):
    pytest.exit("Mail server not available")

try:
    PostgresManager.check_existence("test")
except OperationalError:
    pytest.exit("postgres not available")

# Check if Celery can connect to PostgreSQL broker
try:
    from cosmopolitan_app.background_job_manager import get_background_job_manager

    # Test Celery broker connection by inspecting active workers
    job_manager = get_background_job_manager()

    # This will raise an exception if broker is not accessible
    job_manager.app.control.inspect().active()

    log.info("Celery broker connection verified")
except (OperationalError, ConnectionError) as e:
    pytest.exit(f"Celery broker connection failed: {e}")

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


@pytest.fixture
def celery_worker():
    """Start a Celery worker for testing job processing."""
    log.info("Starting Celery worker for testing...")

    # Start Celery worker process
    worker_process = subprocess.Popen(
        [
            "poetry",
            "run",
            "celery",
            "-A",
            "cosmopolitan_app.background_job_manager.celery",
            "worker",
            "--loglevel=info",
            "--concurrency=1",
            "--pool=solo",  # Use solo pool for better test isolation
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        preexec_fn=os.setsid,  # Create new process group for clean termination
    )

    # Give worker time to start and connect to broker
    time.sleep(3)

    # Check if worker process is still running (not crashed)
    if worker_process.poll() is not None:
        stdout, stderr = worker_process.communicate()
        pytest.exit(
            f"Celery worker failed to start. stdout: {stdout}, stderr: {stderr}"
        )

    log.info("Celery worker started successfully")

    yield worker_process

    # Cleanup: terminate worker process and all child processes
    log.info("Terminating Celery worker...")
    try:
        # Send SIGTERM to the process group
        os.killpg(os.getpgid(worker_process.pid), signal.SIGTERM)

        # Wait for graceful shutdown
        try:
            worker_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            # Force kill if it doesn't terminate gracefully
            os.killpg(os.getpgid(worker_process.pid), signal.SIGKILL)
            worker_process.wait()

        log.info("Celery worker terminated")
    except ProcessLookupError:
        # Process already terminated
        pass
    except (OSError, subprocess.TimeoutExpired) as e:
        log.warning(f"Error during worker cleanup: {e}")
        # Try one more time with SIGKILL
        try:
            os.killpg(os.getpgid(worker_process.pid), signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass


def pytest_sessionfinish(session, exitstatus):
    """Restore .env file."""
    if os.path.exists("env_test_backup"):
        shutil.copyfile("env_test_backup", ".env")
        os.remove("env_test_backup")
    else:
        os.remove(".env")
