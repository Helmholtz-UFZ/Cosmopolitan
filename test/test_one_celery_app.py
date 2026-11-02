"""Guardrail: a web process holds exactly one Celery app, the framework's.

Runs in a fresh interpreter: Celery keeps every app ever built in a process-wide
registry, and this session builds its own. The app is imported with all framework
pages, as the web server does, so a page or job module that builds a second
instance shows up here.
"""

import json
import subprocess
import sys

from cosmo_ecosystem.celery_app import NAME_CLEANUP_TASK

from cosmopolitan_app.submissions import NAME_COMPUTATION_TASK, NAME_UPDATE_DB_TASK

SUBPROCESS_TIMEOUT = 120  # seconds; importing the app takes a few

REPORT = """
import json

from celery import _state

import cosmopolitan_app.app  # imports every framework page
from cosmo_ecosystem.background_job_manager import background_job_manager

# Private API, on purpose: Celery offers no public way to count the apps alive in a
# process, and counting them is the whole point of this guardrail.
apps = list(_state._get_active_apps())
conf = background_job_manager.app.conf
print(json.dumps({
    "count": len(apps),
    "is_managers": apps[0] is background_job_manager.app,
    "routes": conf.task_routes,
    "timezone": conf.timezone,
    "time_limits": [conf.task_soft_time_limit, conf.task_time_limit],
    "beat": {
        name: {
            "hour": sorted(entry["schedule"].hour),
            "minute": sorted(entry["schedule"].minute),
            "queue": entry["options"]["queue"],
        }
        for name, entry in conf.beat_schedule.items()
    },
}))
"""


def _report():
    """Import the web app in a fresh interpreter and report its Celery state."""
    result = subprocess.run(
        [sys.executable, "-c", REPORT],
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_TIMEOUT,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_web_process_holds_one_celery_app_with_the_domain_settings():
    report = _report()

    assert report["count"] == 1
    assert report["is_managers"]
    # The web process routes the domain tasks too, not only the worker.
    assert report["routes"][NAME_COMPUTATION_TASK] == {"queue": "computation"}
    assert report["routes"][NAME_UPDATE_DB_TASK] == {"queue": "maintenance"}
    assert report["timezone"] == "Europe/Berlin"
    assert report["time_limits"] == [3600, 3900]


def test_beat_runs_cleanup_at_three_and_update_db_at_four_berlin_time():
    report = _report()

    assert report["beat"] == {
        NAME_CLEANUP_TASK: {"hour": [3], "minute": [0], "queue": "maintenance"},
        NAME_UPDATE_DB_TASK: {"hour": [4], "minute": [0], "queue": "maintenance"},
    }
    assert report["timezone"] == "Europe/Berlin"
