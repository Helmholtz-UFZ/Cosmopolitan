"""Dash app that presents results."""

import json
import os
from collections import OrderedDict

import dash_bootstrap_components as dbc
from dash import MATCH, Dash, Input, Output, State, dcc, html

# from flask import current_app as app
from plot_functions import (
    plot_measurements,
    plot_predictor_importance,
    plot_predictors,
    plot_rf_prediction,
    pred_corr_matrix,
    predictor_importance_along_days,
)
from RFoPrediction import RFoPrediction

from cosmopolitan_app.config import WEB_INPUT_DIR
from cosmopolitan_app.dash_component.dash_component import Callback, init_callbacks

# TODO rfo_prediction variable cachen


def globals_module():
    """Get globals from this module, needed for init_dash in dash_component."""
    return globals()


def load_rfo_prediction(job_id):
    """Load job model for plotting."""
    # TODO API
    working_dir = os.path.join(WEB_INPUT_DIR, job_id)

    with open(os.path.join(working_dir, "parameters.json"), "r") as f_handle:
        input_data = json.loads(f_handle.read())

    return RFoPrediction(input_data, working_dir, load_results=True)


def create_slider(plot_id, rfo_prediction):
    """Create dash slider for days."""
    return dcc.Slider(
        id={"type": "slider-days", "plot_id": f"{plot_id}"},
        min=1,
        max=rfo_prediction.input_data.n_days,
        step=1,
        value=1,
        marks={i: str(i) for i in range(1, 11)},
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
            [
                html.Img(
                    id={"type": "plot-img", "plot_id": f"{plot_id}"},
                    src=f"data:image/svg+xml;base64,{content}",
                    width="60%",
                )
            ],
            style={"textAlign": "center"},
        )
    )

    return html.Div(element_list)


PLOT_PARAMETER = OrderedDict()
PLOT_PARAMETER["sm-pred"] = [
    "Soil Moisture Prediction",
    True,
    plot_rf_prediction,
]
PLOT_PARAMETER["crn"] = [
    "Measurements",
    True,
    plot_measurements,
]
PLOT_PARAMETER["pred"] = [
    "Predictors",
    False,
    plot_predictors,
]
PLOT_PARAMETER["pred-corr"] = [
    "Predictor Correlation",
    False,
    pred_corr_matrix,
]
PLOT_PARAMETER["pred-imp"] = [
    "Predictor Importance",
    True,
    plot_predictor_importance,
]
PLOT_PARAMETER["pred-imp-ot"] = [
    "Predictor Importance over time",
    False,
    predictor_importance_along_days,
]

app_layout = html.Div(
    [
        dcc.Location(id="url"),
        dbc.Card(
            [
                dbc.CardHeader(
                    dbc.Tabs(
                        [
                            dbc.Tab(label="Soil Moisture Prediction", tab_id="sm-pred"),
                            dbc.Tab(label="Measurements", tab_id="crn"),
                            dbc.Tab(label="Predictors", tab_id="pred"),
                            dbc.Tab(
                                label="Predictor Correlation",
                                label_class_name="fs-7",
                                tab_id="pred-corr",
                            ),
                            dbc.Tab(
                                label="Predictor Importance",
                                label_class_name="fs-7",
                                tab_id="pred-imp",
                            ),
                            dbc.Tab(
                                label="Predictor Importance over time",
                                label_class_name="fs-9",
                                tab_id="pred-imp-ot",
                            ),
                        ],
                        id="plot-tabs",
                        active_tab="sm-pred",
                    )
                ),
                dbc.CardBody(html.Div(id="plot-content")),
            ]
        ),
    ]
)


class RenderContent(Callback):
    """Generate plot for day passed by slider."""

    in_out_state = (
        Output("plot-content", "children"),
        Input("plot-tabs", "active_tab"),
        Input("url", "pathname"),
    )

    parameters = {}

    @staticmethod
    def function(plot_id, pathname):
        """Render content on tab select."""
        job_id = pathname.split("/")[-1]
        try:
            rfo_prediction = load_rfo_prediction(job_id)
        except FileNotFoundError:
            return dbc.Alert("Error: Job id not found", color="danger")

        return create_content(plot_id, rfo_prediction, *PLOT_PARAMETER[plot_id])


class GeneratePlotPerDay(Callback):
    """Generate plot for day passed by slider."""

    in_out_state = (
        Output({"type": "plot-img", "plot_id": MATCH}, "src"),
        Input({"type": "slider-days", "plot_id": MATCH}, "value"),
        State("plot-tabs", "active_tab"),
        Input("url", "pathname"),
    )

    parameters = {
        "prevent_initial_call": True,
    }

    @staticmethod
    def function(day, plot_id_tab, pathname):
        """Generate plot for day passed by slider."""
        day -= 1
        job_id = pathname.split("/")[-1]
        rfo_prediction = load_rfo_prediction(job_id)
        plot_id = plot_id_tab.replace("-tab", "")
        plot_function = PLOT_PARAMETER[plot_id][-1]
        content = plot_function(rfo_prediction, day, return_base64_img=True)
        return f"data:image/svg+xml;base64,{content}"


def main():
    """For testing and devolpment."""
    app = Dash(__name__, suppress_callback_exceptions=True)
    app.layout = app_layout

    init_callbacks(app, globals())
    app.run_server(debug=True)


if __name__ == "__main__":
    main()
