"""Tests for the TimeIO retry ladder and the throttled maintenance error mail.

Regression cover for the nightly "404 Client Error ... /Things?$select=id,name"
mail: the upstream STA (a FROST webapp behind Tomcat) answers 404 while its
context is unavailable, which used to abort the whole run and mail every night.
"""

from unittest.mock import Mock, patch

import pytest
import requests
from requests.exceptions import HTTPError, ReadTimeout

import cosmopolitan_app.tasks.maintenance_tasks as maintenance_tasks
from cosmopolitan_app.constants import CONSECUTIVE_FAILURES_BEFORE_MAIL
from cosmopolitan_app.error_handling import TimeIOUnavailableError
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
