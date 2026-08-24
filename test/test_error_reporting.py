"""Test that unhandled callback errors reach the maintainer-notification hook.

This is the one change in the error path that fails silently: `handle_error` no
longer imports the mail service, it calls whatever `on_unhandled` it was handed.
Forget to wire the hook and nothing breaks — no import error, no failing test,
the maintainer simply stops being told. Hence this test.
"""

import dash
import pytest

from cosmopolitan_app import error_handling
from cosmopolitan_app.error_handling import (
    JobNotFound,
    NotFinishedException,
    handle_error,
)


@pytest.fixture
def captured_props(monkeypatch):
    """Silence the modal writes; handle_error is called outside a callback here."""
    monkeypatch.setattr(error_handling, "set_props", lambda *args, **kwargs: None)


@pytest.fixture
def empty_ctx(monkeypatch):
    """Give handle_error a callback context with no triggers."""

    class _Ctx:
        triggered = []

    monkeypatch.setattr(dash, "ctx", _Ctx())


def test_unexpected_error_calls_hook(captured_props, empty_ctx):
    """An error outside the expected set is reported through the hook."""
    reported = []

    handle_error(
        RuntimeError("boom"),
        on_unhandled=lambda error, subject, body: reported.append((error, subject)),
    )

    assert len(reported) == 1, "on_unhandled was not called for an unexpected error"
    error, subject = reported[0]
    assert isinstance(error, RuntimeError)
    assert "boom" in subject


@pytest.mark.parametrize("expected_error", [JobNotFound("x"), NotFinishedException("some_job")])
def test_expected_errors_do_not_call_hook(expected_error, captured_props, empty_ctx):
    """Expected conditions must not mail the maintainer.

    NotFinishedException is the reason this app keeps its own handler: the
    framework's expected set omits it, so adopting that version would mail on
    every "job is still running" view.
    """
    reported = []

    handle_error(expected_error, on_unhandled=lambda *args: reported.append(args))

    assert reported == [], f"{type(expected_error).__name__} should not be reported"


def test_hook_failure_does_not_break_the_error_modal(captured_props, empty_ctx):
    """A failing notification must not hide the error it was reporting."""

    def exploding_hook(error, subject, body):
        raise ConnectionRefusedError("smtp down")

    handle_error(RuntimeError("boom"), on_unhandled=exploding_hook)


def test_app_wires_the_hook():
    """The seam is only useful if app.py actually passes it.

    Guards the wiring itself, since a missing `on_unhandled=` is exactly the
    silent failure this file exists for. Reads the source rather than importing
    app.py, which would connect to Postgres and start Celery Beat.
    """
    import pathlib

    source = (
        pathlib.Path(__file__).parent.parent / "cosmopolitan_app" / "app.py"
    ).read_text()

    assert "on_unhandled=notify_maintainer" in source, (
        "app.py must wire handle_error's on_unhandled hook, "
        "otherwise maintainer mails stop silently"
    )
