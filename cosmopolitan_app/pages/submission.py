"""Submission page for the Cosmopolitan app."""

import logging
import os

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, html
from flask import url_for

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


def wrap_button(button):
    """Wrap a button in a row and column for better layout."""
    return dbc.Row(
        dbc.Col(
            button,
            class_name="m-2 d-flex justify-content-center align-items-center",
        ),
    )


submit_button = dbc.Button("Submit", id="submit_button", color="primary")
resubmit_button = dbc.Button("Resubmit", id="resubmit_button", color="primary")
change_input_button = dbc.Button(
    "Change input", id="change_input_button", color="primary"
)
spawn_button = dbc.Button("Spawn new job", id="spawn_button", color="primary")


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

    job.prepare_input_files()

    header = create_header("Submission", job.job_id, bg_color=job.status)
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
    print(job.logs)
    accordion = dbc.Accordion(
        [
            dbc.AccordionItem(
                form_layout,
                title="Input",
                item_id="input_accordion",
            ),
            dbc.AccordionItem(
                [
                    html.Div(
                        job.logs,
                        id="logs",
                        className="w-100 bg-dark text-white p-3 rounded font-monospace",  # noqa
                        style={"white-space": "pre-wrap"},
                    ),
                ],
                title=html.Span(
                    [
                        html.I(className="bi bi-x-octagon-fill me-2"),
                        "Item 1",
                    ]
                ),
                item_id="logs_accordion",
            ),
        ],
        id="accordion",
    )

    submission_layout = [
        accordion,
    ]

    if job.status == "PENDING":
        submission_layout += [
            wrap_button(submit_button),
            wrap_button(change_input_button),
        ]

    return [
        header,
        html.Div(job.job_id, id="submission_job_id", style={"display": "none"}),
        dbc.Row(
            dbc.Col(
                submission_layout,
                id="form-container",
                className="col-11 col-xl-8 mx-auto",
            )
        ),
    ]


@callback(
    Output("submit_button", "disabled"),
    Output("change_input_button", "disabled"),
    Output("accordion", "active_item"),
    Input("submit_button", "n_clicks"),
    State("submission_job_id", "children"),
    prevent_initial_call=True,
)
def submit_job(n_clicks, job_id):
    """Submit the job."""
    logging.info(f"Submit job {job_id}")
    job = Job(job_id)
    job.submit()
    return True, True, "logs_accordion"
