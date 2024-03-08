"""Test .env files for the project."""

import shutil


def test_env_dev_mock():
    """Test .env_dev_mock file."""
    shutil.copy(".env_dev_mock", ".env")
    import cosmopolitan_app.config  # noqa


def test_env_dev_prod():
    """Test .env_dev_prod file."""
    shutil.copy(".env_dev_prod", ".env")
    import cosmopolitan_app.config  # noqa


def test_env_prod():
    """Test .env_prod file."""
    shutil.copy(".env_prod", ".env")
    # Add the following line to .env file
    # EMAIL_PASSWORD="password"
    with open(".env", "a") as f:
        f.write("EMAIL_PASSWORD='password'\n")
        f.write("CLUSTER_TOKEN='password'\n")
        f.write("DB_PW='password'\n")
    import cosmopolitan_app.config  # noqa
