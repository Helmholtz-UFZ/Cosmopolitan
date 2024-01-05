"""Dash app that presents results."""

import logging
from collections import OrderedDict
from functools import lru_cache
from logging.config import dictConfig
from time import time

import dash_bootstrap_components as dbc
from dash import MATCH, Input, Output, State, ctx, dcc, html
from plot_functions import (
    plot_measurements,
    plot_predictor_importance,
    plot_predictors,
    plot_rf_prediction,
    pred_corr_matrix,
    predictor_importance_along_days,
)
from RFoPrediction import RFoPrediction
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
        input_data,
        working_dir,
        load_results,
    ) = cosmopolitan_job.get_paratameters_rfo_prediction()
    return RFoPrediction(input_data, working_dir, load_results=True)


def create_slider(plot_id, rfo_prediction):
    """Create dash slider for days."""
    number_days = rfo_prediction.input_data.n_days
    size_slider = min(max(int(number_days * 0.6), 1), 12)

    return html.Div(
        html.Div(
            dcc.Slider(
                id={"type": "slider-days", "plot_id": f"{plot_id}"},
                min=1,
                max=number_days,
                step=1,
                value=1,
                marks={i: str(i) for i in range(1, number_days + 1)},
            ),
            className=f"mt-4 col-{ size_slider }",
        ),
        className="row justify-content-center",
    )


def create_content(plot_id, rfo_prediction, header, slider, plot_function):
    """Create content for plot."""
    element_list = [html.H2(header, style={"textAlign": "center"})]
    if slider:
        element_list.extend(
            [
                html.H3(children="Select day", style={"textAlign": "center"}),
                create_slider(plot_id, rfo_prediction),
            ]
        )

    if slider:
        content = plot_function(rfo_prediction, 0, return_base64_img=True)
    else:
        content = plot_function(rfo_prediction, return_base64_img=True)

    element_list.append(
        html.Div(
            html.Div(
                [
                    html.Img(
                        id={"type": "plot-img", "plot_id": f"{plot_id}"},
                        src=f"data:image/svg+xml;base64,{content}",
                        width="100%",
                    )
                ],
                className="col-12 col-xl-9",
            ),
            className="row justify-content-center",
        ),
    )

    return html.Div(element_list)


plot_parameter = OrderedDict()
plot_parameter["sm-pred"] = [
    "Soil Moisture Prediction",
    True,
    plot_rf_prediction,
]
plot_parameter["crn"] = [
    "Measurements",
    True,
    plot_measurements,
]
plot_parameter["pred"] = [
    "Predictors",
    False,
    plot_predictors,
]
plot_parameter["pred-corr"] = [
    "Predictor Correlation",
    False,
    pred_corr_matrix,
]
plot_parameter["pred-imp"] = [
    "Predictor Importance",
    True,
    plot_predictor_importance,
]
plot_parameter["pred-imp-ot"] = [
    "Predictor Importance over time",
    False,
    predictor_importance_along_days,
]

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
                        dbc.ButtonGroup(
                            [
                                dbc.Button(
                                    "Soil Moisture Prediction",
                                    id="sm-pred-pill",
                                    n_clicks=0,
                                    outline=True,
                                    color="primary",
                                ),
                                dbc.Button(
                                    "Measurements",
                                    id="crn-pill",
                                    n_clicks=0,
                                    outline=True,
                                    color="primary",
                                ),
                                dbc.Button(
                                    "Predictors",
                                    id="pred-pill",
                                    n_clicks=0,
                                    outline=True,
                                    color="primary",
                                ),
                                dbc.Button(
                                    "Predictor Correlation",
                                    id="pred-corr-pill",
                                    n_clicks=0,
                                    outline=True,
                                    color="primary",
                                ),
                                dbc.Button(
                                    "Predictor Importance",
                                    id="pred-imp-pill",
                                    n_clicks=0,
                                    outline=True,
                                    color="primary",
                                ),
                                dbc.Button(
                                    "Predictor Importance over time",
                                    id="pred-imp-ot-pill",
                                    n_clicks=0,
                                    outline=True,
                                    color="primary",
                                ),
                            ],
                        ),
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
    """Generate plot for day passed by slider."""

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
            create_content(plot_id, rfo_prediction, *plot_parameter[plot_id]),
            plot_id,
        )


class GeneratePlotPerDay(Callback):
    """Generate plot for day passed by slider."""

    in_out_state = (
        Output({"type": "plot-img", "plot_id": MATCH}, "src"),
        Input({"type": "slider-days", "plot_id": MATCH}, "value"),
        State("plot-id", "value"),
        State("url", "pathname"),
    )

    parameters = {
        "prevent_initial_call": True,
    }

    @staticmethod
    def function(day, plot_id_tab, pathname):
        """Generate plot for day passed by slider."""
        job_id = pathname.split("/")[-1]
        logging.debug(f"Generate plot for {job_id} on day {day}.")
        day -= 1
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
        plot_function = plot_parameter[plot_id][-1]
        content = plot_function(rfo_prediction, day, return_base64_img=True)
        return f"data:image/svg+xml;base64,{content}"


callbacks = list_callbacks(globals())
if __name__ == "__main__":
    dictConfig(logging_config)
    stand_alone(app_layout, callbacks)
