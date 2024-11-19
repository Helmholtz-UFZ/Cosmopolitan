"""Dash app that presents results."""

import logging
from collections import OrderedDict
from functools import lru_cache
from logging.config import dictConfig
from time import time

import dash_bootstrap_components as dbc
from dash import MATCH, Input, Output, State, ctx, dcc, html
from soil_moisture_prediction.plot_functions import (
    plot_measurements,
    plot_predictor_importance,
    plot_predictors,
    plot_rfo_model,
    prediction_correlation_matrix,
    predictor_importance_along_days,
)
from soil_moisture_prediction.random_forest_model import RFoModel
from sqlalchemy.exc import OperationalError

from cosmopolitan_app.cosmopolitan_job import (
    CosmopolitanJob,
    InvalidJobID,
    NotFinishedException,
    NotSubmittedException,
)
from cosmopolitan_app.dash_component.dash_component import (
    Callback,
    error_response_dash,
    list_callbacks,
    logging_config,
    stand_alone,
)
from cosmopolitan_app.db_manager import JobNotFound


def get_ttl_hash(seconds=3600):
    """Return the same value withing `seconds` time period."""
    return round(time() / seconds)


@lru_cache()
def load_rfo_prediction(job_id, ttl_hash=None):
    """Load job model for plotting."""
    del ttl_hash
    logging.debug(f"Load rfo prediction for {job_id}.")
    cosmopolitan_job = CosmopolitanJob(job_id=str(job_id))
    (
        input_parameters,
        working_dir,
        load_results,
    ) = cosmopolitan_job.get_parameters_rfo_prediction()
    rfo_model = RFoModel(input_parameters=input_parameters, work_dir=working_dir)
    rfo_model.load_input_data(load_from_dump=True)
    rfo_model.load_predictions()
    return rfo_model


def create_slider(plot_id, rfo_prediction):
    """Create dash slider for time steps."""
    time_steps = rfo_prediction.input_data.soil_moisture_data.time_steps
    number_time_steps = len(rfo_prediction.input_data.soil_moisture_data.time_steps)
    size_slider = min(max(int(number_time_steps * 0.8), 3), 12)
    return html.Div(
        html.Div(
            dcc.Slider(
                id={"type": "slider-time-steps", "plot_id": f"{plot_id}"},
                min=1,
                max=number_time_steps,
                step=1,
                value=1,
                marks=dict(enumerate(time_steps, start=1)),
            ),
            className=f"mt-4 col-{ size_slider }",
        ),
        className="row justify-content-center",
    )


# @lru_cache()
def get_image(rfo_prediction, plot_id, time_index, hash_ttl=None):
    """Get image for plot."""
    del hash_ttl

    _header, _time_variable, plot_function = plot_parameter[plot_id]

    logging.debug(f"Get image by function {plot_function.__name__}")

    if time_index is None:
        width, height, content = plot_function(rfo_prediction, None)
    else:
        time_step = rfo_prediction.input_data.soil_moisture_data.time_steps[time_index]
        width, height, content = plot_function(rfo_prediction, time_step, None)

    kwargs_img_element = {
        "className": "d-block mx-auto",
        "src": f"data:image/svg+xml;base64,{content}",
    }

    if width > height:
        kwargs_img_element["width"] = "90%"
    else:
        kwargs_img_element["height"] = "100%"

    return html.Img(**kwargs_img_element)


def create_content(plot_id, rfo_prediction):
    """Create content for plot."""
    logging.debug(f"Create content for {plot_id}.")
    header, time_variable, plot_function = plot_parameter[plot_id]
    element_list = [html.H2(header, style={"textAlign": "center"})]

    # Check if slider is needed
    if (
        time_variable == "var_predictors"
        and rfo_prediction.input_data.all_predictors_constant()
    ):
        slider = False
    elif time_variable == "constant":
        slider = False
    else:
        slider = True

    if slider:
        logging.debug("Create slider.")
        element_list.extend(
            [
                html.H3(children="Select time step", style={"textAlign": "center"}),
                create_slider(plot_id, rfo_prediction),
            ]
        )
    else:
        logging.debug("No slider needed.")

    time_index = 0 if time_variable != "constant" else None
    html_img = get_image(rfo_prediction, plot_id, time_index, hash_ttl=get_ttl_hash())

    element_list.append(
        html.Div(
            html.Div(
                [html_img],
                id={"type": "plot-img", "plot_id": f"{plot_id}"},
                className="col-12 col-xl-9",
            ),
            className="row justify-content-center",
        ),
    )

    return html.Div(element_list)


plot_parameter = OrderedDict()
plot_parameter["sm-pred"] = [
    "Soil Moisture Prediction",
    "var_measurements",
    plot_rfo_model,
]
plot_parameter["crn"] = [
    "Measurements",
    "var_measurements",
    plot_measurements,
]
plot_parameter["pred"] = [
    "Predictors",
    "var_predictors",
    plot_predictors,
]
plot_parameter["pred-corr"] = [
    "Predictor Correlation",
    "var_predictors",
    prediction_correlation_matrix,
]
plot_parameter["pred-imp"] = [
    "Predictor Importance",
    "var_measurements",
    plot_predictor_importance,
]
plot_parameter["pred-imp-ot"] = [
    "Predictor Importance over time",
    "constant",
    predictor_importance_along_days,
]

predictor_plots = ["pred", "pred-corr", "pred-imp"]
plot_button_group = dbc.ButtonGroup(
    [
        dbc.Button(v[0], id=f"{k}-pill", n_clicks=0, outline=True, color="primary")
        for k, v in plot_parameter.items()
    ]
)

app_layout = html.Div(
    [
        dcc.Location(id="url"),
        html.Div(
            [
                html.H2("Results", className="text-center"),
                html.H3(id="job-id", className="text-center"),
            ],
            className="bg-success rounded-top py-2",
        ),
        dbc.Card(
            [
                dbc.CardHeader(
                    [
                        html.H3("Select Plot"),
                        plot_button_group,
                    ],
                    className="text-center",
                ),
                dcc.Input(id="plot-id", value="", type="hidden"),
                dbc.CardBody(html.Div(id="plot-content")),
            ],
            className="rounded-0",
        ),
    ]
)


class RenderContent(Callback):
    """Generate plot for the time step passed by slider."""

    in_out_state = (
        Output("job-id", "children"),
        Output("plot-content", "children"),
        Output("plot-id", "value"),
        State("url", "pathname"),
        Input("sm-pred-pill", "n_clicks"),
        Input("crn-pill", "n_clicks"),
        Input("pred-pill", "n_clicks"),
        Input("pred-corr-pill", "n_clicks"),
        Input("pred-imp-pill", "n_clicks"),
        Input("pred-imp-ot-pill", "n_clicks"),
    )

    parameters = {}

    @staticmethod
    def function(pathname, *pill):
        """Render content on pill select."""
        job_id = pathname.split("/")[-1]
        pill_clicked = ctx.triggered_id
        if pill_clicked is None:
            plot_id = next(iter(plot_parameter))
        else:
            plot_id = pill_clicked.replace("-pill", "")
        logging.debug(f"Render content for {job_id}.")
        try:
            rfo_prediction = load_rfo_prediction(job_id, ttl_hash=get_ttl_hash())
        except (
            InvalidJobID,
            JobNotFound,
            NotFinishedException,
            NotSubmittedException,
            OperationalError,
        ) as e:
            # return ("", dbc.Alert("Error: Job id not found", color="danger"), "")
            return ("", error_response_dash(e), "")

        return (
            job_id,
            create_content(plot_id, rfo_prediction),
            plot_id,
        )


class GeneratePlotPerTimeStep(Callback):
    """Generate plot for the time step passed by slider."""

    in_out_state = (
        Output({"type": "plot-img", "plot_id": MATCH}, "children"),
        Input({"type": "slider-time-steps", "plot_id": MATCH}, "value"),
        State("plot-id", "value"),
        State("url", "pathname"),
    )

    parameters = {
        "prevent_initial_call": True,
    }

    @staticmethod
    def function(time_index, plot_id_tab, pathname):
        """Generate plot for time index passed by slider."""
        job_id = pathname.split("/")[-1]
        logging.debug(f"Generate plot for {job_id} on time index {time_index}.")
        time_index -= 1
        try:
            rfo_prediction = load_rfo_prediction(job_id, ttl_hash=get_ttl_hash())
        except (
            InvalidJobID,
            JobNotFound,
            NotFinishedException,
            NotSubmittedException,
            OperationalError,
        ):
            return
        plot_id = plot_id_tab.replace("-tab", "")
        html_img = get_image(
            rfo_prediction,
            plot_id,
            time_index,
            hash_ttl=get_ttl_hash(),
        )
        return [html_img]


callbacks = list_callbacks(globals())
css_route = "/static/flatly_bootstrap.css"
base_path = "/results/"
if __name__ == "__main__":
    dictConfig(logging_config)
    stand_alone(app_layout, callbacks, css_route)
