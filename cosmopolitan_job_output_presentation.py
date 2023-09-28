"""Dash app that presents results."""

import json
import os
from collections import OrderedDict

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

from config import WEB_INPUT_DIR
from dash_component import DashComponent

# TODO init call backs eleganter
# TODO rfo_prediction variable cachen
# TODO error calling von Werkzeuge verhandeln lassen
# TODO logger font_manager wtf?


def init_dash(server):
    """Add server to flask server.

    Usage:

    with app.app_context():
        import cosmopolitan_job_output_presentation
        app = cosmopolitan_job_output_presentation.init_dash(app)
    """
    dash_app = DashComponent(
        server=server,
        routes_pathname_prefix="/results/",
    )
    dash_app.layout = app_layout

    init_callbacks(dash_app)
    return dash_app.server


def init_callbacks(dash_app):
    """Add callbacks to dash app."""
    dash_app.callback(
        *callbacks_generate_plot_per_day[0], **callbacks_generate_plot_per_day[1]
    )(generate_plot_per_day)

    dash_app.callback(*callbacks_render_content[0], **callbacks_render_content[1])(
        render_content
    )

    # dash_app.callback(*callbacks_init[0], **callbacks_init[1])(
    #     init
    # )
    return dash_app


def load_rfo_prediction(job_id):
    """Load job model for plotting."""
    global rfo_prediction
    working_dir = f"{ WEB_INPUT_DIR }/ruddy_violet_marmoset/"

    with open(os.path.join(working_dir, "parameters.json"), "r") as f_handle:
        input_data = json.loads(f_handle.read())

    rfo_prediction = RFoPrediction(input_data, working_dir, load_results=True)


def create_slider(plot_id):
    """Create dash slider for days."""
    return dcc.Slider(
        id={"type": "slider-days", "plot_id": f"{plot_id}"},
        min=1,
        max=rfo_prediction.input_data.n_days,
        step=1,
        value=1,
        marks={i: str(i) for i in range(1, 11)},
    )


def create_content(plot_id, header, slider, plot_function):
    """Create conten for plot."""
    element_list = [html.H2(header, style={"textAlign": "center"})]
    if slider:
        element_list.extend(
            [
                html.H3(children="Select day", style={"textAlign": "center"}),
                create_slider(plot_id),
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
        html.H1(children="Title of Dash App", style={"textAlign": "center"}),
        dcc.Tabs(
            id="plot-tabs",
            value="sm-pred",
            children=[
                dcc.Tab(label="Soil Moisture Prediction", value="sm-pred"),
                dcc.Tab(label="Measurements", value="crn"),
                dcc.Tab(label="Predictors", value="pred"),
                dcc.Tab(label="Predictor Correlation", value="pred-corr"),
                dcc.Tab(label="Predictor Importance", value="pred-imp"),
                dcc.Tab(label="Predictor Importance over time", value="pred-imp-ot"),
            ],
        ),
        html.Div(id="plot-content"),
    ]
)


callbacks_render_content = (
    (
        Output("plot-content", "children"),
        Input("plot-tabs", "value"),
        Input("url", "pathname"),
    ),
    {},
)


def render_content(plot_id, pathname):
    """Render content on tab select."""
    if rfo_prediction is None:
        job_id = pathname.split("/")[-1]
        load_rfo_prediction(job_id)

    return create_content(plot_id, *PLOT_PARAMETER[plot_id])


callbacks_generate_plot_per_day = (
    (
        Output({"type": "plot-img", "plot_id": MATCH}, "src"),
        Input({"type": "slider-days", "plot_id": MATCH}, "value"),
        State("plot-tabs", "value"),
    ),
    {
        "prevent_initial_call": True,
    },
)


def generate_plot_per_day(day, plot_id_tab):
    """Generate plot for day passed by slider."""
    day -= 1
    plot_id = plot_id_tab.replace("-tab", "")
    plot_function = PLOT_PARAMETER[plot_id][-1]
    content = plot_function(rfo_prediction, day, return_base64_img=True)
    return f"data:image/svg+xml;base64,{content}"


def main():
    """For testing and devolpment."""
    global rfo_prediction
    working_dir = "output/ruddy_violet_marmoset/"

    with open(os.path.join(working_dir, "parameters.json"), "r") as f_handle:
        input_data = json.loads(f_handle.read())

    rfo_prediction = RFoPrediction(input_data, working_dir, load_results=True)
    app = Dash(__name__, suppress_callback_exceptions=True)
    app.layout = app_layout

    init_callbacks(app)
    app.run_server(debug=True)


if __name__ == "__main__":
    main()
