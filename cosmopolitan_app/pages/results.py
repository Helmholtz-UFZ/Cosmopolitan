"""Results page for Cosmopolitan App."""

import glob
import logging
import os
from collections import OrderedDict

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html
from flask import url_for

from cosmopolitan_app.config import JOB_WORK_DIR_TEMPLATE
from cosmopolitan_app.job import Job
from cosmopolitan_app.layouts import create_header
from cosmopolitan_app.utils import InvalidJobID, JobNotFound

dash.register_page(
    __name__,
    path_template="/results/<job_id>",
)


def get_time_steps(job_id):
    """Get time steps for job."""
    job_work_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=job_id)
    files = glob.glob(f"{job_work_dir}/measurements_*")
    time_steps = []
    for file in files:
        file_name = os.path.basename(file)
        time_step = file_name.replace("measurements_", "").split(".")[0]
        time_steps.append(time_step)

    return time_steps


def create_slider(job_id):
    """Create dash slider for time steps."""
    time_steps = get_time_steps(job_id)
    number_time_steps = len(time_steps)
    size_slider = min(max(int(number_time_steps * 0.8), 3), 12)
    return dbc.Row(
        dbc.Col(
            dcc.Slider(
                id="slider_results",
                min=1,
                max=number_time_steps,
                step=1,
                value=1,
                marks=dict(enumerate(time_steps, start=1)),
                disabled=number_time_steps <= 1,
            ),
            className=f"mt-4 col-{size_slider}",
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


plot_parameter = OrderedDict()
plot_parameter["sm_pred"] = [
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
plot_parameter["pred_corr"] = [
    "Predictor Correlation",
    "var_predictors",
    "correlation_matrix{time_step}.png",
]
plot_parameter["pred_imp"] = [
    "Predictor Importance",
    "var_measurements",
    "predictor_importance{time_step}.png",
]
plot_parameter["pred_imp_ot"] = [
    "Predictor Importance over time",
    "constant",
    "predictor_importance_vs_days.png",
]
plot_parameter["pred_dist"] = [
    "Predictor Distance",
    "var_measurements",
    "prediction_distance{time_step}.png",
]


def layout(job_id):
    """Layout for the submission page."""
    logging.info(f"Create result page for job {job_id}")
    try:
        job = Job(job_id)
    except (JobNotFound, InvalidJobID):
        logging.info(f"Job {job_id} not found")
        return html.Div(
            [
                create_header("Error", "Job not found"),
                html.P("The job you are looking for does not exist."),
            ]
        )

    header = create_header(
        "Results", job.job_id, bg_color="bg-info", id="results_header"
    )

    start_plot_id = "sm_pred"
    plot_header_title, time_variable, file_name_template = plot_parameter[start_plot_id]

    image_name = get_image_name(job_id, start_plot_id, 0)
    img_url = url_for("serve_file", job_id=job_id, filename=image_name)

    submission_path = dash.page_registry["pages.submission"]["path_template"]
    submission_url = submission_path.replace("<job_id>", str(job_id))

    submission_button = dcc.Link(
        dbc.Button("Back to Submission", color="primary", className="mt-3"),
        href=submission_url,
    )

    pill_group = html.Div(
        dbc.RadioItems(
            id="plot_pill_group",
            className="btn-group",
            inputClassName="btn-check",
            labelClassName="btn btn-outline-primary",
            labelCheckedClassName="active",
            options=[{"label": v[0], "value": k} for k, v in plot_parameter.items()],
            value=start_plot_id,
        ),
        className="radio-group",
    )

    return [
        header,
        dbc.Card(
            [
                dbc.CardHeader(
                    [
                        html.H3("Select Plot"),
                        pill_group,
                        submission_button,
                    ],
                    className="text-center pb-4",
                ),
                dbc.CardBody(
                    [
                        html.H2(
                            plot_header_title,
                            id="plot_header",
                            style={"textAlign": "center"},
                        ),
                        create_slider(job_id),
                        dbc.Row(
                            dbc.Col(
                                html.Img(
                                    src=img_url, id="plot_img", style={"width": "100%"}
                                ),
                                className="col-12 col-xl-9",
                            ),
                            className="row justify-content-center",
                        ),
                    ]
                ),
            ],
            className="rounded-0",
        ),
    ]


@callback(
    Output("plot_header", "children"),
    Output("plot_img", "src"),
    Output("slider_results", "disabled"),
    Input("plot_pill_group", "value"),
    Input("slider_results", "value"),
    State("url", "pathname"),
    prevent_initial_call=True,
)
def image_swap(plot_id, time_index, pathname):
    """Swap image on button click."""
    logging.info(f"Swap image to {plot_id} with time index {time_index}")
    job_id = pathname.split("/")[-1]
    image_name = get_image_name(job_id, plot_id, time_index - 1)
    img_url = url_for("serve_file", job_id=job_id, filename=image_name)

    plot_header_title = plot_parameter[plot_id][0]
    time_variable = plot_parameter[plot_id][1]

    # Check if slider is needed
    if time_variable == "var_predictors" and all_predictors_constant(job_id):
        disable_slider = True
    elif time_variable == "constant":
        disable_slider = True
    else:
        disable_slider = False

    return plot_header_title, img_url, disable_slider
