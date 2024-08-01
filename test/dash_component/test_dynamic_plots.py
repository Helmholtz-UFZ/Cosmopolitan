"""Test the dynamic plots."""

import logging

import pytest
from flask import Flask

from cosmopolitan_app.dash_component.dynamic_plots import (
    create_content,
    load_rfo_prediction,
    plot_parameter,
)


@pytest.mark.order(-1)
def test_dynamic_plots():
    """Test the dynamic plots."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    matplotlib_logger = logging.getLogger("matplotlib")
    matplotlib_logger.setLevel(logging.CRITICAL)
    app = Flask(__name__)
    job_id = "valid_form_data"
    with app.app_context():
        rfo_prediction = load_rfo_prediction(job_id)
        for plot_id in plot_parameter:
            create_content(plot_id, rfo_prediction, *plot_parameter[plot_id])
