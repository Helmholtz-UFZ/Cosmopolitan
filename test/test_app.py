"""Test the Dash app."""

import io
import logging
import os
import time
import zipfile
from logging.config import dictConfig
from unittest.mock import patch

import pytest
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    NoSuchElementException,
    StaleElementReferenceException,
)

from cosmopolitan_app.app import app
from cosmopolitan_app.constants import (
    CHANGE_INPUT_BUTTON_ID,
    CHECK_INPUT_ID,
    JOB_LOGS_ID,
    NAVBAR_TOGGLER_ID,
    NEW_JOB_LINK_ID,
    PREPARE_INPUT_ID,
    RESULT_BUTTON_ID,
    SUBMISSION_STATUS_ID,
    SUBMIT_JOB_ID,
)
from cosmopolitan_app.form_factory import (
    active_form_factory,
    active_form_template_factory,
)
from cosmopolitan_app.logger import get_logger_config_web
from cosmopolitan_app.pydantic_models import ModelWebsite
from cosmopolitan_app.utils import wait_for_all_images_loaded


def check_all_errors(dash_duo):
    """Simplified error checking that works with most WebDriver configurations."""
    time.sleep(1)  # for everything to load properly
    errors = []

    # Console errors (most reliable)
    console_logs = dash_duo.driver.get_log("browser")
    console_errors = [
        log
        for log in console_logs
        if log["level"] in ["SEVERE", "ERROR"]
        and "favicon" not in log["message"].lower()
    ]
    if console_errors:
        errors.extend([f"Console: {log['message']}" for log in console_errors])

    # JavaScript errors
    js_errors = dash_duo.driver.execute_script(
        """
        return (window.jsErrors || []).concat(
            Array.from(document.querySelectorAll('[data-error]'))
            .map(el => el.dataset.error)
        );
        """
    )
    if js_errors:
        errors.extend([f"JS Error: {err}" for err in js_errors if err])

    # Basic broken image check
    wait_for_all_images_loaded(dash_duo.driver)
    broken_images = dash_duo.driver.execute_script(
        """
        return Array.from(document.querySelectorAll('img'))
            .filter(img => img.complete && img.naturalWidth === 0 && img.src !== '')
            .map(img => img.src);
        """
    )
    if broken_images:
        errors.extend([f"Broken image: {img}" for img in broken_images])

    if errors:
        pytest.fail("Errors detected:\n" + "\n".join(errors))


def scroll_to_element_and_click(dash_duo, element_id):
    """Scroll to a specific element in the Dash app."""
    for _ in range(5):
        element = dash_duo.wait_for_element(f"#{element_id}", timeout=10)
        try:
            dash_duo.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", element
            )
            time.sleep(0.5)
            element.click()
            return element
        except ElementClickInterceptedException:
            pass
        except StaleElementReferenceException:
            pass


def save_snapshot(dash_duo):
    """Save a snapshot of the current state of the Dash app."""
    rendered_html = dash_duo.driver.execute_script(
        "return document.documentElement.outerHTML"
    )
    with open("debug_source.html", "w") as f:
        f.write(rendered_html)
    dash_duo.driver.save_screenshot("headless_debug.png")


@patch("cosmopolitan_app.map_utils.create_tile_layer_component")
def test_full_procedure(
    mock_tile_layer, dash_duo, crns_file_path, pred_file_paths, celery_worker
):
    """Test the full procedure of the Dash app."""
    # Mock tile layer creation to avoid tile server dependency in tests Mock returns
    # None so only the legend is rendered, preventing JavaScript tile fetch errors
    mock_tile_layer.return_value = None

    # Ensure Celery worker is running before starting tests
    dictConfig(get_logger_config_web(True))
    if celery_worker.poll() is not None:
        logging.error("Celery worker process terminated unexpectedly")
        raise RuntimeError("Celery worker not available for testing")

    logging.info("Starting full procedure test with Celery worker")
    dash_duo.start_server(app)
    dash_duo.driver.set_window_size(1920, 1080)
    dash_duo.driver.execute_cdp_cmd("Runtime.enable", {})
    dash_duo.driver.execute_cdp_cmd("Log.enable", {})
    check_all_errors(dash_duo)

    # Expand navbar if collapsed
    try:
        toggler = dash_duo.wait_for_element(f"#{NAVBAR_TOGGLER_ID}", timeout=10)
        if toggler.is_displayed():
            toggler.click()
    except (NoSuchElementException, ElementNotInteractableException):
        pass

    dash_duo.wait_for_element(f"#{NEW_JOB_LINK_ID}", timeout=10).click()
    check_all_errors(dash_duo)
    dash_duo.wait_for_element(f"#{PREPARE_INPUT_ID}", timeout=10).click()
    check_all_errors(dash_duo)

    time.sleep(5)
    # Uncheck predictors
    predictor_dropdown_id = active_form_factory.id_format.format(
        field_name="pred_streams"
    )
    # First the button to open the dropdown menu
    dropdown_menu = dash_duo.find_element("#pred_streams").find_element(
        "xpath", "./ancestor::div[contains(@class, 'dropdown-menu')]"
    )
    aria_labelledby = dropdown_menu.get_attribute("aria-labelledby")
    aria_labelledby = aria_labelledby.replace(":", "\\:")
    scroll_to_element_and_click(dash_duo, aria_labelledby)
    # Now the dropdown menu should be open
    # Find all checked checkboxes in the dropdown menu and uncheck them
    checked_checkboxes = dash_duo.find_elements(
        f"#{predictor_dropdown_id} input[type='checkbox']:checked", "CSS_SELECTOR"
    )
    for checkbox in checked_checkboxes:
        scroll_to_element_and_click(dash_duo, checkbox.get_attribute("id"))

    # Upload predictor files
    pred_field_name = "predictor_upload"
    assert (
        pred_field_name in ModelWebsite.model_fields
    ), "Predictor field not found in pymodel"
    pred_upload_id = active_form_factory.id_format.format(field_name=pred_field_name)
    upload_element = dash_duo.find_element(f"#{pred_upload_id} input[type='file']")
    selected_pred_id = active_form_template_factory.selected_predictors_key
    for pred_file_path in pred_file_paths:
        pred_file_name = str(pred_file_path.name)

        upload_element.send_keys(str(pred_file_path))
        for attempts in range(10):
            time.sleep(1)
            items = dash_duo.find_elements(f"#{selected_pred_id}")
            if any(pred_file_name in item.text for item in items):
                break
        else:
            raise AssertionError(
                f"Predictor file {pred_file_name} not found in the list after upload"  # noqa
            )

    # Upload CRNS file

    # Uncheck all CRNS measurement fields
    for crns_measurment_field_name in ["train_data", "station_data", "rover_data"]:
        crns_measurment_id = active_form_factory.id_format.format(
            field_name=crns_measurment_field_name
        )
        scroll_to_element_and_click(dash_duo, crns_measurment_id)

    crns_file_name = str(crns_file_path.name)
    crns_field_name = "crns_upload"
    assert (
        crns_field_name in ModelWebsite.model_fields
    ), "CRNS field not found in pymodel"
    crns_upload_id = active_form_factory.id_format.format(field_name=crns_field_name)

    upload_element = dash_duo.find_element(f"#{crns_upload_id} input[type='file']")
    upload_element.send_keys(str(crns_file_path))
    selected_crns_id = active_form_template_factory.selected_crns_key
    for attempts in range(10):
        time.sleep(1)
        items = dash_duo.find_elements(f"#{selected_crns_id}")
        if any(crns_file_name in item.text for item in items):
            break
    else:
        raise AssertionError(
            f"CRNS file {crns_file_name} not found in the list after upload"
        )

    check_all_errors(dash_duo)

    # Check input
    scroll_to_element_and_click(dash_duo, CHECK_INPUT_ID)
    check_all_errors(dash_duo)
    # Change input
    scroll_to_element_and_click(dash_duo, CHANGE_INPUT_BUTTON_ID)
    check_all_errors(dash_duo)
    scroll_to_element_and_click(dash_duo, CHECK_INPUT_ID)
    check_all_errors(dash_duo)

    # Submit job
    scroll_to_element_and_click(dash_duo, SUBMIT_JOB_ID)
    check_all_errors(dash_duo)

    # Wait for the submission status to change
    for attempts in range(60):
        time.sleep(1)
        status_element = dash_duo.wait_for_element(
            f"#{SUBMISSION_STATUS_ID}", timeout=1
        )
        if "RUNNING" in status_element.text:
            continue
        elif "PENDING" in status_element.text:
            continue
        break

    if "COMPLETED" not in status_element.text:
        logging.error(f"Job finished with status: {status_element.text}")
        save_snapshot(dash_duo)
        job_logs = dash_duo.find_element(f"#{JOB_LOGS_ID}").text
        raise AssertionError("Job did not complete successfully. Logs:\n" + job_logs)

    scroll_to_element_and_click(dash_duo, RESULT_BUTTON_ID)
    time.sleep(2)
    check_all_errors(dash_duo)

    # Test work_dir download
    # Verify button has external_link (rendered as plain <a>, not Dash-intercepted)
    download_link = dash_duo.wait_for_element(
        "a[href*='/download/'][href$='.zip']", timeout=10
    )
    download_href = download_link.get_attribute("href")
    logging.info(f"Download button href: {download_href}")

    # Use Flask test client to fetch the zip from the route
    with app.server.test_client() as client:
        response = client.get(download_href)
        assert response.status_code == 200, f"Download failed: {response.status_code}"
        assert response.content_type == "application/zip"

        zip_data = io.BytesIO(response.data)
        with zipfile.ZipFile(zip_data) as zf:
            zip_file_names = sorted(zf.namelist())
            logging.info(f"Zip file names: {zip_file_names}")

            # Verify files match the work_dir on disk
            # Extract job_id from href: /download/<job_id>.zip
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

            expected_files = [
                "correlation_matrix.csv",
                "correlation_matrix_20220326.png",
                "correlation_matrix_20220327.png",
                "crn_test_crns_data.csv",
                "data_dump/elevation.npz",
                "data_dump/pred_3.npz",
                "data_dump/pred_4.npz",
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
            ]
            assert zip_file_names == expected_files, (
                f"Unexpected files in work_dir zip.\n"
                f"Zip: {zip_file_names}\nExpected: {expected_files}"
            )
