"""Test the measurement view's Load callbacks on inputs the user can clear.

No services are needed: a cleared date picker or bounding box input reaches the
callbacks as None, and they must answer with the page's empty state before they
touch the database.
"""

import sys

import pytest
from dash import html

from cosmopolitan_app.app import app  # noqa: F401 - registers the pages first

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
