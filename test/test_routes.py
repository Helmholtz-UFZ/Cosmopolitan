"""Test the routes of the Flask application."""

import logging
from test.mock_input import valid_form_data

import pytest


@pytest.mark.order(-1)
def test_download_results(app):
    """Test that the /download/<job_id> route correctly serves a ZIP file."""
    # Set up logger inside the test function so pytest only show logs of failed tests
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    job_id = valid_form_data["job_id"]
    with app.test_client() as app:
        import cosmopolitan_app.routes  # noqa

        # Simulate a GET request to the /download/valid_job route
        response = app.get(f"/download/{job_id}")

        # Assert the response status code is 200 OK
        assert response.status_code == 200

        # Assert the response is a downloadable zip file
        assert response.content_type == "application/zip"

        # Assert the correct filename for the download
        assert (
            response.headers["Content-Disposition"]
            == f"attachment; filename={job_id}.zip"
        )
