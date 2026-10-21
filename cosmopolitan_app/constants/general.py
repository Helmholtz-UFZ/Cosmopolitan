"""General application constants for COSMOPOLITAN."""

# Number of days to keep the logs
LOG_RETENTION_DAYS = 60

# Consecutive failed nightly CRNS update runs before the maintainer is mailed.
# The upstream STA is briefly unavailable during its own maintenance, which used
# to cost one mail every night; three in a row is a real outage worth reporting.
CONSECUTIVE_FAILURES_BEFORE_MAIL = 3

LOG_FILE_NAME = "logs"

# Packages only this app pulls in; their DEBUG output would otherwise fill the logs
# table. Passed to the cosmo_ecosystem logger builders, which add them to their own
# defaults (watchdog, selenium).
EXCLUDED_LOG_PACKAGES = ("matplotlib", "PIL", "rasterio")
