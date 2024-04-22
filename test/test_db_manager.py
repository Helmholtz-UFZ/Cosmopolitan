"""Test the db_manager class."""

import datetime
from test.mock_input import valid_form_data


def test_if_test_job_exists():
    """Test if the test job exists in the database."""
    from cosmopolitan_app.db_manager import DataBaseManager

    assert DataBaseManager.check_existence(valid_form_data["job_id"])


def test_db_manager():
    """Test the db_manager class."""
    # Need to import here to assure that the .env is set up before import
    from cosmopolitan_app.db_manager import DataBaseManager

    job_id = "job123"

    data_to_insert = {
        "job_id": job_id,
        "start_date": datetime.date(2024, 3, 12),
        "input_data": {"param1": 10, "param2": "value"},
        "files": [b"binary_data1", b"binary_data2"],
        "file_names": ["file1.txt", "file2.txt"],
        "submitted": True,
        "cluster_job_id": "cluster_789",
        "email": "example@example.com",
        "notified_end": False,
        "logs": "Some log information",
        "status": "completed",
        "version": 1.0,
    }
    DataBaseManager.add_entry(data_to_insert)
    assert DataBaseManager.check_existence(job_id)
