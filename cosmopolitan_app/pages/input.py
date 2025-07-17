"""Dash form for the cosmopolitan job."""

import logging
import os

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, callback_context, dcc, html
from dash.exceptions import PreventUpdate
from flask import url_for

from cosmopolitan_app.constants import (
    ERROR_MESSAGE_ID,
    ERROR_MODAL_ID,
    ERROR_TITLE_ID,
    INPUT_HEADER_ID,
    LOADING_OVERLAY_ID,
)
from cosmopolitan_app.error_handling import error_responds_dict
from cosmopolitan_app.form_factory import (
    FormFactory,
    active_form_factory,
    active_form_template_factory,
    construct_selected_input,
)
from cosmopolitan_app.job import Job, NoMeasurementPointsError
from cosmopolitan_app.layouts import create_header
from cosmopolitan_app.utils import InvalidJobID, JobNotFound, swap_classes

dash.register_page(
    __name__,
    path_template="/input/<job_id>",
)


def layout(job_id):
    """Create static layout for the submission page."""
    header = create_header(
        "Input", "Loading ...", bg_color="bg-secondary", id=INPUT_HEADER_ID
    )

    return [
        dcc.Store(id="job-id-store", data=job_id),
        header,
        html.Div(
            dbc.Container(
                dbc.Row(
                    dbc.Col(
                        dbc.Spinner(
                            size="lg",
                            color="primary",
                            type="border",
                            fullscreen=False,
                        ),
                        className="d-flex justify-content-center align-items-center",
                    ),
                    style={"height": "100vh"},
                ),
                fluid=True,
                style={"height": "100vh"},
            ),
            id="input_content",
        ),
    ]


@callback(
    [
        Output(INPUT_HEADER_ID, "className", allow_duplicate=True),
        Output(f"{INPUT_HEADER_ID}-subtitle", "children"),
        Output("input_content", "children"),
    ],
    [Input("job-id-store", "data")],
    [State(INPUT_HEADER_ID, "className")],
    prevent_initial_call="initial_duplicate",
)
def load_submission_content(job_id, header_class_name):
    """Load the main submission content triggered by job-id-store."""
    logging.info(f"Loading submission content for job {job_id}")
    try:
        job = Job(job_id)
    except (JobNotFound, InvalidJobID):
        logging.info(f"Job {job_id} not found")
        content = dbc.Row(
            dbc.Col(
                [
                    html.Div(
                        "The job you are looking for does not exist.",
                    ),
                ],
                className="col-11 col-xl-8 mx-auto",
            )
        )
        header_class_name = swap_classes("bg-danger", header_class_name)
        header_subtitle = "Job Not Found"
        return header_class_name, header_subtitle, content

    if job.status not in ["PENDING", "FAILED"]:
        if job.status == "RUNNING":
            header_subtitle = "Job is running. You can only spawn a new job."
        elif job.status == "COMPLETED":
            header_subtitle = "Job is completed. You can only spawn a new job."
        header_class_name = swap_classes("bg-danger", header_class_name)

        base_path_submission = dash.page_registry["pages.input"]["path_template"]
        submission_path = base_path_submission.replace("<job_id>", str(job_id))
        content = dbc.Row(
            dbc.Col(
                [
                    html.Div(
                        "You can find more information about your job in the submission page.",  # noqa
                    ),
                    html.A("Submission page", href=submission_path),
                ],
                className="col-11 col-xl-8 mx-auto",
            )
        )
        return header_class_name, header_subtitle, content

    header_subtitle = job.job_id
    header_class_name = swap_classes("bg-info", header_class_name)
    preview_path = job.get_preview_path()
    if preview_path is None:
        logging.info("No preview path found, generating new preview.")
        job.preview_area()
        preview_path = job.get_preview_path()
    preview_file_name = os.path.basename(preview_path)
    preview_src = url_for("serve_file", job_id=job.job_id, filename=preview_file_name)

    active_form_template_factory.preview_src = preview_src
    active_form_template_factory.job_id = job.job_id
    active_form_template = active_form_template_factory.generate_template()

    active_form_factory = FormFactory(job.model, active_form_template)

    form_layout = active_form_factory.generate_form()
    content = dbc.Row(
        dbc.Col(
            form_layout,
            id="form-container",
            className="col-11 col-xl-8 mx-auto",
        )
    )

    return header_class_name, header_subtitle, content


@callback(
    Output(LOADING_OVERLAY_ID, "is_open", allow_duplicate=True),
    Input(active_form_factory.get_key_submit_button(), "n_clicks"),
    prevent_initial_call=True,
)
def show_loading(n_clicks):
    """Show loading overlay when preparing input."""
    if n_clicks:
        return True
    return False


@callback(
    output={
        active_form_template_factory.area_preview_key: Output(
            active_form_template_factory.area_preview_key, "src"
        )
    },
    state={
        **active_form_factory.produce_callback_inputs(use_state=True),
        active_form_template_factory.job_id_key: Input(
            active_form_template_factory.job_id_key, "children"
        ),
    },
    inputs={
        active_form_template_factory.new_area_preview_key: Input(
            active_form_template_factory.new_area_preview_key, "n_clicks"
        )
    },
)
def regenerate_preview(**state):
    """Regenerate the preview."""
    logging.info("Regenerate preview")
    job_id = state["job_id"]

    try:
        active_form_factory.set_model(state)
    except ValueError:
        logging.debug("Model not valid")
        raise PreventUpdate

    active_form_factory.pymodel.job_id = job_id
    job = Job(model=active_form_factory.pymodel)
    file_name = job.preview_area()
    image_src = url_for("serve_file", job_id=job.job_id, filename=file_name)

    return {"area_preview": image_src}


@callback(
    output={
        **active_form_factory.produce_callback_outputs(),
        active_form_template_factory.selected_crns_key: Output(
            active_form_template_factory.selected_crns_key, "children"
        ),
        active_form_template_factory.selected_predictors_key: Output(
            active_form_template_factory.selected_predictors_key, "children"
        ),
        "redirect": Output("url", "pathname"),
        "loading_overlay": Output(LOADING_OVERLAY_ID, "is_open", allow_duplicate=True),
        "error_message": Output(ERROR_MESSAGE_ID, "children", allow_duplicate=True),
        "error_title": Output(ERROR_TITLE_ID, "children", allow_duplicate=True),
        "error_modal": Output(ERROR_MODAL_ID, "is_open", allow_duplicate=True),
    },
    inputs=active_form_factory.produce_callback_inputs(),
    state={
        active_form_template_factory.job_id_key: Input(
            active_form_template_factory.job_id_key, "children"
        ),
    },
    prevent_initial_call="initial_duplicate",
)
def form_manager(**state):
    """Wrap all input logic of the form into one callback."""
    logging.info("Form manager")

    file_upload_error = {}

    triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0]
    logging.debug(f"Triggered id: {triggered_id}")

    if triggered_id == active_form_factory.get_id_delete_button("crns_upload"):
        job_id = state["job_id"]
        job = Job(job_id=job_id)
        logging.debug("Delete CRNS button clicked")
        job.delete_input_files("crn")
        active_form_factory.set_file_information(state, {}, "crns_upload")
    elif triggered_id == active_form_factory.get_id_delete_button("predictor_upload"):
        job_id = state["job_id"]
        job = Job(job_id=job_id)
        logging.debug("Delete predictor button clicked")
        job.delete_input_files("pred")
        active_form_factory.set_file_information(state, {}, "predictor_upload")
    elif triggered_id == active_form_factory.get_id_input_file_content("crns_upload"):
        job_id = state["job_id"]
        job = Job(job_id=job_id)
        logging.debug("CRNS file uploaded")
        job.delete_input_files("crn")

        file_name, file_content = active_form_factory.get_file_content(
            state, "crns_upload"
        )
        try:
            file_name, file_information = job.safe_input_file(
                file_name, file_content, "crn", upload=True
            )
            active_form_factory.set_file_information(
                state, {file_name: file_information}, "crns_upload"
            )
        except ValueError as e:
            file_upload_error["crns_upload"] = str(e)
    elif triggered_id == active_form_factory.get_id_input_file_content(
        "predictor_upload"
    ):
        job_id = state["job_id"]
        job = Job(job_id=job_id)
        logging.debug("Predictor file(s) uploaded")
        job.delete_input_files("pred")

        uploaded_file_information = {}
        try:
            for file_name, content in zip(
                *active_form_factory.get_file_content(state, "predictor_upload")
            ):
                file_name, file_information = job.safe_input_file(
                    file_name, content, "pred", upload=True
                )
                uploaded_file_information[file_name] = file_information

            active_form_factory.set_file_information(
                state, uploaded_file_information, "predictor_upload"
            )
        except ValueError as e:
            file_upload_error["predictor_upload"] = str(e)

    valid, output_dict = active_form_factory.validate_callback(state, file_upload_error)
    print(output_dict)

    output_dict["error_modal"] = False
    output_dict["error_title"] = ""
    output_dict["error_message"] = ""
    output_dict["loading_overlay"] = False
    active_form_factory.pymodel.job_id = state["job_id"]

    if triggered_id == active_form_factory.get_key_submit_button() and valid:
        logging.debug("Submit button clicked")
        job = Job(model=active_form_factory.pymodel)
        try:
            job.prepare_input_files()
            submission_base_path = dash.page_registry["pages.submission"][
                "path_template"
            ]
            output_dict["redirect"] = submission_base_path.replace(
                "<job_id>", str(job.job_id)
            )
        except NoMeasurementPointsError as error:
            output_dict["error_modal"] = True
            output_dict["error_title"] = error_responds_dict[type(error)][0]
            output_dict["error_message"] = error_responds_dict[type(error)][1]
            output_dict["redirect"] = dash.no_update
    else:
        output_dict["redirect"] = dash.no_update

    output_dict["selected_predictors"] = construct_selected_input(
        active_form_factory.pymodel, "predictor_upload"
    )
    print(active_form_factory.pymodel)
    print(output_dict["selected_predictors"])
    output_dict["selected_crns"] = construct_selected_input(
        active_form_factory.pymodel, "crns_upload"
    )
    print(output_dict["selected_crns"])

    return output_dict
