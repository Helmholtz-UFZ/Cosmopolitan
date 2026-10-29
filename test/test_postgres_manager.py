"""Test the postgres_manager class."""

import datetime

from cosmo_ecosystem.db_manager import DbManager

from cosmopolitan_app.postgres_manager import PostgresManager


def test_postgres_manager():
    """Test the postgres_manager class."""
    job_id = "job123"

    data_to_insert = {
        "job_id": job_id,
        "start_date": datetime.date(2024, 3, 12),
        "input_data": {"param1": 10, "param2": "value"},
        "submitted": True,
        "notified_end": False,
        "status": "completed",
        "version": "1.0.0",
    }
    DbManager.add_entry(data_to_insert)
    assert PostgresManager.check_existence(job_id)
