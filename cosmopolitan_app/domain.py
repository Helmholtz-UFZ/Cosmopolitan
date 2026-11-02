"""COSMOPOLITAN's domain module: what the framework needs to assemble a process.

Named by ``COSMO_DOMAIN=cosmopolitan_app.domain`` in every process (web, worker,
CLI). ``cosmo_ecosystem.celery_app`` imports it on first access to the Celery app
and builds that app from the attributes below; see
docs/conventions/domain_module.md in cosmo-ecosystem for the contract.

Importing it also wires ``DbManager.job_table`` (through ``postgres_manager``),
so the worker, which never imports ``app.py``, has it before any task runs. The web process imports it at
the top of ``app.py`` for the same reason. This app has no framework Job seams to
set: its ``Job`` subclasses ``BaseJob`` and submits through
``cosmopolitan_app.submissions`` itself.
"""

from celery.schedules import crontab
from cosmo_ecosystem.celery_config import BaseCeleryConfig
from cosmo_ecosystem.task_spec import BeatEntry, TaskSpec

from cosmopolitan_app.constants.general import EXCLUDED_LOG_PACKAGES

# Imported for its side effect: postgres_manager assigns DbManager.job_table at
# its bottom, once JobTable is defined. It stays there rather than moving here
# because tests and pages reach DbManager through postgres_manager without
# importing this module, and they need the seam too.
import cosmopolitan_app.postgres_manager  # noqa: F401
from cosmopolitan_app.submissions import NAME_COMPUTATION_TASK, NAME_UPDATE_DB_TASK
from cosmopolitan_app.tasks.computation_tasks import start_computation_task
from cosmopolitan_app.tasks.maintenance_tasks import update_db_task


class CeleryConfig(BaseCeleryConfig):
    """Domain Celery settings for COSMOPOLITAN.

    Routes and the beat schedule do not belong here: they come from
    ``task_specs``, and the framework rejects a config that sets either.
    """

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

    # BaseCeleryConfig leaves this at UTC, so crontab(hour=4) fired at 06:00 Berlin
    # in summer — the entry names below were simply wrong, and the pods' own
    # TZ=Europe/Berlin does not reach Beat (Celery schedules in conf.timezone, not
    # in the process timezone). Set here rather than in the framework: the run time
    # of these two jobs is a domain decision, and cosmo-ecosystem has other consumers.
    timezone = "Europe/Berlin"


celery_config = CeleryConfig

task_specs = [
    TaskSpec(
        fn=start_computation_task,
        name=NAME_COMPUTATION_TASK,
        queue="computation",
        base_task=None,
    ),
    TaskSpec(
        fn=update_db_task,
        name=NAME_UPDATE_DB_TASK,
        queue="maintenance",
        base_task=None,
        # The nightly CRNS update, an hour after the framework cleanup (03:00),
        # in the timezone above.
        beat=BeatEntry(schedule=crontab(minute=0, hour=4)),
    ),
]

# matplotlib/PIL/rasterio all run inside worker processes during a prediction;
# see constants/general.py.
excluded_log_packages = EXCLUDED_LOG_PACKAGES

# Log rows older than this are deleted by the framework cleanup.
log_retention_days = 60
