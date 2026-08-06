"""Celery application with task registration.

This module creates the Celery worker entry point by importing the shared
Celery app and registering all task functions. The worker command points here:

    celery -A cosmopolitan_app.celery_app.celery worker ...

Separated from background_job_manager to break a circular import:
    tasks/*.py → job → background_job_manager → tasks/*.py
"""

from cosmo_suite.tasks.test_tasks import long_running_test_task

from cosmopolitan_app.background_job_manager import (
    NAME_CLEANUP_TASK,
    NAME_COMPUTATION_TASK,
    NAME_TEST_TASK,
    NAME_UPDATE_DB_TASK,
    background_job_manager,
)
from cosmopolitan_app.tasks.computation_tasks import start_computation_task
from cosmopolitan_app.tasks.maintenance_tasks import cleanup_task, update_db_task

app = background_job_manager.app

app.task(bind=True, name=NAME_COMPUTATION_TASK)(start_computation_task)
app.task(bind=True, name=NAME_CLEANUP_TASK)(cleanup_task)
app.task(bind=True, name=NAME_UPDATE_DB_TASK)(update_db_task)
# Body and name both come from the framework: NAME_TEST_TASK is re-exported from
# cosmo_suite, so what the inherited submit_test_task() sends is what the worker
# has registered. Submitted to the "test" queue, which the worker must consume.
app.task(bind=True, name=NAME_TEST_TASK)(long_running_test_task)

# Expose for: celery -A cosmopolitan_app.celery_app.celery worker ...
celery = app
