"""Test the Dash app."""

from cosmopolitan_app.app import app


def test_full_procedure(dash_duo):
    """Test the full procedure of the Dash app."""
    dash_duo.start_server(app)
    print("Dash app started")
