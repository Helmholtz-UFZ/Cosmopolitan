"""Submission page for the Cosmopolitan app."""

import logging
import os
import re

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, callback_context, dcc, html
from flask import url_for

from cosmopolitan_app.constants import (
    JOB_LOGS_ID,
    RESULT_BUTTON_ID,
    SUBMISSION_STATUS_ID,
    SUBMIT_JOB_ID,
)
from cosmopolitan_app.form_factory import (
    FormFactory,
    FormTemplateFactory,
    construct_selected_input,
)
from cosmopolitan_app.job import Job
from cosmopolitan_app.layouts import create_header
from cosmopolitan_app.utils import InvalidJobID, JobNotFound

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


def swap_classes(new_class: str, class_name: str) -> str:
    """Replace or add a class with the same prefix as new_class in a className string.

    The prefix is automatically extracted from the new_class.

    Parameters:
    new_class (str): The new class to add (e.g., "bg-primary", "text-white")
    class_name (str): The original className string

    Returns:
    str: The updated className string with the replaced class

    Examples:
    >>> swap_classes("bg-primary", "bg-info rounded-top py-2 mb-4")
    'bg-primary rounded-top py-2 mb-4'
    >>> swap_classes("text-danger", "bg-info text-dark py-2")
    'bg-info text-danger py-2'
    """
    # Extract prefix from new_class
    prefix_match = re.match(r"^([a-zA-Z0-9]+)-", new_class)
    if not prefix_match:
        raise ValueError(
            f"New class '{new_class}' must have a prefix followed by a hyphen (e.g., 'bg-primary')"  # noqa
        )

    class_prefix = prefix_match.group(1)

    # Pattern to match classes with the given prefix
    class_pattern = rf"\b{class_prefix}-[a-zA-Z0-9]+"

    # Check if a class with the given prefix exists
    match = re.search(class_pattern, class_name)

    if match:
        # Replace existing class with the new one
        updated_class_name = re.sub(class_pattern, new_class, class_name)
        return updated_class_name
    else:
        # Add new class if none with the prefix exists
        return f"{class_name} {new_class}"


def wrap_button(button):
    """Wrap a button in a row and column for better layout."""
    return dbc.Row(
        dbc.Col(
            button,
            class_name="m-2 d-flex justify-content-center align-items-center",
        ),
    )


def create_button_set(status):
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
            id="change_input_button",
            color="primary",
            disabled=disabled_change_input,
        )
    )
    spawn_button = wrap_button(
        dbc.Button(
            "Spawn new job", id="spawn_button", color="primary", disabled=disabled_spawn
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
    return [submit_button, change_input_button, spawn_button, result_button]


deletion_information_template = "The job will be deleted after {time_to_life} days."
status_information_template = "Status:\n {status}"


def layout(job_id):
    """Layout for the submission page."""
    logging.info(f"Create submission page for job {job_id}")
    try:
        job = Job(job_id)
    except (JobNotFound, InvalidJobID):
        logging.info(f"Job {job_id} not found")
        return html.Div(
            [
                create_header("Error", "Job not found"),
                html.P("The job you are looking for does not exist."),
            ]
        )

    header = create_header(
        "Submission", job.job_id, bg_color=job.status_color(), id="submission_header"
    )
    preview_path = job.get_preview_path()
    preview_file_name = os.path.basename(preview_path)
    preview_src = url_for("serve_file", job_id=job.job_id, filename=preview_file_name)
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

    icon_color = "icon-error" if job.status == "FAILED" else "icon-none"
    if job.status == "PENDING":
        active_item = "input_accordion"
    else:
        active_item = "logs_accordion"

    accordion_item_style = {
        "max-height": "70vh",
        "overflow-y": "auto",
    }
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
                        className="w-100 bg-dark text-white p-3 rounded font-monospace",  # noqa
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

    submission_layout = [
        accordion,
    ]

    submission_layout += create_button_set(job.status)

    return [
        dcc.Interval(id="interval", interval=2000, disabled=True),
        header,
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


@callback(
    Output("url", "pathname", allow_duplicate=True),
    Output(JOB_LOGS_ID, "children"),
    Output("submission_header", "className"),
    Output("interval", "disabled", allow_duplicate=True),
    Output("submission_icon", "className"),
    Output(SUBMIT_JOB_ID, "disabled"),
    Output("change_input_button", "disabled"),
    Output("spawn_button", "disabled"),
    Output("result_button", "disabled"),
    Output(SUBMISSION_STATUS_ID, "children"),
    Output("submission_time_to_life", "children"),
    Output("accordion", "active_item"),
    Input("interval", "n_intervals"),
    Input(SUBMIT_JOB_ID, "n_clicks"),
    Input("change_input_button", "n_clicks"),
    Input("spawn_button", "n_clicks"),
    Input("result_button", "n_clicks"),
    State("url", "pathname"),
    State("submission_header", "className"),
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
    logging.info(f"Submission manager for {job_id}")
    triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0]
    num_outputs = len(dash.callback_context.outputs_list)
    input_base_path = dash.page_registry["pages.input"]["path_template"]
    logging.debug(f"Triggered id: {triggered_id}")
    job = Job(job_id)
    if triggered_id == SUBMIT_JOB_ID:
        job.delete_logs()
        job.submit()
    elif triggered_id == "change_input_button":
        job.clean_work_dir()
        input_path = input_base_path.replace("<job_id>", job.job_id)
        return tuple([input_path] + [dash.no_update] * (num_outputs - 1))
    elif triggered_id == "spawn_button":
        new_job = job.spawn()
        input_path = input_base_path.replace("<job_id>", new_job.job_id)
        return tuple([input_path] + [dash.no_update] * (num_outputs - 1))
    elif triggered_id == "result_button":
        result_base_path = dash.page_registry["pages.results"]["path_template"]
        result_path = result_base_path.replace("<job_id>", job.job_id)
        return tuple([result_path] + [dash.no_update] * (num_outputs - 1))

    job.reload_logs()
    bg_color = job.status_color()
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
        dash.no_update,
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
