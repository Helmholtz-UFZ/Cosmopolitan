"""Background job manager for COSMOPOLITAN.

Extends ``cosmo_suite.background_job_manager.BackgroundJobManager``: the generic
plumbing (``submit_named_job``, ``get_job_status``, ``get_task_result_info``,
``get_all_tasks_overview``, ``revoke_job``, ``submit_test_task``) comes from the
framework; only the domain submissions are added here.

Task registration lives in celery_app.py (the worker entry point) to avoid a
circular import: tasks/*.py → job → this module → tasks/*.py.
"""

import logging
from logging.config import dictConfig

from celery.signals import worker_process_init
from cosmo_suite.background_job_manager import NAME_TEST_TASK as NAME_TEST_TASK
from cosmo_suite.background_job_manager import (
    BackgroundJobManager as BaseBackgroundJobManager,
)
from cosmo_suite.background_job_manager import (
    configure_worker_logging as framework_configure_worker_logging,
)

from cosmopolitan_app.celery_config import CeleryConfig
from cosmopolitan_app.logger import get_logger_config_worker

log = logging.getLogger(__name__)

# The framework module connects its own worker_process_init handler on import.
# Both would run and the last one would win, i.e. the effective worker logging
# config would depend on import order. Disconnect it explicitly: this app needs
# its own excluded-packages list (matplotlib/PIL/rasterio all run inside worker
# processes during a prediction), see logger.py.
worker_process_init.disconnect(framework_configure_worker_logging)


@worker_process_init.connect
def configure_worker_logging(sender=None, conf=None, **kwargs):
    """Configure database logging for Celery worker processes."""
    dictConfig(get_logger_config_worker())


NAME_COMPUTATION_TASK = "cosmopolitan_app.tasks.computation_tasks.start_computation"
NAME_CLEANUP_TASK = "cosmopolitan_app.tasks.maintenance_tasks.cleanup"
NAME_UPDATE_DB_TASK = "cosmopolitan_app.tasks.maintenance_tasks.update_db"


class BackgroundJobManager(BaseBackgroundJobManager):
    """Cosmopolitan's job manager: framework plumbing + the domain submissions."""

    def __init__(self):
        """Build the framework manager, then re-point it at this app's config."""
        super().__init__()
        # CeleryConfig subclasses BaseCeleryConfig, so this only adds the domain
        # queues and beat schedule. The Celery app's own name stays the
        # framework's; every task here is registered with an explicit name, so
        # nothing is auto-named from it.
        self.app.config_from_object(CeleryConfig)

    def submit_computation_job(self, job) -> tuple[str | None, bool]:
        """Submit a computation job to the Celery queue.

        Args:
            job: Job instance to process

        Returns:
            tuple: (celery_task_id, failed_boolean)
                   celery_task_id is None if submission failed
        """
        return self.submit_named_job(
            NAME_COMPUTATION_TASK,
            args=[job.job_id],
            queue="computation",
        )

    def submit_update_db_task(self) -> tuple[str | None, bool]:
        """Submit the update_db maintenance task to the Celery queue.

        Returns:
            tuple: (celery_task_id, failed_boolean)
                   celery_task_id is None if submission failed
        """
        return self.submit_named_job(NAME_UPDATE_DB_TASK, queue="maintenance")

    def submit_cleanup_task(self) -> tuple[str | None, bool]:
        """Submit this app's maintenance cleanup task.

        Overrides the framework method, which submits
        ``cosmo_suite.tasks.maintenance_tasks.cleanup`` — that task cleans up via
        cosmo_suite.db_manager, which this app does not use.
        """
        return self.submit_named_job(NAME_CLEANUP_TASK, queue="default")


_background_job_manager = None


def __getattr__(name):
    """Lazy singleton — BackgroundJobManager is created on first access, not on import."""  # noqa
    global _background_job_manager
    if name == "background_job_manager":
        if _background_job_manager is None:
            _background_job_manager = BackgroundJobManager()
        return _background_job_manager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
