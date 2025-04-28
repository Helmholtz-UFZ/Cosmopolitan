"""Dash form for the cosmopolitan job."""

import logging
from collections import OrderedDict

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback_context, dcc, html
from dash.exceptions import PreventUpdate
from flask import url_for
from soil_moisture_prediction.input_data import stream_dic

from cosmopolitan_app.error_handling import create_callback_with_error_handling
from cosmopolitan_app.form_factory import FormFactory
from cosmopolitan_app.job import Job
from cosmopolitan_app.layouts import create_header
from cosmopolitan_app.pydantic_models import ModelWebsite

dash.register_page(__name__)


def construct_selected_input(states: dict, input_type: str) -> dbc.ListGroup:
    """Construct html view of the selected inputs (predictors and crns data)."""
    content = []
    chosen_input = {}
    crns_data_info_dict = {
        "station_data": ModelWebsite.__fields__["station_data"].description,
        "rover_data": ModelWebsite.__fields__["rover_data"].description,
        "train_data": ModelWebsite.__fields__["train_data"].description,
    }

    for file_name, file_info in form_factory.get_file_information(states, input_type):
        if input_type == "predictor_upload":
            chosen_input[file_name] = (
                f"Unit: { file_info['unit'] }\n"
                f"With deviation: { file_info['std_deviation'] }\n"
                f"Constant: {file_info['constant'] }\n"
                f"Predictor name: {file_info['predictor_name'] }\n"
            )
        else:
            chosen_input[file_name] = (
                f"Time steps: {', '.join(file_info['time_steps'])}\n"
            )

    if input_type == "predictor_upload":
        for stream in states["pred_streams"]:
            chosen_input[stream] = stream_dic[stream].class_info(stream)
    else:
        for source_name, crns_info in crns_data_info_dict.items():
            if states[source_name]:
                chosen_input[source_name] = crns_info

    for input_name, input_info in chosen_input.items():
        content.append(
            dbc.ListGroupItem(
                html.Div(
                    [
                        html.Div(input_name, className="fw-bold"),
                        html.Small(
                            input_info,
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
]

selected_predictors = [
    html.H2("Selected Predictors", className="text-center"),
    html.Div(id="selected-predictors", className="text-center"),
]

selected_crns = [
    html.H2("Selected CRNS measurments", className="text-center"),
    html.Div(id="selected-crns", className="text-center"),
]

# Dependency with init callback. Second element is expected to be the image
area_preview = dbc.Row(
    [
        html.H5("Area preview:"),
        dbc.Spinner(
            html.Img(
                id="area_preview",
                className="col-6 mx-auto d-block",
                src="",
                alt="area preview",
            ),
        ),
        html.Div(  # wrapper for centering
            dbc.Button(
                "Generate preview",
                id="new_preview",
                color="primary",
                class_name="my-2",
                style={"width": "auto"},
            ),
            className="d-flex justify-content-center",
        ),
    ],
    className="text-center pt-2",
)

crns_data_base = dbc.Row(
    [
        html.H5("Use CRNS data from TimeIO:"),
        dbc.FormText("Select the CRNS data to use for the prediction."),
        dbc.FormText(
            "If you whish to use your own data, upload it in the file upload section."
        ),
        dbc.FormText(
            "If you dont want to use any data from the data base uncheck all checkboxes."  # noqa
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
            [area_preview],
        ],
        "CRNS Measurments": [
            [crns_data_base],
            ["date_range"],
            ["train_data"],
            ["station_data"],
            ["rover_data"],
            [html.Hr()],
            ["crns_upload"],
            [html.Hr()],
            [selected_crns],
        ],
        "Predictors": [
            ["pred_streams"],
            ["predictor_upload"],
            [html.Hr()],
            [selected_predictors],
        ],
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
        dcc.Store(id="initial-trigger", data={"init": False}),
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
    Output("initial-trigger", "data"),
    Input("initial-trigger", "data"),
)
def init_input(data):
    """Validate the form."""
    if data["init"]:
        raise PreventUpdate
    logging.debug("Init form")

    job = Job()
    file_name = job.preview_area()
    image_src = url_for("serve_file", job_id=job.job_id, filename=file_name)
    area_preview.children[1].src = image_src
    job_id_information[1].children = job.job_id
    form_factory = FormFactory(job.model, form_layout)
    return form_factory.generate_form(muted=False), {"init": True}


@create_callback_with_error_handling(
    output={"area_preview": Output("area_preview", "src")},
    state={
        **form_factory.produce_callback_inputs(use_state=True),
        "init_trigger": Input("initial-trigger", "data"),
    },
    inputs={"new_preview": Input("new_preview", "n_clicks")},
)
def regenerate_preview(**state):
    """Regenerate the preview."""
    logging.debug("Regenerate preview")
    init_trigger = state.pop("init_trigger")
    if not init_trigger["init"]:
        raise PreventUpdate
    logging.debug("Job initialized")
    state.pop("new_preview")
    try:
        form_factory.set_model(state)
    except ValueError:
        logging.debug("Model not valid")
        raise PreventUpdate
    job = Job(model=form_factory.pymodel)
    file_name = job.preview_area()
    image_src = url_for("serve_file", job_id=job.job_id, filename=file_name)

    return {"area_preview": image_src}


@create_callback_with_error_handling(
    output={
        **form_factory.produce_callback_outputs(),
        "selected_crns": Output("selected-crns", "children"),
        "selected_predictors": Output("selected-predictors", "children"),
        # "redirect": Output("url", "pathname"),
    },
    inputs=form_factory.produce_callback_inputs(),
    state={
        "init_trigger": Input("initial-trigger", "data"),
        "job_id": Input("job_id", "children"),
    },
)
def form_manager(**state):
    """Wrap all input logic of the form into one callback."""
    logging.info("Form manager")
    init_trigger = state.pop("init_trigger")
    if not init_trigger["init"]:
        logging.debug("Job not initialized")
        raise PreventUpdate

    job_id = state.pop("job_id")
    job = Job(job_id=job_id)
    file_upload_error = {}

    triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0]
    logging.debug(f"Triggered id: {triggered_id}")
    if triggered_id == form_factory.get_id_delete_button("crns_upload"):
        logging.debug("Delete CRNS button clicked")
        job.delete_input_files("crn")
    elif triggered_id == form_factory.get_id_delete_button("predictor_upload"):
        logging.debug("Delete predictor button clicked")
        job.delete_input_files("pred")
    elif triggered_id == form_factory.get_id_input_file_content("crns_upload"):
        logging.debug("CRNS file uploaded")
        job.delete_input_files("crn")

        file_name, file_content = form_factory.get_file_content(state, "crns_upload")
        try:
            file_name, file_information = job.safe_input_file(
                file_name, file_content, "crn"
            )
        except ValueError as e:
            file_upload_error["crns_upload"] = e

        form_factory.set_file_information(
            state, {file_name: file_information}, "crns_upload"
        )

    elif triggered_id == form_factory.get_id_input_file_content("predictor_upload"):
        logging.debug("Predictor file(s) uploaded")
        job.delete_input_files("pred")

        uploaded_file_information = {}
        try:
            for content, file_name in form_factory.get_file_content(
                state, "predictor_upload"
            ):
                file_name, file_information = job.safe_input_file(
                    file_name, content, "pred"
                )
                uploaded_file_information[file_name] = file_information
        except ValueError as e:
            file_upload_error["predictor_upload"] = e

        form_factory.set_file_information(
            state, uploaded_file_information, "predictor_upload"
        )

    valid, output_dict = form_factory.validate_callback(state, file_upload_error)

    if triggered_id == form_factory.get_key_submit_button():
        logging.debug("Submit button clicked")

    output_dict["selected_predictors"] = construct_selected_input(
        state, "predictor_upload"
    )
    output_dict["selected_crns"] = construct_selected_input(state, "crns_upload")

    return output_dict
