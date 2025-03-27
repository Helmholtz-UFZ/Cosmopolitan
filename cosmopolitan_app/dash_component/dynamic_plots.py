"""Dash app that presents results."""

import glob
import logging
import os
from collections import OrderedDict
from logging.config import dictConfig

import dash_bootstrap_components as dbc
from dash import MATCH, Input, Output, State, ctx, dcc, html
from flask import url_for
from sqlalchemy.exc import OperationalError

from cosmopolitan_app.config import JOB_WORK_DIR_TEMPLATE
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
from cosmopolitan_app.postgres_manager import JobNotFound


def get_time_steps(job_id):
    """Get time steps for job."""
    job_work_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=job_id)
    files = glob.glob(f"{job_work_dir}/measurements_*")
    time_steps = []
    for file in files:
        file_name = os.path.basename(file)
        time_step = file_name.replace("measurements_", "").split(".")[0]
        time_steps.append(time_step)
    time_steps.sort()
    return time_steps


def create_slider(plot_id, job_id):
    """Create dash slider for time steps."""
    time_steps = get_time_steps(job_id)
    number_time_steps = len(time_steps)
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


def all_predictors_constant(job_id):
    """Check if all predictors are constant."""
    job_work_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=job_id)
    return os.path.exists(f"{job_work_dir}/predictors.png")


def get_image_name(job_id, plot_id, time_index):
    """Get image name for plot."""
    # No time step for constant plots or if all predictors are constant and the plot is
    # a predictor plot
    if plot_parameter[plot_id][1] == "constant" or (
        plot_parameter[plot_id][1] == "var_predictors"
        and all_predictors_constant(job_id)
    ):
        time_step = ""
    else:
        time_step = "_" + get_time_steps(job_id)[time_index]

    return plot_parameter[plot_id][2].format(time_step=time_step)


def create_content(plot_id, job_id):
    """Create content for plot."""
    logging.debug(f"Create content for {plot_id}.")
    header, time_variable, file_name_template = plot_parameter[plot_id]
    element_list = [html.H2(header, style={"textAlign": "center"})]

    # Check if slider is needed
    logging.debug(f"Check if slider is needed for {plot_id}.")
    logging.debug(f"Time variable: {time_variable}")
    logging.debug(f"Predictors constant: {all_predictors_constant(job_id)}")
    if time_variable == "var_predictors" and all_predictors_constant(job_id):
        slider = False
    elif time_variable == "constant":
        slider = False
    else:
        slider = True

    logging.debug(f"Slider: {slider}")

    if slider:
        logging.debug("Create slider.")
        element_list.extend(
            [
                html.H3(children="Select time step", style={"textAlign": "center"}),
                create_slider(plot_id, job_id),
            ]
        )
    else:
        logging.debug("No slider needed.")

    image_name = get_image_name(job_id, plot_id, 0)
    img_url = url_for("result_file", job_id=job_id, file_name=image_name)

    element_list.append(
        html.Div(
            html.Div(
                html.Img(src=img_url, style={"width": "100%"}),
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
    "prediction{time_step}.png",
]
plot_parameter["crn"] = [
    "Measurements",
    "var_measurements",
    "measurements{time_step}.png",
]
plot_parameter["pred"] = [
    "Predictors",
    "var_predictors",
    "predictors{time_step}.png",
]
plot_parameter["pred-corr"] = [
    "Predictor Correlation",
    "var_predictors",
    "correlation_matrix{time_step}.png",
]
plot_parameter["pred-imp"] = [
    "Predictor Importance",
    "var_measurements",
    "predictor_importance{time_step}.png",
]
plot_parameter["pred-imp-ot"] = [
    "Predictor Importance over time",
    "constant",
    "predictor_importance_vs_days.png",
]
plot_parameter["pred-dist"] = [
    "Predictor Distance",
    "var_measurements",
    "prediction_distance{time_step}.png",
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
        Input("pred-dist-pill", "n_clicks"),
    )

    parameters = {}

    @staticmethod
    def function(pathname, *pill):
        """Render content on pill select."""
        job_id = pathname.split("/")[-1]
        try:
            cosmopolitan_job = CosmopolitanJob(job_id)
            if cosmopolitan_job.status not in ["COMPLETED", "FAILED"]:
                raise NotFinishedException(job_id)
        except (
            InvalidJobID,
            JobNotFound,
            NotSubmittedException,
            OperationalError,
            NotFinishedException,
        ) as e:
            return ("", error_response_dash(e), "")

        pill_clicked = ctx.triggered_id
        if pill_clicked is None:
            plot_id = next(iter(plot_parameter))
        else:
            plot_id = pill_clicked.replace("-pill", "")
        logging.debug(f"Render content for {job_id}.")

        return (
            job_id,
            create_content(plot_id, job_id),
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
            cosmopolitan_job = CosmopolitanJob(job_id)
            if cosmopolitan_job.status not in ["COMPLETED", "FAILED"]:
                logging.debug(f"Job {job_id} not finished GeneratePlotPerTimeStep.")
                raise NotFinishedException(job_id)
        except (
            InvalidJobID,
            JobNotFound,
            NotSubmittedException,
            OperationalError,
            NotFinishedException,
        ) as e:
            return ("", error_response_dash(e), "")

        plot_id = plot_id_tab.replace("-tab", "")
        image_name = get_image_name(
            job_id,
            plot_id,
            time_index,
        )
        img_url = url_for("result_file", job_id=job_id, file_name=image_name)
        return html.Img(src=img_url, style={"width": "100%"})


callbacks = list_callbacks(globals())
css_route = "/static/flatly_bootstrap.css"
base_path = "/results/"
if __name__ == "__main__":
    dictConfig(logging_config)
    stand_alone(app_layout, callbacks, css_route)
