"""Logging configuration: the framework's, plus this app's noisy packages.

`PostgreSQLHandler`, the log format and the three dictConfig builders come from
:mod:`cosmo_suite.logger`. Only the exclusion list differs — this app pulls in
matplotlib, PIL and rasterio, whose debug output would otherwise fill the logs
table.

cosmo_suite v0.3.0 hardcodes the exclusion list inside `ExcludeSubmodulesFilter`
and takes no argument for it, so the domain entries are added by a subclass that
is patched into the config dicts the framework returns. Remove this shim once
the framework accepts the excluded packages as a parameter.
"""

from cosmo_suite.logger import ExcludeSubmodulesFilter
from cosmo_suite.logger import get_logger_config_computation as _framework_computation
from cosmo_suite.logger import get_logger_config_web as _framework_web
from cosmo_suite.logger import get_logger_config_worker as _framework_worker

# Packages only this app depends on; their DEBUG output is not worth persisting.
DOMAIN_EXCLUDED_PACKAGES = ("matplotlib", "PIL", "rasterio")


class ExcludeDomainSubmodulesFilter(ExcludeSubmodulesFilter):
    """Framework filter, extended by the packages only this app pulls in."""

    def filter(self, record):
        """Filter."""
        if record.name.startswith(DOMAIN_EXCLUDED_PACKAGES):
            return False
        return super().filter(record)


def _with_domain_filter(config):
    """Swap in the filter that also mutes this app's noisy packages."""
    config["filters"]["exclude_submodules"]["()"] = ExcludeDomainSubmodulesFilter
    return config


def get_logger_config_computation(log_file_path):
    """Get the config dict for the computation logger."""
    return _with_domain_filter(_framework_computation(log_file_path))


def get_logger_config_web(debug):
    """Get the logging configuration for the web process (Dash/Flask)."""
    return _with_domain_filter(_framework_web(debug))


def get_logger_config_worker():
    """Get the logging configuration for use inside a Celery worker task."""
    return _with_domain_filter(_framework_worker())
