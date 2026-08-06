"""Celery configuration for COSMOPOLITAN background tasks.

Broker, timeouts, serialization and worker limits come from the framework's
`BaseCeleryConfig`. This app adds its computation queue and the nightly CRNS
database update, and replaces the cleanup schedule: the framework's entry points
at `cosmo_suite.tasks.maintenance_tasks.cleanup`, which this app's worker does
not register — its cleanup task lives in `cosmopolitan_app.tasks`.
"""

from celery.schedules import crontab

from cosmo_suite.celery_config import BaseCeleryConfig


class CeleryConfig(BaseCeleryConfig):
    """Celery configuration for COSMOPOLITAN."""

    task_routes = {
        **BaseCeleryConfig.task_routes,
        "cosmopolitan_app.tasks.computation_tasks.*": {"queue": "computation"},
        "cosmopolitan_app.tasks.maintenance_tasks.*": {"queue": "maintenance"},
    }

    # Replaces (not extends) the framework schedule — see module docstring.
    beat_schedule = {
        "cleanup-at-3am": {
            "task": "cosmopolitan_app.tasks.maintenance_tasks.cleanup",
            "schedule": crontab(minute=0, hour=3),
            "options": {"queue": "maintenance"},
        },
        "update-db-at-4am": {
            "task": "cosmopolitan_app.tasks.maintenance_tasks.update_db",
            "schedule": crontab(minute=0, hour=4),
            "options": {"queue": "maintenance"},
        },
    }
