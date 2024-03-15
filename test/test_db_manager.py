"""Test the db_manager class."""

import datetime


def test_db_manager():
    """Test the db_manager class."""
    from cosmopolitan_app.db_manager import DataBaseManager

    db_manager = DataBaseManager()

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

    db_manager.add_entry(data_to_insert)
    assert db_manager.check_existence(job_id)
