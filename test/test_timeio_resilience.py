"""Tests for the TimeIO retry ladder and the throttled maintenance error mail.

Regression cover for the nightly "404 Client Error ... /Things?$select=id,name"
mail: the upstream STA (a FROST webapp behind Tomcat) answers 404 while its
context is unavailable, which used to abort the whole run and mail every night.
"""

import logging
from datetime import date, datetime, timedelta
from unittest.mock import Mock, call, patch

import pytest
import requests
from celery.exceptions import SoftTimeLimitExceeded
from requests.exceptions import HTTPError, ReadTimeout

import cosmopolitan_app.tasks.maintenance_tasks as maintenance_tasks
import cosmopolitan_app.timeio_manager as timeio_manager
from cosmopolitan_app.constants import (
    CONSECUTIVE_FAILURES_BEFORE_MAIL,
    UPDATE_RUN_HARD_LIMIT_SECONDS,
)
from cosmopolitan_app.domain import CeleryConfig
from cosmopolitan_app.error_handling import (
    CrnsUpdateIncomplete,
    TimeIODayError,
    TimeIOUnavailableError,
)
from cosmopolitan_app.postgres_manager import PostgresManager, UpdateDbRuns
from cosmopolitan_app.timeio_manager import TimeIOManager

QUERY = "http://timeio.invalid/v1.1/Things"


def _response(status_code, body='{"value": []}'):
    """Build a requests.Response double that raises like the real one."""
    response = Mock()
    response.status_code = status_code
    response.text = body
    response.json.return_value = {"value": [{"@iot.id": 1, "name": "CRNS - Test"}]}

    def raise_for_status():
        if status_code >= 400:
            raise HTTPError(f"{status_code} Client Error", response=response)

    response.raise_for_status = raise_for_status
    return response


def test_request_data_retries_then_raises_domain_error():
    """A permanently unavailable upstream exhausts the ladder exactly once."""
    with (
        patch.object(requests, "get", return_value=_response(404)) as get,
        patch("cosmopolitan_app.timeio_manager.sleep") as sleep,
    ):
        with pytest.raises(TimeIOUnavailableError) as excinfo:
            list(TimeIOManager.request_data(QUERY))

    # One attempt per delay, plus the initial one.
    assert get.call_count == len(TimeIOManager.retry_delays) + 1
    assert [call.args[0] for call in sleep.call_args_list] == list(
        TimeIOManager.retry_delays
    )
    assert excinfo.value.query == QUERY
    # The HTTPError is chained, so the traceback still names the status.
    assert isinstance(excinfo.value.__cause__, HTTPError)


def test_request_data_recovers_when_upstream_comes_back():
    """A transient outage must not cost the run — this is the incident itself."""
    responses = [_response(404), _response(404), _response(200)]
    with (
        patch.object(requests, "get", side_effect=responses) as get,
        patch("cosmopolitan_app.timeio_manager.sleep"),
    ):
        items = list(TimeIOManager.request_data(QUERY))

    assert get.call_count == 3
    assert [item["@iot.id"] for _query, item in items] == [1]


def test_request_data_survives_a_timeout_without_a_response():
    """ReadTimeout carries no .response; reading the status must not crash."""
    with (
        patch.object(requests, "get", side_effect=ReadTimeout("timed out")),
        patch("cosmopolitan_app.timeio_manager.sleep"),
    ):
        with pytest.raises(TimeIOUnavailableError):
            list(TimeIOManager.request_data(QUERY))


@pytest.mark.parametrize(
    "consecutive_failures, mail_expected",
    [
        (1, False),
        (CONSECUTIVE_FAILURES_BEFORE_MAIL - 1, False),
        (CONSECUTIVE_FAILURES_BEFORE_MAIL, True),
    ],
)
def test_update_db_task_mails_only_after_repeated_failures(
    consecutive_failures, mail_expected
):
    """One bad night is logged; a persistent outage still reaches the maintainer."""
    with (
        patch.object(
            maintenance_tasks,
            "update_crns_measurments",
            side_effect=TimeIOUnavailableError(QUERY),
        ),
        patch.object(
            maintenance_tasks.PostgresManager, "create_update_run", return_value=1
        ),
        patch.object(maintenance_tasks.PostgresManager, "complete_update_run") as done,
        patch.object(
            maintenance_tasks.PostgresManager,
            "count_consecutive_failed_update_runs",
            return_value=consecutive_failures,
        ),
        patch.object(maintenance_tasks, "send_mail") as send_mail,
    ):
        maintenance_tasks.update_db_task(None)

    # The run is always recorded as failed, whether or not it was mailed.
    done.assert_called_once_with(1, "failed")
    assert send_mail.called is mail_expected
    if mail_expected:
        assert str(consecutive_failures) in send_mail.call_args.args[1]


DAY_ONE = date(2024, 1, 1)
DAY_TWO = date(2024, 1, 2)
THING = {"@iot.id": 1, "name": "CRNS - Test"}


@pytest.fixture
def two_day_update():
    """Patch the update's database bookkeeping for a two-day range; yield the recorder.

    The yielded mock is ``add_update_crns``: its calls are the days the run recorded.
    """
    manager = timeio_manager.PostgresManager
    with (
        patch.object(manager, "get_crns_date_range", return_value=(DAY_ONE, DAY_TWO)),
        patch.object(TimeIOManager, "check_things"),
        patch.object(
            manager,
            "get_earliest_missing_or_failed_date",
            return_value=DAY_ONE,
        ),
        patch.object(manager, "was_update_successful", return_value=False),
        patch.object(manager, "add_update_crns") as recorded,
    ):
        yield recorded


def test_the_soft_time_limit_is_not_swallowed_by_the_day_loop(two_day_update):
    """The soft limit ends the run at once; the next day is not started."""
    with patch.object(
        timeio_manager, "transfer_data_by_day", side_effect=SoftTimeLimitExceeded()
    ) as transfer:
        with pytest.raises(SoftTimeLimitExceeded):
            timeio_manager.update_crns_measurments()

    assert transfer.call_count == 1
    # The interrupted day is neither a success nor a finished failure.
    two_day_update.assert_not_called()


def test_a_failed_day_is_recorded_and_fails_the_run_after_the_other_days(
    two_day_update, caplog
):
    """One bad day does not stop the loop, but the run does not end as a success."""
    with (
        patch.object(
            timeio_manager,
            "transfer_data_by_day",
            side_effect=[TimeIODayError("no location"), None],
        ),
        caplog.at_level(logging.ERROR),
    ):
        with pytest.raises(CrnsUpdateIncomplete) as excinfo:
            timeio_manager.update_crns_measurments()

    assert excinfo.value.failed_days == [DAY_ONE]
    assert two_day_update.call_args_list == [
        call(datetime(2024, 1, 1), False),
        call(datetime(2024, 1, 2)),
    ]
    assert "no location" in caplog.text


def test_an_unexpected_error_on_a_day_is_recorded_as_a_failed_day(two_day_update):
    """A day failing for any reason is recorded, so it is not silently replayed."""
    with patch.object(
        timeio_manager, "transfer_data_by_day", side_effect=ValueError("unknown thing")
    ):
        with pytest.raises(CrnsUpdateIncomplete) as excinfo:
            timeio_manager.update_crns_measurments()

    assert excinfo.value.failed_days == [DAY_ONE, DAY_TWO]
    assert two_day_update.call_args_list == [
        call(datetime(2024, 1, 1), False),
        call(datetime(2024, 1, 2), False),
    ]


def test_a_thing_without_datastreams_fails_its_day(two_day_update):
    """collect_datastreams returns None for it; that is a failed day, not a crash."""
    with (
        patch.object(TimeIOManager, "get_ignore_things", return_value=[]),
        patch.object(TimeIOManager, "get_things", return_value=[THING]),
        patch.object(TimeIOManager, "get_thing_datastream_dict", return_value={1: {}}),
    ):
        with pytest.raises(CrnsUpdateIncomplete) as excinfo:
            timeio_manager.update_crns_measurments()

    assert excinfo.value.failed_days == [DAY_ONE, DAY_TWO]
    assert two_day_update.call_args_list[0] == call(datetime(2024, 1, 1), False)


def test_a_stationary_sensor_without_location_fails_its_day(two_day_update, caplog):
    """get_location_of_thing returns None for it; the day fails and names the sensor."""
    with (
        patch.object(TimeIOManager, "get_ignore_things", return_value=[]),
        patch.object(TimeIOManager, "get_things", return_value=[THING]),
        patch.object(
            TimeIOManager,
            "get_thing_datastream_dict",
            return_value={1: {10: "Neutron counts"}},
        ),
        patch.object(
            TimeIOManager,
            "get_values",
            return_value=(["2024-01-01T12:00:00"], [100.0]),
        ),
        patch.object(TimeIOManager, "is_stationary", return_value=True),
        patch.object(TimeIOManager, "get_location_of_thing", return_value=None),
        caplog.at_level(logging.ERROR),
    ):
        with pytest.raises(CrnsUpdateIncomplete) as excinfo:
            timeio_manager.update_crns_measurments()

    assert excinfo.value.failed_days == [DAY_ONE, DAY_TWO]
    assert "no location" in caplog.text


def test_update_db_task_marks_the_run_failed_when_the_soft_limit_hits():
    """The soft limit reaches the task, which records the run as failed."""
    with (
        patch.object(
            maintenance_tasks,
            "update_crns_measurments",
            side_effect=SoftTimeLimitExceeded(),
        ),
        patch.object(
            maintenance_tasks.PostgresManager, "create_update_run", return_value=1
        ),
        patch.object(maintenance_tasks.PostgresManager, "complete_update_run") as done,
        patch.object(
            maintenance_tasks.PostgresManager,
            "count_consecutive_failed_update_runs",
            return_value=1,
        ),
        patch.object(maintenance_tasks, "send_mail"),
    ):
        maintenance_tasks.update_db_task(None)

    done.assert_called_once_with(1, "failed")


@pytest.fixture
def update_runs():
    """Yield a function that adds a run row started so long ago; clear the table."""

    def add(age: timedelta, status: str) -> None:
        with PostgresManager.session_scope() as session:
            session.add(
                UpdateDbRuns(start_time=datetime.now() - age, pid=1, status=status)
            )

    with PostgresManager.session_scope() as session:
        session.query(UpdateDbRuns).delete()
    yield add
    with PostgresManager.session_scope() as session:
        session.query(UpdateDbRuns).delete()


def test_a_run_killed_at_the_hard_limit_counts_as_failed(update_runs):
    """Its row stays 'running' forever; once past the hard limit it is a failure."""
    update_runs(timedelta(days=3), "completed")
    update_runs(timedelta(days=2), "failed")
    update_runs(timedelta(days=1), "running")  # killed, never completed
    update_runs(timedelta(minutes=5), "running")  # the run in progress now

    assert PostgresManager.count_consecutive_failed_update_runs() == 2


def test_the_stale_run_limit_is_the_celery_hard_time_limit():
    assert UPDATE_RUN_HARD_LIMIT_SECONDS == CeleryConfig.task_time_limit


def test_a_run_inside_the_hard_limit_is_not_counted(update_runs):
    update_runs(timedelta(days=1), "failed")
    update_runs(timedelta(seconds=CeleryConfig.task_time_limit - 60), "running")

    assert PostgresManager.count_consecutive_failed_update_runs() == 1
