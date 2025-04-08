"""Dash form for the cosmopolitan job."""

import logging
from collections import OrderedDict

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, html
from dash.exceptions import PreventUpdate
from flask import url_for
from soil_moisture_prediction.input_data import stream_dic

from cosmopolitan_app.error_handling import create_callback_with_error_handling
from cosmopolitan_app.form_factory import FormFactory
from cosmopolitan_app.job import Job
from cosmopolitan_app.layouts import create_header
from cosmopolitan_app.pydantic_models import ModelWebsite

dash.register_page(__name__)


def construct_selected_predictors(streams):
    """Construct the selected predictors list."""
    content = []
    for stream in streams:
        content.append(
            dbc.ListGroupItem(
                html.Div(
                    [
                        html.Div(stream, className="fw-bold"),
                        html.Small(
                            stream_dic[stream].class_info(stream),
                            style={"white-space": "pre-line"},
                            className="text-muted",
                        ),
                    ],
                    className="ms-2 me-auto",
                ),
                className="d-flex justify-content-between align-items-start",
            )
        )
    return dbc.ListGroup(content, numbered=True, className="text-start")


# Dependency with init callback. Second element is expected to be the job id
job_id_information = [
    html.Div("Job ID", className="text-center fw-bold fs-4"),
    html.Div("foo_bar", id="job_id", className="text-center"),
    html.Div(id="initial-trigger", style={"display": "none"}),
]

selected_predictors = [
    html.H2("Selected Predictors", className="text-center"),
    html.Div(id="selected-predictors", className="text-center"),
]

# Dependency with init callback. Second element is expected to be the image
area_preview = dbc.Row(
    [
        html.H5("Area preview:"),
        html.Img(
            id="area_preview",
            className="col-6 mx-auto d-block",
            src="",
            alt="area preview",
        ),
    ],
    className="text-center pt-2",
)

form_layout = OrderedDict(
    {
        "Job Information": [[job_id_information], ["email"]],
        "Area of Interest": [
            ["area_x1", "area_x2"],
            ["area_y1", "area_y2"],
            ["area_resolution", "projection"],
            ["date_range"],
            [area_preview],
        ],
        "Predictors": [
            ["pred_streams"],
            ["predictor_upload"],
            [html.Hr()],
            [selected_predictors],
        ],
        # "CRNS Measurments": [["pred_streams"]],
        "Model Parameters": [
            ["monte_carlo_soil_moisture"],
            ["monte_carlo_predictors"],
            ["monte_carlo_iterations"],
            ["past_prediction_as_feature"],
            ["allow_nan_in_training"],
            ["predictor_qmc_sampling"],
            ["compute_slope"],
            ["compute_aspect"],
        ],
    }
)

form_factory = FormFactory(ModelWebsite, form_layout)


header = create_header(
    "Input",
    "Define new input",
)


def layout():
    """Layout of the page."""
    return [
        header,
        dbc.Row(
            dbc.Col(
                form_factory.generate_form(muted=True),
                id="form-container",
                className="col-11 col-xl-8 mx-auto",
            )
        ),
    ]


@create_callback_with_error_handling(
    Output("form-container", "children"),
    Input("initial-trigger", "id"),
)
def init_input(_):
    """Validate the form."""
    logging.debug("Init form")

    job = Job()
    image_src = url_for(
        "serve_file", job_id=job.job_id, filename=job.preview_area_filename
    )
    area_preview.children[1].src = image_src
    job_id_information[1].children = job.job_id
    return form_factory.generate_form(muted=False)


@create_callback_with_error_handling(
    Output("selected-predictors", "children", allow_duplicate=True),
    Input("pred_streams-input", "value"),
)
def list_predictors(streams):
    """Validate the form."""
    logging.debug("List predictors")

    return construct_selected_predictors(streams)


@create_callback_with_error_handling(
    output=[],
    inputs={"file_content": Input("predictor_upload-input", "contents")},
    state={
        "file_name": State("predictor_upload-input", "filename"),
    }
    | form_factory.produce_callback_inputs(use_state=True),
)
def upload_predictor_file(**state):
    """Upload a predictor file."""
    logging.info("Upload predictor file")

    contents = state["file_content"]
    file_names = state["file_name"]
    state.pop("file_content")
    state.pop("file_name")
    if contents is None:
        raise PreventUpdate
    model = ModelWebsite(**state)
    job = Job(model=model)
    for content, file_name in zip(contents, file_names):
        job.validate_input_file(file_name, content, "pred")

    raise PreventUpdate


@create_callback_with_error_handling(
    output=form_factory.produce_callback_outputs(),
    inputs=form_factory.produce_callback_inputs(),
)
def validate(**input):
    """Validate the form."""
    logging.info("Validate form")
    logging.debug(f"Validate call back {dash.callback_context.triggered}")
    return form_factory.validate_callback(input)


@create_callback_with_error_handling(
    output=[],
    state=form_factory.produce_callback_inputs(use_state=True),
    inputs=form_factory.produce_callback_input_button(),
)
def submit(**state):
    """Submit the form."""
    logging.info("Submit job")
    if dash.callback_context.triggered[0]["value"] is None:
        raise PreventUpdate
    logging.debug(f"Initial call back {dash.callback_context.triggered}")
    state.pop(form_factory.get_submit_key())
    model = ModelWebsite(**state)
    job = Job(model=model)
    job.submit()
    # print(model)
