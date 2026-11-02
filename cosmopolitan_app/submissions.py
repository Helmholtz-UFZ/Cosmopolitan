"""COSMOPOLITAN's domain submissions: module functions over the framework manager.

Not a manager subclass and nothing mounted on the framework manager (ADR 0003 of
cosmo-ecosystem). ``submit_job`` takes a plain job id and never touches a job
object, so the computation wrapper pulls the id out and passes it. The update_db
task carries no job id at all and stays on ``submit_named_job``.

The task names here are the names the task specs in ``cosmopolitan_app.domain``
register; both sides read them from this module.
"""

import cosmo_ecosystem.background_job_manager

NAME_COMPUTATION_TASK = "cosmopolitan_app.tasks.computation_tasks.start_computation"
NAME_UPDATE_DB_TASK = "cosmopolitan_app.tasks.maintenance_tasks.update_db"


def _manager():
    """Return the framework manager, looked up at call time.

    Binding it with a ``from … import`` at import would assemble the Celery app
    while ``cosmopolitan_app.domain``, which imports this module through
    ``job.py``, is still half-imported.
    """
    return cosmo_ecosystem.background_job_manager.background_job_manager


def submit_computation_job(job) -> tuple[str | None, bool]:
    """Submit a computation job; its task spec in ``domain`` names the queue.

    Args:
        job: Job instance to process

    Returns:
        tuple: (celery_task_id, failed_boolean)
               celery_task_id is None if submission failed
    """
    # track_task_name=True, not left to the framework default: this app has always
    # registered the task name (the pre-Slice-1b code wrote task_name:<id> to
    # Redis itself, and submit_named_job does it unconditionally). Without it a
    # revoked computation task shows up as "Unknown" on the worker page, and a
    # revoked long-running prediction is exactly the case that page exists for.
    return _manager().submit_job(
        NAME_COMPUTATION_TASK,
        job.job_id,
        track_task_name=True,
    )


def submit_update_db_task() -> tuple[str | None, bool]:
    """Submit the update_db task; its task spec in ``domain`` names the queue.

    Returns:
        tuple: (celery_task_id, failed_boolean)
               celery_task_id is None if submission failed
    """
    return _manager().submit_named_job(NAME_UPDATE_DB_TASK)
