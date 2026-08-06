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

    # v0.4.0 set both to None in BaseCeleryConfig, so they are declared here rather
    # than inherited. Keeping 3600/3900 is the evidenced choice, not inertia: the app
    # has run in production under this limit for a long time, and regionalisation jobs
    # being cut off at 65 minutes would have been noticed. Dropping the limit is the
    # unevidenced change — a runaway task would then pin a worker indefinitely
    # (worker_max_tasks_per_child only recycles after a task finishes).
    #
    # COSMONAUT's reason for removing them does not transfer: its O(n²) routing over
    # large surveys outgrows any fixed bound, whereas random forest with Monte Carlo
    # scales with realisations × predictors and is bounded by the job config itself.
    #
    # To replace inheritance with measurement, the runtimes are already in the
    # database: jobs.start_date against the last log entry per job_id.
    task_soft_time_limit = 3600  # 1 hour
    task_time_limit = 3900  # 65 minutes

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
