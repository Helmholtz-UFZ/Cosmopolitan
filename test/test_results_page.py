"""Test the results page against a job whose dates differ in the files they have.

Pure functions over a temporary work dir: no services are needed.
"""

import json
import sys

import dash
import pytest
from cosmo_ecosystem import job_persistence

from soil_moisture_prediction.plot_functions import SCALE_FILE_NAME

from cosmopolitan_app.app import app  # noqa: F401 - registers the pages first

FIRST_DATE = "20220326"
SECOND_DATE = "20220327"
JOB_ID = "results_page_job"

CORRELATION_CSV = (
    "time_step,feature,pred_4,pred_3\n"
    f"{SECOND_DATE},pred_4,1.00,0.97\n"
    f"{SECOND_DATE},pred_3,0.97,1.00\n"
)
IMPORTANCE_CSV = (
    "time_step,predictor,importance,5th_percentile,95th_percentile\n"
    f"{SECOND_DATE},pred_4,0.181,0.083,0.278\n"
    f"{SECOND_DATE},pred_3,0.117,0.039,0.225\n"
)


@pytest.fixture(scope="module")
def results():
    """Return the results page module Dash registered (see test_job_persistence)."""
    page = next(
        page
        for page in dash.page_registry.values()
        if page["path_template"] == "/results/<job_id>"
    )
    return sys.modules[page["module"]]


@pytest.fixture
def work_dir(tmp_path, monkeypatch):
    """Point the results page at a temp work dir holding the files of two dates.

    The first date has only the PNG-side outputs for prediction distance, as a real
    job does: no GeoTIFF and no entry in the scale file.
    """
    files = {
        "correlation_matrix.csv": CORRELATION_CSV,
        "predictor_importance.csv": IMPORTANCE_CSV,
        SCALE_FILE_NAME: json.dumps(
            {
                f"prediction_distance_{SECOND_DATE}": [-0.0, 2.5, ""],
                f"dispersion_coefficient_{FIRST_DATE}": [0.007, 0.05, ""],
                f"dispersion_coefficient_{SECOND_DATE}": [0.007, 0.04, ""],
            }
        ),
        f"prediction_{FIRST_DATE}.tif": "",
        f"prediction_{SECOND_DATE}.tif": "",
        f"prediction_distance_{SECOND_DATE}.tif": "",
        f"dispersion_coefficient_{FIRST_DATE}.tif": "",
        f"dispersion_coefficient_{SECOND_DATE}.tif": "",
        f"measurements_{FIRST_DATE}.geojson": "{}",
        f"measurements_{SECOND_DATE}.geojson": "{}",
    }
    for name, content in files.items():
        (tmp_path / name).write_text(content, encoding="UTF-8")
    monkeypatch.setattr(job_persistence, "local_dir", lambda job_id: str(tmp_path))
    return tmp_path


def test_stats_plots_hold_data_for_a_date_without_dashes(results, work_dir):
    """A time_step like 20220327 is read as text, so the selected date matches."""
    stats = results.load_stats_data(JOB_ID)

    heatmap = results.create_correlation_heatmap(stats["correlation"], SECOND_DATE)
    importance = results.create_importance_by_timestep(stats["timeseries"], SECOND_DATE)

    assert heatmap.data[0].z.shape == (2, 2)
    assert list(importance.data[0].x) == ["pred_4", "pred_3"]
