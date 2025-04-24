"""Dash form for the cosmopolitan job."""

import json
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


def construct_selected_input(chosen_input):
    """Construct html view of the selected inputs (predictors and crns data)."""
    content = []
    for input_name, input_info in chosen_input.items():
        if input_name in stream_dic:
            input_info = stream_dic[input_name].class_info(input_name)
        elif "crn_" in input_name:
            print(input_info)
            print(input_name)
            input_info = f"Time steps: {', '.join(input_info['time_steps'])}\n"
        else:
            input_info = (
                f"Unit: { input_info['unit'] }\n"
                f"With deviation: { input_info['std_deviation'] }\n"
                f"Constant: {input_info['constant'] }\n"
                f"Predictor name: {input_info['predictor_name'] }\n"
            )

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
    state.pop("new_preview")
    try:
        model = ModelWebsite(**state)
    except ValueError:
        raise PreventUpdate
    job = Job(model=model)
    file_name = job.preview_area()
    image_src = url_for("serve_file", job_id=job.job_id, filename=file_name)

    return {"area_preview": image_src}


@create_callback_with_error_handling(
    output={
        **form_factory.get_output_file_feedback("crns_upload"),
        **form_factory.get_output_hidden_file_information("crns_upload"),
        "selected_crns": Output("selected-crns", "children"),
    },
    inputs={
        **form_factory.get_input_file_content("crns_upload"),
        **form_factory.get_delete_button("crns_upload"),
    },
    state={
        **form_factory.get_state_file_name("crns_upload"),
        **form_factory.produce_callback_inputs(use_state=True),
        "init_trigger": Input("initial-trigger", "data"),
    },
)
def crns_selection(**state):
    """Upload a CRNS file."""
    logging.info("Upload CRNS file")
    init_trigger = state.pop("init_trigger")
    if not init_trigger["init"]:
        logging.debug("Job not initialized")
        raise PreventUpdate

    triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0]

    key_uploaded_file_information = form_factory.get_output_hidden_file_information(
        "crns_upload", get_key="python"
    )

    key_file_names = form_factory.get_state_file_name("crns_upload", get_key="python")
    file_name = state.pop(key_file_names)

    key_files_content = form_factory.get_input_file_content(
        "crns_upload", get_key="python"
    )
    file_content = state.pop(key_files_content)

    model = ModelWebsite(**state)
    job = Job(model=model)

    if triggered_id == form_factory.get_delete_button("crns_upload", get_key="html"):
        logging.debug("Delete button clicked")
        job.delete_input_files("crn")
        chosen_crns = {}
        output_dict = form_factory.create_output_file_feedback("crns_upload", None)
        output_dict[key_uploaded_file_information] = ""
    elif file_content is not None:
        logging.debug("File uploaded")
        job.delete_input_files("crn")

        try:
            file_name, file_information = job.safe_input_file(
                file_name, file_content, "crn"
            )
        except ValueError as e:
            error = e
            chosen_crns = {}
        else:
            error = None
            chosen_crns = {file_name: file_information}
        output_dict = form_factory.create_output_file_feedback("crns_upload", error)
        output_dict[key_uploaded_file_information] = json.dumps(chosen_crns)
    else:
        raise PreventUpdate

    output_dict["selected_crns"] = construct_selected_input(chosen_crns)

    return output_dict


@create_callback_with_error_handling(
    output={
        "selected_predictors": Output("selected-predictors", "children"),
        **form_factory.get_output_hidden_file_information("predictor_upload"),
        **form_factory.get_output_file_feedback("predictor_upload"),
    },
    inputs={
        "pred_streams": form_factory.produce_callback_inputs(all=True)["pred_streams"],
        **form_factory.get_input_file_content("predictor_upload"),
        **form_factory.get_delete_button("predictor_upload"),
    },
    state={
        **form_factory.get_state_file_name("predictor_upload"),
        **form_factory.produce_callback_inputs(use_state=True),
        **form_factory.get_output_hidden_file_information(
            "predictor_upload", use_state=True
        ),
        "init_trigger": Input("initial-trigger", "data"),
    },
)
def predictor_selection(**state):
    """Upload a predictor file."""
    logging.info("Select predictors from file and stream")
    init_trigger = state.pop("init_trigger")
    if not init_trigger["init"]:
        logging.debug("Job not initialized")
        raise PreventUpdate
    triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0]

    key_uploaded_file_information = form_factory.get_output_hidden_file_information(
        "predictor_upload", get_key="python"
    )
    uploaded_file_information = state.pop(key_uploaded_file_information)

    key_file_names = form_factory.get_state_file_name(
        "predictor_upload", get_key="python"
    )
    file_names = state.pop(key_file_names)

    key_files_content = form_factory.get_input_file_content(
        "predictor_upload", get_key="python"
    )
    files_content = state.pop(key_files_content)

    streams = state["pred_streams"]

    model = ModelWebsite(**state)
    job = Job(model=model)
    if uploaded_file_information == "":
        chosen_predictors = {}
    else:
        chosen_predictors = json.loads(uploaded_file_information)

    if triggered_id == form_factory.get_delete_button(
        "predictor_upload", get_key="html"
    ):
        logging.debug("Delete button clicked")
        job.delete_input_files("pred")

        output_dict = {
            **form_factory.get_output_file_feedback("predictor_upload"),
        }
        output_dict = {key: dash.no_update for key in output_dict.keys()}
        output_dict[key_uploaded_file_information] = ""
        chosen_predictors = {}
    elif files_content is not None:
        logging.debug("File(s) uploaded")
        job.delete_input_files("pred")
        try:
            for content, file_name in zip(files_content, file_names):
                file_name, file_information = job.safe_input_file(
                    file_name, content, "pred"
                )
                chosen_predictors[file_information["predictor_name"]] = file_information
        except ValueError as e:
            error = e
            chosen_predictors = {}
        else:
            error = None

        output_dict = form_factory.create_output_file_feedback(
            "predictor_upload", error
        )
        output_dict[key_uploaded_file_information] = json.dumps(chosen_predictors)
    else:
        logging.debug("Stream selected")
        output_dict = {
            **form_factory.get_output_file_feedback("predictor_upload"),
        }
        output_dict = {key: dash.no_update for key in output_dict.keys()}
        output_dict[key_uploaded_file_information] = ""

    for stream in streams:
        chosen_predictors[stream] = None
        # chosen_predictors[stream] = stream_dic[stream].class_info(stream)

    output_dict["selected_predictors"] = construct_selected_input(chosen_predictors)
    return output_dict


@create_callback_with_error_handling(
    output=form_factory.produce_callback_outputs(),
    state={"init_trigger": Input("initial-trigger", "data")},
    inputs=form_factory.produce_callback_inputs(all=True),
)
def validate(**input):
    """Validate the form."""
    logging.info("Validate form")
    init_trigger = input.pop("init_trigger")
    if not init_trigger["init"]:
        logging.debug("Job not initialized")
        raise PreventUpdate
    return form_factory.validate_callback(input)


@create_callback_with_error_handling(
    output=[],
    state={
        **form_factory.produce_callback_inputs(use_state=True, all=True),
        "init_trigger": Input("initial-trigger", "data"),
    },
    inputs=form_factory.get_submit_button(),
)
def submit(**state):
    """Submit the form."""
    logging.info("Submit job")
    init_trigger = state.pop("init_trigger")
    if not init_trigger["init"]:
        logging.debug("Job not initialized")
        raise PreventUpdate

    submit_button = state.pop(form_factory.get_submit_button(get_key="python"))
    if submit_button is None:
        logging.debug("Submit button not clicked")
        raise PreventUpdate

    inputs = form_factory.produce_callback_inputs(use_state=True, all=True)
    inputs = {key: str(value) for key, value in inputs.items()}
    logging.debug(json.dumps(inputs, indent=4))
    logging.debug(json.dumps(state, indent=4))
    form_factory.set_model(state)
    logging.debug(json.dumps(form_factory.pymodel.dict(), indent=4))
    raise PreventUpdate
    # job = Job(model=model)
    # job.submit()
