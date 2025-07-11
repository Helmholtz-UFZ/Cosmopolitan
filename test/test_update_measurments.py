"""Unit tests for the PostgresManager's update CRNS functionality."""

from datetime import datetime, timedelta

import pytest

from cosmopolitan_app.postgres_manager import PostgresManager

START_DATE = datetime(2024, 1, 1)


@pytest.fixture(autouse=True)
def reset_table():
    """Reset the table before each test."""
    PostgresManager.reset_update_crns()


def populate_table_from_dict(data_dict):
    """Populate the CRNS update table from a dictionary.

    Args:
        data_dict (dict):
            Dictionary with date strings as keys and success status as values
            Format: {'2024-01-01': True, '2024-01-02': False, ...}
    """
    for date_str, successful in data_dict.items():
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        PostgresManager.add_update_crns(date_obj, successful)


def test_empty_table():
    """Test case: Empty table should return None."""
    result = PostgresManager.get_earliest_missing_or_failed_date(START_DATE)
    assert result is START_DATE


def test_first_entry_after_start_date():
    """Test case: First entry after start_date should return start_date."""
    data = {"2024-01-05": True}
    populate_table_from_dict(data)

    result = PostgresManager.get_earliest_missing_or_failed_date(START_DATE)
    assert result == START_DATE


def test_earliest_unsuccessful_date():
    """Test case: Should return earliest unsuccessful date."""
    data = {
        "2024-01-01": True,
        "2024-01-02": True,
        "2024-01-03": False,
        "2024-01-04": True,
        "2024-01-05": False,
    }
    populate_table_from_dict(data)

    result = PostgresManager.get_earliest_missing_or_failed_date(START_DATE)
    expected = datetime(2024, 1, 3)
    assert result == expected


def test_gap_in_sequence():
    """Test case: Should return earliest missing date (gap)."""
    data = {
        "2024-01-01": True,
        "2024-01-02": True,
        "2024-01-04": True,  # Gap on 2024-01-03
        "2024-01-05": True,
    }
    populate_table_from_dict(data)

    result = PostgresManager.get_earliest_missing_or_failed_date(START_DATE)
    expected = datetime(2024, 1, 3)
    assert result == expected


def test_gap_vs_unsuccessful_earlier_gap():
    """Test case: Gap earlier than unsuccessful date should return gap."""
    data = {
        "2024-01-01": True,
        "2024-01-02": True,
        # Gap on 2024-01-03
        "2024-01-04": True,
        "2024-01-05": False,  # Unsuccessful later
    }
    populate_table_from_dict(data)

    result = PostgresManager.get_earliest_missing_or_failed_date(START_DATE)
    expected = datetime(2024, 1, 3)  # Gap is earlier
    assert result == expected


def test_gap_vs_unsuccessful_earlier_unsuccessful():
    """Test case: Unsuccessful earlier than gap should return unsuccessful."""
    data = {
        "2024-01-01": True,
        "2024-01-02": False,  # Unsuccessful earlier
        "2024-01-03": True,
        # Gap on 2024-01-04
        "2024-01-05": True,
    }
    populate_table_from_dict(data)

    result = PostgresManager.get_earliest_missing_or_failed_date(START_DATE)
    expected = datetime(2024, 1, 2)  # Unsuccessful is earlier
    assert result == expected


def test_all_successful_consecutive():
    """Test case: All dates successful and consecutive should return next date."""
    data = {"2024-01-01": True, "2024-01-02": True, "2024-01-03": True}
    populate_table_from_dict(data)

    result = PostgresManager.get_earliest_missing_or_failed_date(START_DATE)
    expected = datetime(2024, 1, 4)  # Next date after last successful
    assert result == expected


def test_update_process_with_gaps_and_failures():
    """Test update process with existing gaps and failures."""
    initial_data = {
        # First date is missing
        "2024-01-02": True,
        "2024-01-03": False,  # Failed update
        # Gap on 2024-01-04
        "2024-01-05": True,
        "2024-01-06": False,  # Another failed update
        "2024-01-07": True,
    }
    populate_table_from_dict(initial_data)

    end_date = datetime(2024, 1, 9)

    # Run update process
    while True:
        next_date = PostgresManager.get_earliest_missing_or_failed_date(START_DATE)
        if next_date > end_date:
            break
        PostgresManager.add_update_crns(next_date, successful=True)

    # Check that all dates from start_date to end_date are now successful
    current_date = START_DATE
    while current_date <= end_date:
        assert PostgresManager.was_update_successful(current_date)
        current_date += timedelta(days=1)
