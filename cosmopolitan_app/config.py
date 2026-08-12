"""Configuration: the framework's infrastructure variables plus COSMOPOLITAN's own.

The infrastructure variables (Postgres, Redis, object storage, Flask) are read and
validated by :mod:`cosmo_suite.config` and re-exported here, so domain modules keep a
single config import. Only the CRNS/notification variables below are read here — the
framework has no use for them.
"""

# Re-exported so `from cosmopolitan_app.config import POSTGRES_DB` keeps working:
# these belong to the framework, this module only forwards them.
from cosmo_suite.config import (  # noqa: F401
    DEBUG,
    JOB_WORK_DIR_TEMPLATE,
    OBJECT_STORAGE_ACCESS_KEY,
    OBJECT_STORAGE_BUCKET,
    OBJECT_STORAGE_HOST,
    OBJECT_STORAGE_REMOTE_NAME,
    OBJECT_STORAGE_SECRET_KEY,
    PORT,
    POSTGRES_DB,
    POSTGRES_HOST_NAME,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
    REDIS_DB,
    REDIS_HOST,
    REDIS_PASSWORD,
    REDIS_PORT,
    WEB_OUTSIDE_URL,
    WEB_WORK_DIR,
    getenv,
)
from cosmo_suite.config import env_vars as framework_env_vars

# Variables the framework does not know about. Needed for test_env.py. Update!
domain_env_vars = [
    "TILESERVER_URL",
    "EMAIL_SERVER",
    "EMAIL_PORT",
    "EMAIL_USERNAME",
    "EMAIL_PASSWORD",
    "EMAIL_SENDER",
    "MAINTAINER_EMAIL",
]

env_vars = framework_env_vars + domain_env_vars

TILESERVER_URL = getenv("TILESERVER_URL")
EMAIL_SERVER = getenv("EMAIL_SERVER")
EMAIL_PORT = getenv("EMAIL_PORT")
EMAIL_USERNAME = getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = getenv("EMAIL_PASSWORD")
EMAIL_SENDER = getenv("EMAIL_SENDER")
MAINTAINER_EMAIL = getenv("MAINTAINER_EMAIL")
