"""Background job manager using Celery for distributed task processing."""

import logging
import time
from logging.config import dictConfig

from celery import Celery
from celery.exceptions import CeleryError
from celery.result import AsyncResult
from celery.schedules import crontab
from celery.signals import worker_process_init

from cosmopolitan_app.celery_config import CeleryConfig
from cosmopolitan_app.logger import get_logger_config_worker
from cosmopolitan_app.tasks.computation_tasks import start_computation_task
from cosmopolitan_app.tasks.maintenance_tasks import cleanup_task, update_db_task
from cosmopolitan_app.tasks.test_tasks import long_running_test_task

log = logging.getLogger(__name__)


@worker_process_init.connect
def configure_worker_logging(sender=None, conf=None, **kwargs):
    """Configure database logging for Celery worker processes."""
    dictConfig(get_logger_config_worker())


class BackgroundJobManager:
    """Centralized manager for all background job operations using Celery."""

    def __init__(self):
        """Initialize the BackgroundJobManager with Celery app."""
        self.app = self._create_celery_app()
        self._register_tasks()
        self._setup_periodic_tasks()

    def _create_celery_app(self) -> Celery:
        """Create and configure the Celery application."""
        app = Celery("cosmopolitan")
        app.config_from_object(CeleryConfig)

        # Update configuration with current instance
        app.conf.update(
            broker_connection_retry_on_startup=True,
            broker_connection_retry=True,
        )

        return app

    def _register_tasks(self):
        """Register all task functions with the Celery app."""
        # Register computation tasks
        self.computation_task = self.app.task(
            bind=True, name="cosmopolitan_app.tasks.computation_tasks.start_computation"
        )(start_computation_task)

        # Register maintenance tasks
        self.cleanup_task = self.app.task(
            bind=True, name="cosmopolitan_app.tasks.maintenance_tasks.cleanup"
        )(cleanup_task)

        self.update_db_task = self.app.task(
            bind=True, name="cosmopolitan_app.tasks.maintenance_tasks.update_db"
        )(update_db_task)

        # Register test tasks
        self.long_running_test_task = self.app.task(
            bind=True, name="cosmopolitan_app.tasks.test_tasks.long_running_test"
        )(long_running_test_task)

    def _setup_periodic_tasks(self):
        """Set up periodic tasks using Celery Beat (replaces APScheduler)."""
        self.app.conf.beat_schedule = {
            "cleanup-at-3am": {
                "task": "cosmopolitan_app.tasks.maintenance_tasks.cleanup",
                "schedule": crontab(minute=0, hour=3),  # Every day at 3:00 AM
                "options": {"queue": "maintenance"},
            },
            "update-db-at-4am": {
                "task": "cosmopolitan_app.tasks.maintenance_tasks.update_db",
                "schedule": crontab(minute=0, hour=4),  # Every day at 4:00 AM
                "options": {"queue": "maintenance"},
            },
        }

    def submit_computation_job(self, job) -> str:
        """Submit a computation job to the Celery queue.

        Args:
            job: Job instance to process

        Returns:
            str: Celery task ID
        """
        log.info(
            f"Submitting computation job {job.job_id} to Celery",
            extra={"tag": "job_submission"},
        )

        # Submit to Celery (pass job_id, not job object)
        result = self.computation_task.apply_async(
            args=[job.job_id],
            queue="computation",
            retry=True,
            retry_policy={
                "max_retries": 3,
                "interval_start": 60,
                "interval_step": 60,
                "interval_max": 300,
            },
        )

        log.info(
            f"Job {job.job_id} submitted with Celery task ID: {result.id}",
            extra={"tag": "job_submission"},
        )

        return result.id, False

    def get_job_status(self, task_id: str) -> dict:
        """Get the status of a Celery task."""
        result = AsyncResult(task_id, app=self.app)

        return {
            "task_id": task_id,
            "status": result.status,
            "result": result.result if result.ready() else None,
            "traceback": result.traceback if result.failed() else None,
            "date_done": result.date_done,
        }

    def get_task_result_info(self, task_id: str) -> dict:
        """Get task name and status from result backend.

        Args:
            task_id: The Celery task ID to look up

        Returns:
            dict: Dictionary with task_name and status, or defaults if not found
        """
        task_name = "Unknown"
        status = "REVOKED"

        try:
            result = AsyncResult(task_id, app=self.app)
            if result.name:
                task_name = result.name.split(".")[-1]
            if result.status:
                status = result.status
        except CeleryError as e:
            log.debug(
                f"Could not get result info for task {task_id}: {e}",
                extra={"tag": "worker"},
            )

        return {"task_name": task_name, "status": status}

    def revoke_job(self, task_id: str, terminate: bool = False) -> None:
        """Revoke/cancel a running task.

        Args:
            task_id: The Celery task ID to revoke
            terminate: If True, send SIGTERM to kill running task process
        """
        self.app.control.revoke(task_id, terminate=terminate)
        log.info(
            f"Task {task_id} revoked (terminate={terminate})",
            extra={"tag": "job_submission"},
        )

    def get_all_tasks_overview(self) -> dict:
        """Get comprehensive overview of all tasks using Celery inspect API.

        Returns:
            dict: Dictionary with task lists grouped by status:
                  - 'active': Currently running tasks
                  - 'reserved': Queued tasks waiting to run
                  - 'scheduled': Tasks scheduled for later execution
                  - 'revoked': Canceled/killed tasks
                  - 'workers': List of online worker names
        """
        inspect = self.app.control.inspect()

        # Get task information from workers
        active = inspect.active() or {}
        reserved = inspect.reserved() or {}
        scheduled = inspect.scheduled() or {}
        revoked = inspect.revoked() or {}

        # Get list of online workers using ping
        ping_result = inspect.ping() or {}
        workers = list(ping_result.keys())

        # Flatten worker-keyed dicts into lists
        def flatten_tasks(worker_dict):
            """Flatten {worker: [tasks]} to [tasks] with worker info."""
            result = []
            for worker, tasks in worker_dict.items():
                for task in tasks:
                    if isinstance(task, dict):
                        task["worker"] = worker
                        result.append(task)
                    else:
                        # Revoked returns just task IDs
                        result.append({"id": task, "worker": worker})
            return result

        return {
            "active": flatten_tasks(active),
            "reserved": flatten_tasks(reserved),
            "scheduled": flatten_tasks(scheduled),
            "revoked": flatten_tasks(revoked),
            "workers": workers,
        }


# Lazy initialization - instance created only when needed
_background_job_manager = None


def get_background_job_manager() -> BackgroundJobManager:
    """Get the global BackgroundJobManager instance (lazy instanziation)."""
    global _background_job_manager
    if _background_job_manager is None:
        _background_job_manager = BackgroundJobManager()
    return _background_job_manager


# Expose the Celery app for the worker command
# Use a function to avoid eager initialization
def make_celery():
    """Create the Celery app for worker use."""
    return get_background_job_manager().app


# Standard Celery app instance for worker command
celery = make_celery()

if __name__ == "__main__":
    # For manual testing of the BackgroundJobManager
    job_manager = get_background_job_manager()
    print("BackgroundJobManager initialized with Celery app:")
    while True:
        overview = job_manager.get_all_tasks_overview()
        print(f"Retrieved task overview: {overview}")
        time.sleep(2)
