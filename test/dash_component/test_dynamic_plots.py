"""Test the dynamic plots."""

import os

import pytest

from cosmopolitan_app.config import JOB_WORK_DIR_TEMPLATE
from cosmopolitan_app.dash_component.dynamic_plots import (
    get_image_name,
    get_time_steps,
    plot_parameter,
)
from cosmopolitan_app.postgres_manager import PostgresManager


@pytest.mark.order(-1)
def test_images_available(logger):
    """Test the dynamic plots."""
    logger.info("Test dynamic plots.")
    job_id = "valid_form_data"
    assert PostgresManager.check_existence(job_id), "Job not found."
    time_steps = get_time_steps(job_id)
    assert len(time_steps) > 0, "No time steps found."
    for plot_id in plot_parameter:
        for time_index in range(len(time_steps)):
            image_name = get_image_name(job_id, plot_id, time_index)
            image_path = os.path.join(
                JOB_WORK_DIR_TEMPLATE.format(job_id=job_id), image_name
            )

            assert os.path.exists(image_path), f"Image {image_name} not found."
