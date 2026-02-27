"""Constants for app including settings and component IDs."""

from cosmopolitan_app.constants.html_ids import *  # noqa: F401, F403

# Number of days to keep a submitted job entries in the database
DAYS_DELETE_SUMBITTED = 60
# Number of days to keep an unsubmitted job entries in the database
DAYS_DELETE_NOT_SUMBITTED = 2
# Number of days to keep the logs
LOG_RETENTION_DAYS = 60
