"""Test .env files for the project."""

import os
import shutil


def test_env_dev_mock():
    """Test .env_dev_mock file."""
    # Save the current .env file
    if os.path.exists(".env"):
        shutil.copyfile(".env", ".env_test_backup")

    shutil.copy(".env_dev_mock", ".env")
    import cosmopolitan_app.config  # noqa

    # Restore the .env file or remove it
    if os.path.exists(".env_test_backup"):
        shutil.copyfile(".env_test_backup", ".env")
        os.remove(".env_test_backup")
    else:
        os.remove(".env")


def test_env_dev_prod():
    """Test .env_dev_prod file."""
    # Save the current .env file
    if os.path.exists(".env"):
        shutil.copyfile(".env", ".env_test_backup")

    shutil.copy(".env_dev_prod", ".env")
    import cosmopolitan_app.config  # noqa

    # Restore the .env file or remove it
    if os.path.exists(".env_test_backup"):
        shutil.copyfile(".env_test_backup", ".env")
        os.remove(".env_test_backup")
    else:
        os.remove(".env")


def test_env_prod():
    """Test .env_prod file."""
    # Save the current .env file
    if os.path.exists(".env"):
        shutil.copyfile(".env", ".env_test_backup")

    shutil.copy(".env_prod", ".env")
    # Add the following line to .env file
    # EMAIL_PASSWORD="password"
    with open(".env", "a") as f:
        f.write("EMAIL_PASSWORD='password'\n")
        f.write("CLUSTER_TOKEN='password'\n")
        f.write("DB_PW='password'\n")
    import cosmopolitan_app.config  # noqa

    # Restore the .env file or remove it
    if os.path.exists(".env_test_backup"):
        shutil.copyfile(".env_test_backup", ".env")
        os.remove(".env_test_backup")
    else:
        os.remove(".env")
