"""Page for creating a new job."""

import logging

import dash
import dash_bootstrap_components as dbc
from coolname import generate
from dash import Input, Output, State, callback, html
from dash.exceptions import PreventUpdate

from cosmopolitan_app.job import Job
from cosmopolitan_app.layouts import create_header
from cosmopolitan_app.postgres_manager import PostgresManager
from cosmopolitan_app.pydantic_models import ModelWebsite, validate_job_id

dash.register_page(
    __name__,
)

header = create_header(
    "Create new job",
    "Define new input",
    bg_color="bg-info",
)


def layout():
    """Layout for the new job page."""
    logging.info("Create new job page")

    while True:
        job_id = "_".join(generate(3))
        if not PostgresManager.check_existence(job_id):
            break

    return [
        header,
        dbc.Row(
            dbc.Col(
                [
                    dbc.Label("Job ID", style={"font-weight": "bold"}),
                    dbc.Input(
                        id="new_job_id",
                        value=job_id,
                        html_size=len(job_id) + 10,
                        style={"width": "auto"},
                        type="text",
                    ),
                    dbc.FormText(
                        "",
                        id="new_job_id_feedback",
                        className="text-danger",
                    ),
                    html.Br(),
                    dbc.FormText(ModelWebsite.model_fields["job_id"].description),
                    html.Br(),
                    html.Div(
                        dbc.Button(
                            "Prepare input",
                            id="prepare_input",
                            color="primary",
                        ),
                        className="m-2 d-flex justify-content-center",
                    ),
                ],
                width="auto",
                className="my-4",
            ),
            justify="center",
        ),
    ]


@callback(
    Output("url", "pathname", allow_duplicate=True),
    Input("prepare_input", "n_clicks"),
    State("new_job_id", "value"),
    prevent_initial_call=True,
)
def prepare_input(n_clicks, job_id):
    """Prepare the input for the new job."""
    logging.info("Prepare input")
    if n_clicks is None:
        raise PreventUpdate
    Job(new_job_id=job_id)
    base_path_submission = dash.page_registry["pages.input"]["path_template"]
    return base_path_submission.replace("<job_id>", str(job_id))


@callback(
    Output("new_job_id_feedback", "children"),
    Output("new_job_id", "valid"),
    Output("new_job_id", "invalid"),
    Input("new_job_id", "value"),
    prevent_initial_call=True,
)
def validate_new_job_id(job_id):
    """Validate the job ID."""
    logging.info("Validate job ID")
    try:
        validate_job_id(job_id)
    except ValueError as e:
        return str(e), False, True

    if PostgresManager.check_existence(job_id):
        return "Job ID already exists", False, True

    return "", True, False
