"""End-to-end Playwright test for the Dash app."""

import io
import logging
import os
import zipfile
from logging.config import dictConfig
from test.help_functions_tests import check_all_errors
from unittest.mock import patch

from playwright.sync_api import expect

from cosmopolitan_app.config import PORT
from cosmopolitan_app.constants import (
    CHANGE_INPUT_BUTTON_SUBMISSION_ID,
    CHECK_INPUT_BUTTON_INPUT_ID,
    JOB_LOGS_DIV_SUBMISSION_ID,
    NAVBAR_TOGGLER_BUTTON_SHARED_ID,
    NEW_JOB_LINK_SHARED_ID,
    PREPARE_INPUT_BUTTON_NEW_JOB_ID,
    RESULT_BUTTON_SUBMISSION_ID,
    STATUS_DIV_SUBMISSION_ID,
    SUBMIT_JOB_BUTTON_SUBMISSION_ID,
)
from cosmopolitan_app.form_factory import (
    active_form_factory,
    active_form_template_factory,
)
from cosmopolitan_app.logger import get_logger_config_web
from cosmopolitan_app.postgres_manager import PostgresManager
from cosmopolitan_app.pydantic_models import ModelWebsite


@patch("cosmopolitan_app.map_utils.create_tile_layer_component")
def test_full_procedure(
    mock_tile_layer,
    page,
    dash_app,
    crns_file_path,
    pred_file_paths,
    celery_worker,
    worker_log_path,
):
    """Test the full procedure of the Dash app."""
    # Mock tile layer creation to avoid tile server dependency in tests
    # Mock returns None so only the legend is rendered, preventing JS tile fetch errors
    mock_tile_layer.return_value = None

    # Ensure Celery worker is running before starting tests
    dictConfig(get_logger_config_web(True))
    if celery_worker.poll() is not None:
        logging.error("Celery worker process terminated unexpectedly")
        raise RuntimeError("Celery worker not available for testing")

    logging.info("Starting full procedure test with Celery worker")

    # Navigate to the app
    page.goto(f"http://localhost:{PORT}/")
    page.set_viewport_size({"width": 1920, "height": 1080})
    check_all_errors(page)

    # Expand navbar if collapsed
    toggler = page.locator(f"#{NAVBAR_TOGGLER_BUTTON_SHARED_ID}")
    if toggler.is_visible():
        toggler.click()

    # Navigate to New Job > Prepare Input
    page.locator(f"#{NEW_JOB_LINK_SHARED_ID}").click()
    check_all_errors(page)
    page.locator(f"#{PREPARE_INPUT_BUTTON_NEW_JOB_ID}").click()
    check_all_errors(page)

    page.wait_for_timeout(5000)

    # Uncheck predictors
    predictor_dropdown_id = active_form_factory.id_format.format(
        field_name="pred_streams"
    )
    # First the button to open the dropdown menu
    dropdown_menu = page.locator("#pred_streams").locator(
        "xpath=./ancestor::div[contains(@class, 'dropdown-menu')]"
    )
    aria_labelledby = dropdown_menu.get_attribute("aria-labelledby")
    aria_labelledby_escaped = aria_labelledby.replace(":", "\\:")
    page.locator(f"#{aria_labelledby_escaped}").scroll_into_view_if_needed()
    page.locator(f"#{aria_labelledby_escaped}").click()

    # Now the dropdown menu should be open
    # Collect all checked checkbox IDs first, then uncheck them one by one.
    # Clicking a checkbox triggers a Dash callback that re-renders the dropdown,
    # so we cannot iterate a live locator list.
    checked_checkboxes = page.locator(
        f"#{predictor_dropdown_id} input[type='checkbox']:checked"
    )
    checkbox_ids = [
        checked_checkboxes.nth(i).get_attribute("id")
        for i in range(checked_checkboxes.count())
    ]
    for checkbox_id in checkbox_ids:
        checkbox_id_escaped = checkbox_id.replace(":", "\\:")
        page.locator(f"#{checkbox_id_escaped}").scroll_into_view_if_needed()
        page.locator(f"#{checkbox_id_escaped}").click()

    # Upload predictor files
    pred_field_name = "predictor_upload"
    assert (
        pred_field_name in ModelWebsite.model_fields
    ), "Predictor field not found in pymodel"
    pred_upload_id = active_form_factory.id_format.format(field_name=pred_field_name)
    selected_pred_id = active_form_template_factory.selected_predictors_key
    for pred_file_path in pred_file_paths:
        pred_file_name = str(pred_file_path.name)

        page.locator(f"#{pred_upload_id} input[type='file']").set_input_files(
            str(pred_file_path)
        )
        # Wait for the file to appear in the list
        expect(page.locator(f"#{selected_pred_id}")).to_contain_text(
            pred_file_name, timeout=10000
        )

    # Upload CRNS file

    # Uncheck all CRNS measurement fields
    for crns_measurment_field_name in ["train_data", "station_data", "rover_data"]:
        crns_measurment_id = active_form_factory.id_format.format(
            field_name=crns_measurment_field_name
        )
        page.locator(f"#{crns_measurment_id}").scroll_into_view_if_needed()
        page.locator(f"#{crns_measurment_id}").click()

    crns_file_name = str(crns_file_path.name)
    crns_field_name = "crns_upload"
    assert (
        crns_field_name in ModelWebsite.model_fields
    ), "CRNS field not found in pymodel"
    crns_upload_id = active_form_factory.id_format.format(field_name=crns_field_name)

    page.locator(f"#{crns_upload_id} input[type='file']").set_input_files(
        str(crns_file_path)
    )
    selected_crns_id = active_form_template_factory.selected_crns_key
    expect(page.locator(f"#{selected_crns_id}")).to_contain_text(
        crns_file_name, timeout=10000
    )

    check_all_errors(page)

    # Fill in email address for notification testing
    email_id = active_form_factory.id_format.format(field_name="email")
    page.locator(f"#{email_id}").scroll_into_view_if_needed()
    page.locator(f"#{email_id}").fill("test@ufz.de")

    # Check input
    page.locator(f"#{CHECK_INPUT_BUTTON_INPUT_ID}").scroll_into_view_if_needed()
    page.locator(f"#{CHECK_INPUT_BUTTON_INPUT_ID}").click()
    check_all_errors(page)

    # Change input
    page.locator(f"#{CHANGE_INPUT_BUTTON_SUBMISSION_ID}").scroll_into_view_if_needed()
    page.locator(f"#{CHANGE_INPUT_BUTTON_SUBMISSION_ID}").click()
    check_all_errors(page)

    page.locator(f"#{CHECK_INPUT_BUTTON_INPUT_ID}").scroll_into_view_if_needed()
    page.locator(f"#{CHECK_INPUT_BUTTON_INPUT_ID}").click()
    check_all_errors(page)

    # Submit job
    page.locator(f"#{SUBMIT_JOB_BUTTON_SUBMISSION_ID}").scroll_into_view_if_needed()
    page.locator(f"#{SUBMIT_JOB_BUTTON_SUBMISSION_ID}").click()
    check_all_errors(page)

    # Wait for the job to finish — poll status until it leaves RUNNING/PENDING
    status_locator = page.locator(f"#{STATUS_DIV_SUBMISSION_ID}")
    for _ in range(120):
        page.wait_for_timeout(1000)
        status_text = status_locator.text_content()
        if "RUNNING" in status_text or "PENDING" in status_text:
            continue
        break

    status_text = status_locator.text_content()
    if "COMPLETED" not in status_text:
        logging.error(f"Job finished with status: {status_text}")
        job_logs = page.locator(f"#{JOB_LOGS_DIV_SUBMISSION_ID}").text_content()
        raise AssertionError("Job did not complete successfully. Logs:\n" + job_logs)

    # Verify email notifications were logged by the worker
    worker_log = worker_log_path.read_text()
    assert (
        "Send mail about submitted job" in worker_log
    ), "Worker log missing submission email log"
    assert (
        "Send mail about finished job" in worker_log
    ), "Worker log missing finished email log"

    # Verify notification flag in DB
    # Extract job_id from the download link (available after results page)
    # We do this after the results page loads below, but the DB check can
    # use the URL on the current submission page
    current_url = page.url
    job_id = current_url.split("/submission/")[-1].split("/")[0].split("?")[0]
    job_data = PostgresManager.get_job_columns(job_id)
    assert (
        job_data["notified_end"] is True
    ), "Expected notified_end=True in DB after job completion"

    page.locator(f"#{RESULT_BUTTON_SUBMISSION_ID}").scroll_into_view_if_needed()
    page.locator(f"#{RESULT_BUTTON_SUBMISSION_ID}").click()
    page.wait_for_timeout(2000)
    check_all_errors(page)

    # Test work_dir download
    # The download link appears in multiple tab panes; target the visible one.
    download_link = page.locator("a[href*='/download/'][href$='.zip']").first
    expect(download_link).to_be_visible(timeout=10000)
    download_href = download_link.get_attribute("href")
    logging.info(f"Download button href: {download_href}")

    # Use Flask test client to fetch the zip from the route
    with dash_app.server.test_client() as client:
        response = client.get(download_href)
        assert response.status_code == 200, f"Download failed: {response.status_code}"
        assert response.content_type == "application/zip"

        zip_data = io.BytesIO(response.data)
        with zipfile.ZipFile(zip_data) as zf:
            zip_file_names = sorted(zf.namelist())
            logging.info(f"Zip file names: {zip_file_names}")

            # Verify files match the work_dir on disk
            job_id = download_href.split("/download/")[-1].removesuffix(".zip")
            work_dir = f"cosmopolitan_app/work_dir/{job_id}"

            disk_file_names = sorted(
                os.path.relpath(os.path.join(root, f), work_dir)
                for root, _, files in os.walk(work_dir)
                for f in files
            )
            logging.info(f"Disk file names: {disk_file_names}")
            assert zip_file_names == disk_file_names, (
                f"Zip contents don't match work_dir.\n"
                f"Zip: {zip_file_names}\nDisk: {disk_file_names}"
            )

            # Verify file contents are identical
            for name in zip_file_names:
                with open(os.path.join(work_dir, name), "rb") as f:
                    disk_content = f.read()
                zip_content = zf.read(name)
                assert zip_content == disk_content, f"Content mismatch for {name}"

            expected_files = {
                "correlation_matrix.csv",
                "correlation_matrix_20220326.png",
                "correlation_matrix_20220327.png",
                "crn_test_crns_data.csv",
                "data_dump/elevation.npz",
                "data_dump/pred_3.npz",
                "data_dump/pred_4.npz",
                "data_dump/rfm_dump.npz",
                "data_dump/variable_predictor.npz",
                "geotiff_scale.json",
                "logs",
                "measurements_20220326.geojson",
                "measurements_20220326.png",
                "measurements_20220327.geojson",
                "measurements_20220327.png",
                "orginal_crn_test_crns_data.csv",
                "orginal_pred_predictor_1.csv",
                "orginal_pred_predictor_2.csv",
                "orginal_pred_predictor_3.csv",
                "orginal_pred_predictor_4.csv",
                "parameters.json",
                "pred_predictor_1.csv",
                "pred_predictor_2.csv",
                "pred_predictor_3.csv",
                "pred_predictor_4.csv",
                "prediction_20220326.png",
                "prediction_20220326.tif",
                "prediction_20220327.png",
                "prediction_20220327.tif",
                "prediction_distance_20220326.png",
                "prediction_distance_20220326.tif",
                "prediction_distance_20220327.png",
                "prediction_distance_20220327.tif",
                "predictor_elevation_constant.tif",
                "predictor_importance.csv",
                "predictor_importance_20220326.png",
                "predictor_importance_20220327.png",
                "predictor_importance_vs_days.png",
                "predictor_pred_3_constant.tif",
                "predictor_pred_4_constant.tif",
                "predictor_variable_predictor_20220326.tif",
                "predictor_variable_predictor_20220327.tif",
                "predictors_20220326.png",
                "predictors_20220327.png",
                "preview_area_51.79158560622422_10.922864308328695_51.80470713351286_10.945180882465985__2025-06-01_2025-06-28.png",  # noqa
                "smp_version.txt",
            }
            assert set(zip_file_names) == expected_files, (
                f"Unexpected files in work_dir zip.\n"
                f"Zip: {sorted(zip_file_names)}\nExpected: {sorted(expected_files)}"
            )
