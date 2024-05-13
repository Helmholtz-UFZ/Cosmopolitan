"""Test the utils module."""

# from unittest.mock import MagicMock

# import pytest

from cosmopolitan_app.utils import (
    InvalidJobID,
    NotFinishedException,
    NotSubmittedException,
    SubmittedException,
    error_response_args,
)

# lock_task,


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


# @pytest.fixture
# def mock_db_manager():
#     db_manager = MagicMock()
#     # Lock is initially free
#     db_manager.get_lock.return_value = False
#     return db_manager
#
#
# def test_lock_task(mock_db_manager):
#
#     @lock_task
#     def mock_task():
#         pass
#
#     @lock_task
#     def mock_task_with_exception():
#         raise Exception("Test Exception")
#
#     # Basic functionality test
#     mock_task()
#     mock_db_manager.get_lock.assert_called_once_with("mock_task")
#     mock_db_manager.release_lock.assert_called_once_with("mock_task")
#
#     mock_db_manager.reset_mock()
#
#     # Test that the lock is released even if an exception is raised
#     with pytest.raises(Exception):
#         mock_task_with_exception()
#
#     mock_db_manager.get_lock.assert_called_once_with("mock_task_with_exception")
#     mock_db_manager.release_lock.assert_called_once_with("mock_task_with_exception")
#
#     mock_db_manager.reset_mock()
#
#     # Test that the lock is not released if it was not acquired
#     mock_db_manager.get_lock.return_value = True
#     mock_task()
#     mock_db_manager.get_lock.assert_called_once_with("mock_task")
#     mock_db_manager.release_lock.assert_not_called()
#
#     mock_db_manager.reset_mock()
#
#     # Test that the lock is not released if it was not acquired even if an exception
#     # is raised
#     mock_db_manager.get_lock.return_value = True
#
#     with pytest.raises(Exception):
#         mock_task_with_exception()
#
#     mock_db_manager.get_lock.assert_called_once_with("mock_task_with_exception")
#     mock_db_manager.release_lock.assert_not_called()
