"""Test the measurement view's Load callbacks on inputs the user can clear.

A cleared date picker or bounding box input reaches the callbacks as None, and they
must answer with the page's empty state before they touch the database. The type
dropdown reads the live sensor table, which needs the Postgres service.
"""

import sys

import pytest
from dash import html
from sqlalchemy import text

from cosmopolitan_app.app import app  # noqa: F401 - registers the pages first
from cosmopolitan_app.constants.html_ids import TYPE_DROPDOWN_MEASUREMENT_VIEW_ID
from cosmopolitan_app.postgres_manager import PostgresManager

# Looked up in sys.modules instead of imported: Dash registers the page module as
# "pages.measurement_view", and importing it under its package path would register
# the page a second time and fail every later request for duplicate paths.
measurement_view = sys.modules["pages.measurement_view"]

TYPES = ["station"]
BBOX = (580000, 5600000, 590000, 5610000)
PROJECTION = "25832"


def _cleared(index):
    """Return a Load click's date and bbox inputs with the one at index cleared."""
    inputs = ["2024-02-01", "2024-02-29", *BBOX]
    inputs[index] = None
    return inputs


@pytest.mark.parametrize("cleared", range(6))
def test_load_with_a_cleared_input_shows_the_empty_state(cleared):
    start, end, min_lon, min_lat, max_lon, max_lat = _cleared(cleared)

    rows, stats, export_disabled, *_ = measurement_view.load_measurement_data(
        1, TYPES, start, end, False, min_lon, min_lat, max_lon, max_lat, PROJECTION
    )

    assert rows == []
    assert isinstance(stats, html.P)
    assert export_disabled is True


@pytest.mark.parametrize("cleared", range(6))
def test_the_preview_with_a_cleared_input_shows_the_empty_state(cleared):
    start, end, min_lon, min_lat, max_lon, max_lat = _cleared(cleared)

    preview = measurement_view.update_preview_image(
        1, TYPES, start, end, min_lon, min_lat, max_lon, max_lat, PROJECTION
    )

    assert isinstance(preview, html.P)


SENSOR_IDS = {987651: ("added-type", False), 987652: ("ignored-type", True)}


@pytest.fixture
def added_sensors():
    """Yield with one active and one ignored sensor of a type no fixed list knows."""
    for sensor_id, (sensor_type, ignored) in SENSOR_IDS.items():
        PostgresManager.add_timeio_sensor(
            {
                "sensor_id": sensor_id,
                "sensor_name": "test sensor",
                "sensor_type": sensor_type,
                "ignored": ignored,
                "datastreams": {"1": "Neutron counts"},
            }
        )
    yield
    with PostgresManager.session_scope() as session:
        session.execute(
            text("DELETE FROM timeio_info WHERE sensor_id = ANY(:ids)"),
            {"ids": list(SENSOR_IDS)},
        )


def test_the_type_dropdown_offers_the_types_of_the_live_sensor_table(added_sensors):
    """A sensor type added through sensor management is offered; an ignored one not."""
    dropdown = next(
        component
        for component in measurement_view.layout()._traverse()
        if getattr(component, "id", None) == TYPE_DROPDOWN_MEASUREMENT_VIEW_ID
    )

    offered = {option["value"] for option in dropdown.options}
    assert "added-type" in offered
    assert "ignored-type" not in offered
