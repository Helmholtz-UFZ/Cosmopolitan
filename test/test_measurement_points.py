"""Test which measurement points the live sensor table and a date range select.

Runs against the real Postgres with PostGIS. Only the map render, which downloads
tiles, is replaced.
"""

import pandas as pd
import pytest
from sqlalchemy import text

from cosmopolitan_app import job as job_module
from cosmopolitan_app.postgres_manager import PostgresManager

SENSOR_ID = 987654  # not in the static sensor table of cosmopolitan_app.timeio_info
LON, LAT = 11.0, 51.0
BBOX = (LON - 0.1, LAT - 0.1, LON + 0.1, LAT + 0.1)
DAY = "2024-05-10"


class _RecordingContext:
    """Stand-in for staticmaps.Context that records objects and renders nothing."""

    def __init__(self):
        self.objects = []

    def set_tile_provider(self, provider):
        pass

    def add_object(self, obj):
        self.objects.append(obj)

    def render_cairo(self, width, height):
        return self


@pytest.fixture
def recorded_map(monkeypatch):
    """Return the context draw_preview draws on, with the tile render replaced."""
    context = _RecordingContext()
    monkeypatch.setattr(job_module.staticmaps, "Context", lambda: context)
    monkeypatch.setattr(
        _RecordingContext, "write_to_png", lambda self, path: None, raising=False
    )
    return context


@pytest.fixture
def sensor_with_measurements():
    """Yield a station sensor, added as the sensor page does, with measurements.

    The measurements lie at noon of the day before DAY, at noon of DAY and at noon
    of the day after.
    """
    PostgresManager.add_timeio_sensor(
        {
            "sensor_id": SENSOR_ID,
            "sensor_name": "test sensor",
            "sensor_type": "station",
            "ignored": False,
            "datastreams": {"1": "Neutron counts"},
        }
    )
    times = ["2024-05-09 12:00", DAY + " 12:00", "2024-05-11 12:00"]
    PostgresManager.insert_crns_measurements_from_df(
        pd.DataFrame(
            {
                "date_time": pd.to_datetime(times),
                "sensor_id": SENSOR_ID,
                "soil_moisture": 0.3,
                "error_high": 0.35,
                "error_low": 0.25,
                "latitude": LAT,
                "longitude": LON,
                "sensor_name": "test sensor",
                "representative": True,
            }
        )
    )
    yield SENSOR_ID
    PostgresManager.purge_measurement_points([SENSOR_ID])
    with PostgresManager.session_scope() as session:
        session.execute(
            text("DELETE FROM timeio_info WHERE sensor_id = :id"), {"id": SENSOR_ID}
        )


def test_a_sensor_added_through_the_sensor_page_is_drawn_in_the_preview(
    sensor_with_measurements, recorded_map
):
    """The preview types a point by the live sensor table, not by a fixed id list."""
    job_module.draw_preview(None, *BBOX, ["station"], DAY, "2024-05-12")

    # the area and one marker for each of the measurements on the 10th and 11th
    assert len(recorded_map.objects) == 3


def test_the_last_selected_day_is_part_of_the_points(sensor_with_measurements):
    """A single-day range holds that day's measurements; the next day's stay out."""
    df = PostgresManager.get_measurement_points(
        BBOX, ["station"], DAY, DAY, representative=False
    )

    assert list(df["date_time"].dt.strftime("%Y-%m-%d")) == [DAY]
