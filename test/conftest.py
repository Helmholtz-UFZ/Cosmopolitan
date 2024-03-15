"""Setup tests."""

import logging
import os
import shutil
import subprocess
import time

import pytest

import docker

logging.basicConfig(level=logging.INFO)


def start_mock_server():
    """Start the mock server."""
    logging.info("Starting mock server")
    subprocess.Popen("docker compose up".split())
    time.sleep(120)
    client = docker.from_env()
    container_names = ["postgres-local", "cosmopolitan-local", "cosmopolitan-mailhog-1"]

    # Check if all specified containers are running
    while True:
        containers_running = True

        for container in container_names:
            container_info = client.containers.get(container)
            if container_info.status != "running":
                containers_running = False
                break

        if containers_running:
            logging.info("Mock server are running")
            break

        time.sleep(1)

    logging.info("Stopping mock server")
    subprocess.run(
        "docker compose down".split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


@pytest.fixture(scope="session", autouse=True)
def set_up_env():
    """Set up env file.

    Save the current .env file and copy .env_dev_mock to .env.
    """
    logging.info("Setting up env file")
    if os.path.exists(".env"):
        shutil.copyfile(".env", ".env_bak")
    shutil.copyfile(".env_test", ".env")

    yield

    logging.info("Tearing down env file")
    if os.path.exists(".env_bak"):
        shutil.copyfile(".env_bak", ".env")
        os.remove(".env_bak")
    else:
        os.remove(".env")


if __name__ == "__main__":
    logging.info("Running mock server.")
    start_mock_server()
