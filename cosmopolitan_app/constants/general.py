"""General application constants for COSMOPOLITAN."""

# Consecutive failed nightly CRNS update runs before the maintainer is mailed.
# The upstream STA is briefly unavailable during its own maintenance, which used
# to cost one mail every night; three in a row is a real outage worth reporting.
CONSECUTIVE_FAILURES_BEFORE_MAIL = 3

# A nightly update run still marked 'running' after this long was killed at the
# Celery hard time limit (domain.CeleryConfig.task_time_limit, checked by a test)
# and never got to record its end; it counts as failed.
UPDATE_RUN_HARD_LIMIT_SECONDS = 3900

LOG_FILE_NAME = "logs"

# Packages only this app pulls in; their DEBUG output would otherwise fill the logs
# table. Passed to the cosmo_ecosystem logger builders, which add them to their own
# defaults (watchdog, selenium).
EXCLUDED_LOG_PACKAGES = ("matplotlib", "PIL", "rasterio")
