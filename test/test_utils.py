"""Test the utils module."""

from cosmopolitan_app import utils


def test_error_response_args():
    """Test that the error response args are correct."""
    job_error_exceptions = [
        utils.InvalidJobID,
        utils.SubmittedException,
        utils.NotSubmittedException,
        utils.NotFinishedException,
    ]

    for exception in job_error_exceptions:
        try:
            raise exception("test_job")
        except Exception as job_error:  # noqa
            template_kwargs, html_error_code, log_it = utils.error_response_args(
                job_error
            )
        error_message = f"Error response args are incorrect for {exception.__name__}"
        assert isinstance(template_kwargs, dict), error_message
        assert isinstance(html_error_code, int), error_message
        assert isinstance(log_it, bool), error_message
        assert set(template_kwargs.keys()) == {"job_id", "error_page"}, error_message
        assert template_kwargs["job_id"] == "test_job", error_message
        assert html_error_code == 400, error_message
