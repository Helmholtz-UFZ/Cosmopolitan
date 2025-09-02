"""Background job manager using Celery for distributed task processing."""

import logging
from logging.config import dictConfig

from celery import Celery
from celery.result import AsyncResult
from celery.signals import worker_process_init

from cosmopolitan_app.celery_config import CeleryConfig
from cosmopolitan_app.config import DEBUG
from cosmopolitan_app.logger import get_logger_config_web
from cosmopolitan_app.tasks.computation_tasks import start_computation_task
from cosmopolitan_app.tasks.maintenance_tasks import cleanup_task, update_db_task


@worker_process_init.connect
def configure_worker_logging(sender=None, conf=None, **kwargs):
    """Configure database logging for Celery worker processes."""
    dictConfig(get_logger_config_web(DEBUG, tag="worker"))


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

    def _setup_periodic_tasks(self):
        """Set up periodic tasks using Celery Beat (replaces APScheduler)."""
        from celery.schedules import crontab

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
        logging.info(
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

        logging.info(result)
        logging.info(
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

    def revoke_job(self, task_id: str, terminate: bool = False) -> bool:
        """Revoke/cancel a running task."""
        try:
            self.app.control.revoke(task_id, terminate=terminate)
            logging.info(
                f"Task {task_id} revoked (terminate={terminate})",
                extra={"tag": "job_submission"},
            )
            return True
        except Exception as e:  # noqa
            logging.error(
                f"Failed to revoke task {task_id}: {e}", extra={"tag": "job_submission"}
            )
            return False


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
