"""Helper functions for tests."""

import logging

import pytest
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
from cosmopolitan_app.form_template_factory import (
    active_form_factory,
    active_form_template_factory,
)


def wait_for_dash_callback(page):
    """Wait for a pending Dash callback to complete and DOM to stabilize.

    Every form action that triggers a Dash callback (checkbox click, file upload,
    delete button, text input) must call this before further actions. This prevents
    race conditions where a new callback fires before the previous one's response
    has been applied to the DOM.

    The brief timeout before networkidle is necessary because Playwright's click()
    returns to Python before the browser initiates the callback POST. Without it,
    networkidle returns immediately (page is still idle from the previous callback).
    """
    page.wait_for_timeout(100)
    page.wait_for_load_state("networkidle")


def check_all_errors(page):
    """Check for errors on the page.

    This function checks for:
    - Console errors (SEVERE/ERROR level, excluding favicon errors)
    - JavaScript errors
    - Broken images
    """
    wait_for_dash_callback(page)
    errors = []

    # Console errors - get from browser console logs
    console_logs = page.context.pages[0].evaluate(
        """() => {
            return window.__CONSOLE_LOGS__ || [];
        }"""
    )

    # Filter severe/error console messages
    console_errors = [
        log
        for log in console_logs
        if isinstance(log, dict)
        and log.get("level") in ["SEVERE", "ERROR"]
        and "favicon" not in str(log.get("message", "")).lower()
    ]
    if console_errors:
        errors.extend([f"Console: {log['message']}" for log in console_errors])

    # JavaScript errors - check for error elements or window.jsErrors
    js_errors = page.evaluate(
        """() => {
            const errors = window.jsErrors || [];
            const errorElements = Array.from(document.querySelectorAll('[data-error]'))
                .map(el => el.dataset.error);
            return errors.concat(errorElements);
        }"""
    )
    if js_errors:
        errors.extend([f"JS Error: {err}" for err in js_errors if err])

    # Wait for all network requests (Dash callbacks, image loads) to settle
    page.wait_for_load_state("networkidle", timeout=30000)

    # Check for broken images (exclude Leaflet tile images)
    broken_images = page.evaluate(
        """() => {
            return Array.from(document.querySelectorAll('img'))
                .filter(img => !img.closest('.leaflet-tile-pane'))
                .filter(img => img.complete && img.naturalWidth === 0 && img.src !== '')
                .map(img => img.src);
        }"""
    )
    if broken_images:
        errors.extend([f"Broken image: {img}" for img in broken_images])

    if errors:
        pytest.fail("Errors detected:\n" + "\n".join(errors))


# ---------------------------------------------------------------------------
# Layer 1 — Atomic form actions
# ---------------------------------------------------------------------------


def uncheck_all_pred_streams(page):
    """Open the predictor streams dropdown and uncheck all checked items."""
    predictor_dropdown_id = active_form_factory.id_format.format(
        field_name="pred_streams"
    )
    dropdown_menu = page.locator("#pred_streams").locator(
        "xpath=./ancestor::div[contains(@class, 'dropdown-menu')]"
    )
    aria_labelledby = dropdown_menu.get_attribute("aria-labelledby")
    aria_labelledby_escaped = aria_labelledby.replace(":", "\\:")
    page.locator(f"#{aria_labelledby_escaped}").scroll_into_view_if_needed()
    page.locator(f"#{aria_labelledby_escaped}").click()

    # If dropdown was already open, the click closed it — click again to reopen
    if not dropdown_menu.is_visible():
        page.locator(f"#{aria_labelledby_escaped}").click()

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
        wait_for_dash_callback(page)


def check_pred_stream(page, index=0):
    """Open the predictor streams dropdown, check the nth unchecked item.

    Returns the text content of the checked stream's parent element,
    which can be used to assert against selected_predictors.
    """
    predictor_dropdown_id = active_form_factory.id_format.format(
        field_name="pred_streams"
    )
    dropdown_menu = page.locator("#pred_streams").locator(
        "xpath=./ancestor::div[contains(@class, 'dropdown-menu')]"
    )
    aria_labelledby = dropdown_menu.get_attribute("aria-labelledby")
    aria_labelledby_escaped = aria_labelledby.replace(":", "\\:")
    page.locator(f"#{aria_labelledby_escaped}").scroll_into_view_if_needed()
    page.locator(f"#{aria_labelledby_escaped}").click()

    # If dropdown was already open, the click closed it — click again to reopen
    if not dropdown_menu.is_visible():
        page.locator(f"#{aria_labelledby_escaped}").click()

    unchecked = page.locator(
        f"#{predictor_dropdown_id} input[type='checkbox']:not(:checked)"
    )
    target = unchecked.nth(index)
    target_id = target.get_attribute("id")

    # Get the stream key from the checkbox's value attribute.
    # The label shows a human-readable name (e.g. "elevation bkg") but
    # construct_selected_input uses the stream key (e.g. "elevation_bkg").
    stream_name = target.get_attribute("value")

    target_id_escaped = target_id.replace(":", "\\:")
    page.locator(f"#{target_id_escaped}").scroll_into_view_if_needed()
    page.locator(f"#{target_id_escaped}").click()
    wait_for_dash_callback(page)

    return stream_name


def uncheck_all_crns_checkboxes(page):
    """Uncheck all CRNS measurement checkboxes (train, station, rover).

    Clicks all three checkboxes unconditionally. Only call this when all three
    are in their default (checked) state — e.g. right after navigating to the
    input page.
    """
    for field_name in ["train_data", "station_data", "rover_data"]:
        crns_id = active_form_factory.id_format.format(field_name=field_name)
        page.locator(f"#{crns_id}").scroll_into_view_if_needed()
        page.locator(f"#{crns_id}").click()
        wait_for_dash_callback(page)


def check_crns_checkbox(page, field_name):
    """Re-check a specific CRNS checkbox (e.g. 'station_data')."""
    crns_id = active_form_factory.id_format.format(field_name=field_name)
    page.locator(f"#{crns_id}").scroll_into_view_if_needed()
    page.locator(f"#{crns_id}").click()
    wait_for_dash_callback(page)


def upload_predictor_files(page, pred_file_paths):
    """Upload predictor files one at a time and verify each appears after upload."""
    pred_upload_id = active_form_factory.id_format.format(field_name="predictor_upload")
    selected_pred_id = active_form_template_factory.selected_predictors_key
    for pred_file_path in pred_file_paths:
        pred_file_name = str(pred_file_path.name)
        file_input = page.locator(f"#{pred_upload_id} input[type='file']")
        file_input.wait_for(state="attached")
        file_input.set_input_files([])
        wait_for_dash_callback(page)
        file_input.set_input_files(str(pred_file_path))
        expect(page.locator(f"#{selected_pred_id}")).to_contain_text(
            pred_file_name, timeout=10000
        )


def upload_crns_file(page, crns_file_path):
    """Upload a CRNS file and verify it appears in selected_crns.

    Clears the file input first to ensure Dash detects a change even if the
    same file was previously uploaded (dcc.Upload only fires the callback when
    its filename/contents Inputs actually change).
    """
    crns_upload_id = active_form_factory.id_format.format(field_name="crns_upload")
    selected_crns_id = active_form_template_factory.selected_crns_key
    crns_file_name = str(crns_file_path.name)
    file_input = page.locator(f"#{crns_upload_id} input[type='file']")
    file_input.wait_for(state="attached")
    file_input.set_input_files([])
    wait_for_dash_callback(page)
    file_input.set_input_files(str(crns_file_path))
    expect(page.locator(f"#{selected_crns_id}")).to_contain_text(
        crns_file_name, timeout=10000
    )


def click_delete_button(page, delete_button_id: str):
    """Click the delete button for a given upload field."""
    page.locator(f"#{delete_button_id}").scroll_into_view_if_needed()
    page.locator(f"#{delete_button_id}").click()
    wait_for_dash_callback(page)


def fill_email(page):
    """Fill the email field with the test address."""
    email_id = active_form_factory.id_format.format(field_name="email")
    page.locator(f"#{email_id}").scroll_into_view_if_needed()
    page.locator(f"#{email_id}").fill("test@ufz.de")
    page.wait_for_load_state("networkidle")


# ---------------------------------------------------------------------------
# Layer 2 — Page navigation
# ---------------------------------------------------------------------------


def navigate_to_input_page(page):
    """Navigate from home to the input page (New Job > Prepare Input)."""
    page.goto(f"http://localhost:{PORT}/")
    page.set_viewport_size({"width": 1920, "height": 1080})
    check_all_errors(page)

    toggler = page.locator(f"#{NAVBAR_TOGGLER_BUTTON_SHARED_ID}")
    if toggler.is_visible():
        toggler.click()

    page.locator(f"#{NEW_JOB_LINK_SHARED_ID}").click()
    check_all_errors(page)
    page.locator(f"#{PREPARE_INPUT_BUTTON_NEW_JOB_ID}").click()
    check_all_errors(page)

    wait_for_dash_callback(page)


def check_input_and_submit(page):
    """Click Check Input, Change Input, Check Input again, then Submit.

    The double Check Input cycle is required because prepare_input_files()
    updates predictor_upload from disk originals, but the predictors field
    (used by the computation) is only recomputed on the next validate_callback.
    """
    page.locator(f"#{CHECK_INPUT_BUTTON_INPUT_ID}").scroll_into_view_if_needed()
    page.locator(f"#{CHECK_INPUT_BUTTON_INPUT_ID}").click()
    check_all_errors(page)

    page.locator(f"#{CHANGE_INPUT_BUTTON_SUBMISSION_ID}").scroll_into_view_if_needed()
    page.locator(f"#{CHANGE_INPUT_BUTTON_SUBMISSION_ID}").click()
    check_all_errors(page)

    page.locator(f"#{CHECK_INPUT_BUTTON_INPUT_ID}").scroll_into_view_if_needed()
    page.locator(f"#{CHECK_INPUT_BUTTON_INPUT_ID}").click()
    check_all_errors(page)

    page.locator(f"#{SUBMIT_JOB_BUTTON_SUBMISSION_ID}").scroll_into_view_if_needed()
    page.locator(f"#{SUBMIT_JOB_BUTTON_SUBMISSION_ID}").click()
    check_all_errors(page)


def wait_for_job_completion(page):
    """Poll job status until COMPLETED, raise on failure."""
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


def navigate_to_results(page):
    """Navigate to the results page from the submission page."""
    page.locator(f"#{RESULT_BUTTON_SUBMISSION_ID}").scroll_into_view_if_needed()
    page.locator(f"#{RESULT_BUTTON_SUBMISSION_ID}").click()
    wait_for_dash_callback(page)
    check_all_errors(page)


# ---------------------------------------------------------------------------
# Layer 3 — Complete setups
# ---------------------------------------------------------------------------


def setup_default_uploads(page, pred_file_paths, crns_file_path):
    """Set up the form with uploaded files (known-working test config).

    Unchecks all streams and CRNS checkboxes, uploads all files, fills email.
    """
    uncheck_all_pred_streams(page)
    upload_predictor_files(page, pred_file_paths)
    uncheck_all_crns_checkboxes(page)
    upload_crns_file(page, crns_file_path)
    fill_email(page)


def submit_default_job(page, pred_file_paths, crns_file_path):
    """Navigate, set up uploads, submit, and wait for job completion.

    One-liner to get a completed job — useful as setup for result page tests.
    """
    navigate_to_input_page(page)
    setup_default_uploads(page, pred_file_paths, crns_file_path)
    check_input_and_submit(page)
    wait_for_job_completion(page)
