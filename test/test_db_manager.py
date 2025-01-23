"""Test the postgres_manager class."""

import datetime
import logging


def test_postgres_manager():
    """Test the postgres_manager class."""
    # Set up logger inside the test function so pytest only show logs of failed tests
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Need to import here to assure that the .env is set up before import
    from cosmopolitan_app.postgres_manager import PostgresManager

    job_id = "job123"

    data_to_insert = {
        "job_id": job_id,
        "start_date": datetime.date(2024, 3, 12),
        "input_data": {"param1": 10, "param2": "value"},
        "files": [b"binary_data1", b"binary_data2"],
        "file_names": ["file1.txt", "file2.txt"],
        "submitted": True,
        "email": "example@example.com",
        "notified_end": False,
        "logs": "Some log information",
        "status": "completed",
        "version": 1.0,
    }
    PostgresManager.add_entry(data_to_insert)
    assert PostgresManager.check_existence(job_id)
