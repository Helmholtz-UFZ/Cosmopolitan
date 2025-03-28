"""Dash form for the cosmopolitan job."""

from collections import OrderedDict

import dash
import dash_bootstrap_components as dbc
from coolname import generate
from dash import Input, Output, callback, html
from soil_moisture_prediction.input_data import stream_dic

from cosmopolitan_app.form_factory import FormFactory
from cosmopolitan_app.layouts import create_header
from cosmopolitan_app.postgres_manager import PostgresManager
from cosmopolitan_app.pydantic_models import ModelWebsite

dash.register_page(__name__)


job_id_information = [
    html.Div("Job ID", className="text-center fw-bold fs-4"),
    html.Div("foobar", id="job_id", className="text-center"),
    html.Div(id="initial-trigger", style={"display": "none"}),
]

selected_predictors = [
    html.H2("Selected Predictors", className="text-center"),
    html.Div(id="selected-predictors", className="text-center"),
]

form_layout = OrderedDict(
    {
        "Job Information": [[job_id_information], ["email"]],
        "Area of Interest": [
            ["area_x1", "area_x2"],
            ["area_y1", "area_y2"],
            ["area_resolution", "projection"],
            ["date_range"],
        ],
        "Predictors": [
            ["pred_streams"],
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

layout = [
    header,
    dbc.Row(
        dbc.Col(
            form_factory.generate_form(),
            className="col-11 col-xl-8 mx-auto",
        )
    ),
]


@callback(Output("job_id", "children"), Input("initial-trigger", "id"))
def init(_):
    """Validate the form."""
    while True:
        job_id = "_".join(generate(3))
        if not PostgresManager.check_existence(job_id):
            break
    return job_id


@callback(
    Output("selected-predictors", "children"),
    Input("pred_streams-input", "value"),
)
def list_predictors(streams):
    """Validate the form."""
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


@callback(
    output=form_factory.produce_callback_outputs(),
    inputs=form_factory.produce_callback_inputs(),
)
def validate(**input):
    """Validate the form."""
    return form_factory.validate_callback(input)


@callback(
    output=[],
    state=form_factory.produce_callback_inputs(use_state=True),
    inputs=form_factory.produce_callback_input_button(),
)
def submit(**state):
    """Submit the form."""
    state.pop(form_factory.get_submit_key())
    model = ModelWebsite(**state)
    print(model)
