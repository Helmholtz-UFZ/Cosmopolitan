"""Submit your job and monitor its progress.

This page serves as your job control center where you can:
- Review your job configuration and input parameters
- Submit your job for processing in the background
- Monitor job status (Pending, Running, Failed, or Completed)
- View job execution logs in real-time
- Change input parameters if needed
- Navigate to results once processing is complete
- Spawn a new job based on the current one

Jobs are processed asynchronously by background workers, so you can safely navigate
away from this page while your job runs. You'll receive status updates and can return
at any time to check progress.

NOTE: This docstring is displayed on the documentation webpage.
"""

import logging
import os

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, callback_context, dcc, html
from dash_form_factory import FormFactory
from flask import url_for

from cosmopolitan_app.constants import (
    ACCORDION_SUBMISSION_ID,
    CHANGE_INPUT_BUTTON_SUBMISSION_ID,
    HEADER_DIV_SUBMISSION_ID,
    ICON_SUBMISSION_ID,
    INTERVAL_SUBMISSION_ID,
    JOB_LOGS_DIV_SUBMISSION_ID,
    JOB_STORE_SUBMISSION_ID,
    LOADING_OVERLAY_MODAL_SHARED_ID,
    MAIN_CONTENT_DIV_SUBMISSION_ID,
    RESULT_BUTTON_SUBMISSION_ID,
    SPAWN_BUTTON_SUBMISSION_ID,
    STATUS_DIV_SUBMISSION_ID,
    SUBMIT_JOB_BUTTON_SUBMISSION_ID,
    TIME_TO_LIFE_DIV_SUBMISSION_ID,
    URL_LOCATION_SHARED_ID,
)
from cosmopolitan_app.files_route import create_download_button
from cosmopolitan_app.form_template_factory import (
    FormTemplateFactory,
    construct_selected_input,
)
from cosmopolitan_app.job import Job
from cosmopolitan_app.layouts import landing_page_layout_column
from cosmopolitan_app.utils import swap_classes

log = logging.getLogger(__name__)

dash.register_page(
    __name__,
    path_template="/submission/<job_id>",
)


status_button_config = {
    "PENDING": {
        "disabled_submit": False,
        "disabled_change_input": False,
        "disabled_spawn": True,
        "disabled_result": True,
    },
    "RUNNING": {
        "disabled_submit": True,
        "disabled_change_input": True,
        "disabled_spawn": True,
        "disabled_result": True,
    },
    "FAILED": {
        "disabled_submit": False,
        "disabled_change_input": False,
        "disabled_spawn": True,
        "disabled_result": True,
    },
    "COMPLETED": {
        "disabled_submit": True,
        "disabled_change_input": True,
        "disabled_spawn": False,
        "disabled_result": False,
    },
}


def wrap_button(button):
    """Wrap a button in a row and column for better layout."""
    return dbc.Row(
        dbc.Col(
            button,
            className="m-2 d-flex justify-content-center align-items-center",
        ),
    )


def create_button_set(status, job_id):
    """Create a set of buttons based on the job status."""
    disabled_submit = status_button_config[status]["disabled_submit"]
    disabled_change_input = status_button_config[status]["disabled_change_input"]
    disabled_spawn = status_button_config[status]["disabled_spawn"]
    disabled_result = status_button_config[status]["disabled_result"]

    submit_button = wrap_button(
        dbc.Button(
            [html.I(className="bi bi-play-fill me-1"), "Submit"],
            id=SUBMIT_JOB_BUTTON_SUBMISSION_ID,
            color="primary",
            disabled=disabled_submit,
        )
    )
    change_input_button = wrap_button(
        dbc.Button(
            [html.I(className="bi bi-pencil-square me-1"), "Change input"],
            id=CHANGE_INPUT_BUTTON_SUBMISSION_ID,
            color="primary",
            disabled=disabled_change_input,
        )
    )
    spawn_button = wrap_button(
        dbc.Button(
            [html.I(className="bi bi-copy me-1"), "Spawn new job"],
            id=SPAWN_BUTTON_SUBMISSION_ID,
            color="primary",
            disabled=disabled_spawn,
        )
    )
    result_button = wrap_button(
        dbc.Button(
            [html.I(className="bi bi-bar-chart-line me-1"), "Result"],
            id=RESULT_BUTTON_SUBMISSION_ID,
            color="primary",
            disabled=disabled_result,
        )
    )
    download_button = wrap_button(create_download_button(job_id, class_name=""))
    return [
        submit_button,
        change_input_button,
        spawn_button,
        result_button,
        download_button,
    ]


deletion_information_template = "The job will be deleted after {time_to_life} days."
status_information_template = "Status:\n {status}"


def layout(job_id):
    """Layout for submission page."""
    return landing_page_layout_column(
        "Job Submission",
        HEADER_DIV_SUBMISSION_ID,
        JOB_STORE_SUBMISSION_ID,
        job_id,
        MAIN_CONTENT_DIV_SUBMISSION_ID,
    )


@callback(
    [
        Output(HEADER_DIV_SUBMISSION_ID, "className", allow_duplicate=True),
        Output(f"{HEADER_DIV_SUBMISSION_ID}-subtitle", "children"),
        Output(MAIN_CONTENT_DIV_SUBMISSION_ID, "children"),
    ],
    [Input(JOB_STORE_SUBMISSION_ID, "data")],
    [State(HEADER_DIV_SUBMISSION_ID, "className")],
    prevent_initial_call="initial_duplicate",
)
def load_submission_content(job_id, header_class_name):
    """Load the main submission content triggered by job-id-store."""
    log.info(
        f"Loading submission content for job {job_id}", extra={"tag": "job_submission"}
    )
    job = Job(job_id)

    # Create the header with job information
    header_class_name = swap_classes(job.status_color(), header_class_name)
    header_subtitle = job.job_id

    # Generate preview
    preview_path = job.get_preview_path()
    if preview_path is None:
        log.info(
            "No preview path found, generating new preview.", extra={"tag": "frontend"}
        )
        job.preview_area()
        preview_path = job.get_preview_path()

    preview_file_name = os.path.basename(preview_path)
    preview_src = url_for("serve_file", job_id=job.job_id, filename=preview_file_name)

    # Construct form components
    selected_predictors = construct_selected_input(
        job.model, "predictor_upload", full_info=True
    )
    selected_crns = construct_selected_input(job.model, "crns_upload", full_info=True)

    template_factory = FormTemplateFactory(
        job_id=job.job_id,
        active=False,
        preview_src=preview_src,
        selected_predictors=selected_predictors,
        selected_crns=selected_crns,
    )
    form_layout = template_factory.generate_template()
    factory = FormFactory(job.model, form_layout, active=False)
    form = factory.process_layout(factory.layout)

    # Determine icon and active accordion item
    icon_color = "icon-error" if job.status == "FAILED" else "icon-none"
    if job.status == "PENDING":
        active_item = "input_accordion"
    else:
        active_item = "logs_accordion"

    accordion_item_style = {
        "max-height": "70vh",
        "overflow-y": "auto",
    }

    # Create accordion
    accordion = dbc.Accordion(
        [
            dbc.AccordionItem(
                form,
                title="Input",
                item_id="input_accordion",
                style=accordion_item_style,
            ),
            dbc.AccordionItem(
                [
                    html.Div(
                        job.logs,
                        id=JOB_LOGS_DIV_SUBMISSION_ID,
                        className="w-100 bg-dark text-white p-3 rounded font-monospace",
                        # no Bootstrap class for white-space: pre-wrap
                        style={"white-space": "pre-wrap"},
                    ),
                ],
                title=html.Span(
                    [
                        "Logs",
                        html.I(
                            className=f"bi bi-x-octagon-fill ms-2 {icon_color}",
                            id=ICON_SUBMISSION_ID,
                        ),
                    ]
                ),
                item_id="logs_accordion",
                style=accordion_item_style,
            ),
        ],
        id=ACCORDION_SUBMISSION_ID,
        active_item=active_item,
    )

    # Create submission layout
    submission_layout = [accordion]
    submission_layout += create_button_set(job.status, job.job_id)

    # Create main content with interval (returned by callback)
    main_content = html.Div(
        [
            dcc.Interval(id=INTERVAL_SUBMISSION_ID, interval=2000, disabled=True),
            html.Div(
                status_information_template.format(status=job.status),
                id=STATUS_DIV_SUBMISSION_ID,
                className="text-center fs-4",
                # no Bootstrap class for white-space: pre-line
                style={"white-space": "pre-line"},
            ),
            html.Div(
                deletion_information_template.format(time_to_life=job.time_to_life()),
                className="text-center fs-5 mb-2",
                id=TIME_TO_LIFE_DIV_SUBMISSION_ID,
            ),
            dbc.Row(
                dbc.Col(
                    submission_layout,
                    className="col-11 col-xl-8 mx-auto",
                )
            ),
        ]
    )

    return header_class_name, header_subtitle, main_content


# Clientside callback: open loading overlay instantly in the browser.
# A server-side callback here would race with the processing callback
# (due to allow_duplicate), potentially leaving the overlay stuck open.
dash.clientside_callback(
    """
    function() {
        for (var i = 0; i < arguments.length; i++) {
            if (arguments[i] != null) return true;
        }
        return false;
    }
    """,
    Output(LOADING_OVERLAY_MODAL_SHARED_ID, "is_open", allow_duplicate=True),
    Input(SPAWN_BUTTON_SUBMISSION_ID, "n_clicks"),
    Input(SUBMIT_JOB_BUTTON_SUBMISSION_ID, "n_clicks"),
    Input(RESULT_BUTTON_SUBMISSION_ID, "n_clicks"),
    Input(CHANGE_INPUT_BUTTON_SUBMISSION_ID, "n_clicks"),
    prevent_initial_call=True,
)


@callback(
    Output(URL_LOCATION_SHARED_ID, "pathname", allow_duplicate=True),
    Output(LOADING_OVERLAY_MODAL_SHARED_ID, "is_open", allow_duplicate=True),
    Output(JOB_LOGS_DIV_SUBMISSION_ID, "children"),
    Output(HEADER_DIV_SUBMISSION_ID, "className", allow_duplicate=True),
    Output(INTERVAL_SUBMISSION_ID, "disabled", allow_duplicate=True),
    Output(ICON_SUBMISSION_ID, "className"),
    Output(SUBMIT_JOB_BUTTON_SUBMISSION_ID, "disabled"),
    Output(CHANGE_INPUT_BUTTON_SUBMISSION_ID, "disabled"),
    Output(SPAWN_BUTTON_SUBMISSION_ID, "disabled"),
    Output(RESULT_BUTTON_SUBMISSION_ID, "disabled"),
    Output(STATUS_DIV_SUBMISSION_ID, "children"),
    Output(TIME_TO_LIFE_DIV_SUBMISSION_ID, "children"),
    Output(ACCORDION_SUBMISSION_ID, "active_item"),
    Input(INTERVAL_SUBMISSION_ID, "n_intervals"),
    Input(SUBMIT_JOB_BUTTON_SUBMISSION_ID, "n_clicks"),
    Input(CHANGE_INPUT_BUTTON_SUBMISSION_ID, "n_clicks"),
    Input(SPAWN_BUTTON_SUBMISSION_ID, "n_clicks"),
    Input(RESULT_BUTTON_SUBMISSION_ID, "n_clicks"),
    State(URL_LOCATION_SHARED_ID, "pathname"),
    State(HEADER_DIV_SUBMISSION_ID, "className"),
    State(ICON_SUBMISSION_ID, "className"),
    prevent_initial_call=True,
)
def submission_manager(
    n_intervals,
    clicks_submit,
    clicks_change_input,
    clicks_spawn,
    clicks_result,
    path_name,
    class_name_header,
    class_name_icon,
):
    """Reload the logs."""
    job_id = path_name.split("/")[-1]
    log.info(f"Submission manager for {job_id}", extra={"tag": "job_submission"})
    triggered_ids = {
        t["prop_id"].split(".")[0]
        for t in callback_context.triggered
        if t["value"] is not None
    }
    num_outputs = len(dash.callback_context.outputs_list)
    input_base_path = dash.page_registry["pages.input"]["path_template"]
    log.debug(f"Triggered ids: {triggered_ids}", extra={"tag": "frontend"})
    job = Job(job_id)
    if SUBMIT_JOB_BUTTON_SUBMISSION_ID in triggered_ids:
        job.delete_logs()
        job.submit()
    elif CHANGE_INPUT_BUTTON_SUBMISSION_ID in triggered_ids:
        job.clean_work_dir()
        input_path = input_base_path.replace("<job_id>", job.job_id)
        return tuple([input_path] + [dash.no_update] * (num_outputs - 1))
    elif SPAWN_BUTTON_SUBMISSION_ID in triggered_ids:
        new_job = job.spawn()
        input_path = input_base_path.replace("<job_id>", new_job.job_id)
        return tuple([input_path] + [dash.no_update] * (num_outputs - 1))
    elif RESULT_BUTTON_SUBMISSION_ID in triggered_ids:
        result_base_path = dash.page_registry["pages.results"]["path_template"]
        result_path = result_base_path.replace("<job_id>", job.job_id)
        return tuple([result_path] + [dash.no_update] * (num_outputs - 1))

    job.reload_logs()
    bg_color = job.status_color()
    url = dash.no_update
    show_loading = False
    disable_interval = True if job.status != "RUNNING" else False
    icon_color = "icon-error" if job.status == "FAILED" else "icon-none"
    disabled_submit = status_button_config[job.status]["disabled_submit"]
    disabled_change_input = status_button_config[job.status]["disabled_change_input"]
    disabled_spawn = status_button_config[job.status]["disabled_spawn"]
    disabled_result = status_button_config[job.status]["disabled_result"]
    status_info = status_information_template.format(status=job.status)
    time_to_life_info = deletion_information_template.format(
        time_to_life=job.time_to_life()
    )
    active_item = "input_accordion" if job.status == "PENDING" else "logs_accordion"

    return (
        url,
        show_loading,
        job.logs,
        swap_classes(bg_color, class_name_header),
        disable_interval,
        swap_classes(icon_color, class_name_icon),
        disabled_submit,
        disabled_change_input,
        disabled_spawn,
        disabled_result,
        status_info,
        time_to_life_info,
        active_item,
    )
