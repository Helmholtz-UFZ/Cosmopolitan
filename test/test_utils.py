"""Test the utils module."""

from unittest.mock import MagicMock, patch

import pytest

from cosmopolitan_app.db_manager import DataBaseManager
from cosmopolitan_app.utils import (
    InvalidJobID,
    NotFinishedException,
    NotSubmittedException,
    SubmittedException,
    error_response_args,
    lock_task,
)


def test_error_response_args():
    """Test that the error response args are correct."""
    job_error_exceptions = [
        InvalidJobID,
        SubmittedException,
        NotSubmittedException,
        NotFinishedException,
    ]

    for exception in job_error_exceptions:
        try:
            raise exception("test_job")
        except Exception as job_error:  # noqa
            template_kwargs, html_error_code, log_it = error_response_args(job_error)
        error_message = f"Error response args are incorrect for {exception.__name__}"
        assert isinstance(template_kwargs, dict), error_message
        assert isinstance(html_error_code, int), error_message
        assert isinstance(log_it, bool), error_message
        assert set(template_kwargs.keys()) == {"job_id", "error_page"}, error_message
        assert template_kwargs["job_id"] == "test_job", error_message
        assert html_error_code == 400, error_message


@patch.object(DataBaseManager, "get_lock")
@patch.object(DataBaseManager, "release_lock")
def test_lock_task(mock_release_lock, mock_get_lock):
    """Test the lock_task function under three different scenarios.

    1. Task is already running and locked.
    2. Task is not running and lock is acquired.
    3. Task is not running and lock is acquired. But the task raises an exception.
    """
    # Three times the function is called to test. The first two times the lock is
    # acquired and the third time it is not.
    mock_get_lock.side_effect = [False, True, True]
    mock_task = MagicMock()
    # Name attribute is required for the lock_task function to work.
    mock_task.__name__ = "mock_task"

    locked_task = lock_task(mock_task)

    # First case: Task is already running and locked.
    locked_task()
    mock_get_lock.assert_called_once_with("mock_task")
    # The task is already running, so the task should not be called.
    mock_task.assert_not_called()
    mock_release_lock.assert_not_called()
    mock_release_lock.reset_mock()
    mock_get_lock.reset_mock()

    # Second case: Task is not running and lock is acquired.
    locked_task()
    mock_get_lock.assert_called_once_with("mock_task")
    mock_task.assert_called_once()
    mock_release_lock.assert_called_once_with("mock_task")
    mock_release_lock.reset_mock()
    mock_get_lock.reset_mock()

    # Third case: Task is not running and lock is not acquired. But the task raises an
    # exception.
    mock_task.side_effect = Exception("Test")
    with pytest.raises(Exception):
        locked_task()
    mock_get_lock.assert_called_once_with("mock_task")
    mock_release_lock.assert_called_once_with("mock_task")
