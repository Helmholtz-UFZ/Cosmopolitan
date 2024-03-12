"""Setup tests."""

import logging
import os
import shutil
import subprocess
import time

import pytest

import docker

print("Conftest is running")

logging.basicConfig(level=logging.INFO)


@pytest.fixture(scope="session", autouse=True)
def start_mock_server():
    """Start the mock server."""
    logging.info("Starting mock server")
    subprocess.Popen("docker compose up".split())
    time.sleep(1)
    client = docker.from_env()
    container_names = ["postgres-local", "cosmopolitan-local", "cosmopolitan-mailhog-1"]

    # Check if all specified containers are running
    while True:
        containers_running = True

        for container in container_names:
            print(container)
            container_info = client.containers.get(container)
            print(container_info.status)
            if container_info.status != "running":
                containers_running = False
                break

        if containers_running:
            logging.info("Mock server are running")
            break

        time.sleep(1)

    yield

    logging.info("Stopping mock server")
    subprocess.run("docker compose down".split())


@pytest.fixture(scope="session", autouse=True)
def set_up_env():
    """Set up env file.

    Save the current .env file and copy .env_dev_mock to .env.
    """
    logging.info("Setting up env file")
    if os.path.exists(".env"):
        shutil.copyfile(".env", ".env_bak")
    shutil.copyfile(".env_test", ".env")

    with open(".env", "r") as file:
        print(file.read())

    yield

    logging.info("Tearing down env file")
    if os.path.exists(".env_bak"):
        shutil.copyfile(".env_bak", ".env")
        os.remove(".env_bak")
    else:
        os.remove(".env")
