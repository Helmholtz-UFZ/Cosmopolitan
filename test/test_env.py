"""Test .env files for the project."""

import logging
import os
import shutil

from dotenv import load_dotenv

from cosmopolitan_app.config import env_vars, getenv


def test_env_dev_mock(logger):
    """Test .env_dev_mock file."""
    shutil.copy(".env_dev_mock", ".env")
    # Remove the env_vars from the environment
    for env_var in env_vars:
        os.environ.pop(env_var, None)
    # Reload the .env file
    load_dotenv(override=True)

    for env_var in env_vars:
        logger.info(f"Testing {env_var}")
        logging.info(getenv(env_var))


def test_env_dev_prod(logger):
    """Test .env_dev_prod file."""
    shutil.copy(".env_dev_prod", ".env")
    # Remove the env_vars from the environment
    for env_var in env_vars:
        os.environ.pop(env_var, None)
    # Reload the .env file
    load_dotenv(override=True)

    for env_var in env_vars:
        logger.info(f"Testing {env_var}")
        logging.info(getenv(env_var))


def test_env_prod(logger):
    """Test .env_prod file."""
    shutil.copy(".env_prod", ".env")
    # Add the following line to .env file
    # EMAIL_PASSWORD="password"
    with open(".env", "a") as f:
        f.write("EMAIL_PASSWORD='password'\n")
        f.write("CLUSTER_TOKEN='password'\n")
        f.write("POSTGRES_PW='password'\n")
        f.write("MINIO_ACCESS_KEY='password'\n")
        f.write("MINIO_SECRET_KEY='password'\n")

    # Remove the env_vars from the environment
    for env_var in env_vars:
        os.environ.pop(env_var, None)
    # Reload the .env file
    load_dotenv(override=True)

    for env_var in env_vars:
        logger.info(f"Testing {env_var}")
        logging.info(getenv(env_var))
