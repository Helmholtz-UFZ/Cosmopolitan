"""Submissions leave the queue to the task specs in cosmopolitan_app.domain."""

from types import SimpleNamespace

import pytest
from cosmo_ecosystem import background_job_manager as manager_module

from cosmopolitan_app import submissions


@pytest.fixture
def sent_tasks(monkeypatch):
    """Capture what submissions hand to Celery, and where the routes send it."""
    real_app = manager_module.background_job_manager.app
    sent = []

    def send_task(name, args, **opts):
        # The router sees what Celery's own send_task passes it: the explicit
        # options (a "queue" among them if the caller set one), then the routes.
        queue = real_app.amqp.router.route(dict(opts), name, args)["queue"].name
        sent.append({"name": name, "opts": opts, "queue": queue})
        return SimpleNamespace(id="task-id")

    redis = SimpleNamespace(set=lambda *args, **kwargs: None)
    fake_app = SimpleNamespace(
        send_task=send_task,
        backend=SimpleNamespace(client=redis),
    )
    monkeypatch.setattr(manager_module.background_job_manager, "app", fake_app)
    return sent


def test_computation_job_goes_to_the_queue_the_task_spec_names(sent_tasks):
    submissions.submit_computation_job(SimpleNamespace(job_id="job-1"))

    [task] = sent_tasks
    assert "queue" not in task["opts"]
    assert task["queue"] == "computation"


def test_update_db_goes_to_the_queue_the_task_spec_names(sent_tasks):
    submissions.submit_update_db_task()

    [task] = sent_tasks
    assert "queue" not in task["opts"]
    assert task["queue"] == "maintenance"
