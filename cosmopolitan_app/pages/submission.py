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
from flask import url_for

from cosmopolitan_app.constants import (
    CHANGE_INPUT_BUTTON_ID,
    JOB_LOGS_ID,
    LOADING_OVERLAY_ID,
    RESULT_BUTTON_ID,
    SPAWN_BUTTON_ID,
    SUBMISSION_HEADER_ID,
    SUBMISSION_JOB_ID_STORE,
    SUBMISSION_MAIN_CONTENT_ID,
    SUBMISSION_STATUS_ID,
    SUBMIT_JOB_ID,
    URL_ID,
)
from cosmopolitan_app.form_factory import (
    FormFactory,
    FormTemplateFactory,
    construct_selected_input,
)
from cosmopolitan_app.job import Job
from cosmopolitan_app.layouts import landing_page_layout_column
from cosmopolitan_app.utils import swap_classes

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
            class_name="m-2 d-flex justify-content-center align-items-center",
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
            "Submit", id=SUBMIT_JOB_ID, color="primary", disabled=disabled_submit
        )
    )
    change_input_button = wrap_button(
        dbc.Button(
            "Change input",
            id=CHANGE_INPUT_BUTTON_ID,
            color="primary",
            disabled=disabled_change_input,
        )
    )
    spawn_button = wrap_button(
        dbc.Button(
            "Spawn new job",
            id=SPAWN_BUTTON_ID,
            color="primary",
            disabled=disabled_spawn,
        )
    )
    result_button = wrap_button(
        dbc.Button(
            "Result",
            id=RESULT_BUTTON_ID,
            color="primary",
            disabled=disabled_result,
        )
    )
    download_button = wrap_button(
        dbc.Button(
            "Download work_dir",
            color="primary",
            href=f"/download/{job_id}",
        )
    )
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
        SUBMISSION_HEADER_ID,
        SUBMISSION_JOB_ID_STORE,
        job_id,
        SUBMISSION_MAIN_CONTENT_ID,
    )


@callback(
    [
        Output(SUBMISSION_HEADER_ID, "className", allow_duplicate=True),
        Output(f"{SUBMISSION_HEADER_ID}-subtitle", "children"),
        Output(SUBMISSION_MAIN_CONTENT_ID, "children"),
    ],
    [Input(SUBMISSION_JOB_ID_STORE, "data")],
    [State(SUBMISSION_HEADER_ID, "className")],
    prevent_initial_call="initial_duplicate",
)
def load_submission_content(job_id, header_class_name):
    """Load the main submission content triggered by job-id-store."""
    logging.info(
        f"Loading submission content for job {job_id}", extra={"tag": "job_submission"}
    )
    job = Job(job_id)

    # Create the header with job information
    header_class_name = swap_classes(job.status_color(), header_class_name)
    header_subtitle = job.job_id

    # Generate preview
    preview_path = job.get_preview_path()
    if preview_path is None:
        logging.info(
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

    form_template_factory = FormTemplateFactory(
        job_id=job.job_id,
        active=False,
        preview_src=preview_src,
        selected_predictors=selected_predictors,
        selected_crns=selected_crns,
    )
    form_template = form_template_factory.generate_template()
    form_factory = FormFactory(job.model, form_template, active=False)
    form_layout = form_factory.generate_form()

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
                form_layout,
                title="Input",
                item_id="input_accordion",
                style=accordion_item_style,
            ),
            dbc.AccordionItem(
                [
                    html.Div(
                        job.logs,
                        id=JOB_LOGS_ID,
                        className="w-100 bg-dark text-white p-3 rounded font-monospace",
                        style={"white-space": "pre-wrap"},
                    ),
                ],
                title=html.Span(
                    [
                        "Logs",
                        html.I(
                            className=f"bi bi-x-octagon-fill ms-2 {icon_color}",
                            id="submission_icon",
                        ),
                    ]
                ),
                item_id="logs_accordion",
                style=accordion_item_style,
            ),
        ],
        id="accordion",
        active_item=active_item,
    )

    # Create submission layout
    submission_layout = [accordion]
    submission_layout += create_button_set(job.status, job.job_id)

    # Create main content with interval (returned by callback)
    main_content = html.Div(
        [
            dcc.Interval(id="interval", interval=2000, disabled=True),
            html.Div(
                status_information_template.format(status=job.status),
                id=SUBMISSION_STATUS_ID,
                className="text-center fs-4",
                style={"white-space": "pre-line"},
            ),
            html.Div(
                deletion_information_template.format(time_to_life=job.time_to_life()),
                className="text-center fs-5 mb-2",
                id="submission_time_to_life",
            ),
            dbc.Row(
                dbc.Col(
                    submission_layout,
                    id="form-container",
                    className="col-11 col-xl-8 mx-auto",
                )
            ),
        ]
    )

    return header_class_name, header_subtitle, main_content


@callback(
    Output(LOADING_OVERLAY_ID, "is_open", allow_duplicate=True),
    Input(SPAWN_BUTTON_ID, "n_clicks"),
    Input(SUBMIT_JOB_ID, "n_clicks"),
    Input(RESULT_BUTTON_ID, "n_clicks"),
    Input(CHANGE_INPUT_BUTTON_ID, "n_clicks"),
    prevent_initial_call=True,
)
def show_loading(*inputs):
    """Show loading overlay when preparing input."""
    return any(input for input in inputs if input is not None)


@callback(
    Output(URL_ID, "pathname", allow_duplicate=True),
    Output(LOADING_OVERLAY_ID, "is_open", allow_duplicate=True),
    Output(JOB_LOGS_ID, "children"),
    Output(SUBMISSION_HEADER_ID, "className", allow_duplicate=True),
    Output("interval", "disabled", allow_duplicate=True),
    Output("submission_icon", "className"),
    Output(SUBMIT_JOB_ID, "disabled"),
    Output(CHANGE_INPUT_BUTTON_ID, "disabled"),
    Output(SPAWN_BUTTON_ID, "disabled"),
    Output(RESULT_BUTTON_ID, "disabled"),
    Output(SUBMISSION_STATUS_ID, "children"),
    Output("submission_time_to_life", "children"),
    Output("accordion", "active_item"),
    Input("interval", "n_intervals"),
    Input(SUBMIT_JOB_ID, "n_clicks"),
    Input(CHANGE_INPUT_BUTTON_ID, "n_clicks"),
    Input(SPAWN_BUTTON_ID, "n_clicks"),
    Input(RESULT_BUTTON_ID, "n_clicks"),
    State(URL_ID, "pathname"),
    State(SUBMISSION_HEADER_ID, "className"),
    State("submission_icon", "className"),
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
    logging.info(f"Submission manager for {job_id}", extra={"tag": "job_submission"})
    triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0]
    num_outputs = len(dash.callback_context.outputs_list)
    input_base_path = dash.page_registry["pages.input"]["path_template"]
    logging.debug(f"Triggered id: {triggered_id}", extra={"tag": "frontend"})
    job = Job(job_id)
    if triggered_id == SUBMIT_JOB_ID:
        job.delete_logs()
        job.submit()
    elif triggered_id == CHANGE_INPUT_BUTTON_ID:
        job.clean_work_dir()
        input_path = input_base_path.replace("<job_id>", job.job_id)
        return tuple([input_path] + [dash.no_update] * (num_outputs - 1))
    elif triggered_id == SPAWN_BUTTON_ID:
        new_job = job.spawn()
        input_path = input_base_path.replace("<job_id>", new_job.job_id)
        return tuple([input_path] + [dash.no_update] * (num_outputs - 1))
    elif triggered_id == RESULT_BUTTON_ID:
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
