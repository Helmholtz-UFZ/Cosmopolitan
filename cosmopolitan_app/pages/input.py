"""Configure your prediction job parameters and upload input data.

This page provides a comprehensive form where you can:
- Upload cosmic ray neutron sensor (CRNS) measurement data
- Upload predictor variable files (environmental data)
- Define your prediction area by drawing on a map or uploading boundaries
- Set time ranges and other prediction parameters
- Preview your prediction area before submission

The form validates your inputs and shows a live preview of the geographic area where
soil moisture will be predicted. Once all required data is provided and validated,
you can proceed to the submission page.

NOTE: This docstring is displayed on the documentation webpage.
"""

import logging
import os

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, callback_context, html
from dash.exceptions import PreventUpdate
from flask import url_for

from cosmopolitan_app.constants import (
    ERROR_MESSAGE_ID,
    ERROR_MODAL_ID,
    ERROR_TITLE_ID,
    INPUT_HEADER_ID,
    INPUT_JOB_ID_STORE,
    INPUT_MAIN_CONTENT_ID,
    LOADING_OVERLAY_ID,
    URL_ID,
)
from cosmopolitan_app.form_factory import (
    FormFactory,
    active_form_factory,
    active_form_template_factory,
    construct_selected_input,
)
from cosmopolitan_app.job import Job
from cosmopolitan_app.layouts import landing_page_layout_column
from cosmopolitan_app.utils import swap_classes

dash.register_page(
    __name__,
    path_template="/input/<job_id>",
)


def layout(job_id):
    """Layout for input page."""
    return landing_page_layout_column(
        "Input", INPUT_HEADER_ID, INPUT_JOB_ID_STORE, job_id, INPUT_MAIN_CONTENT_ID
    )


@callback(
    [
        Output(INPUT_HEADER_ID, "className", allow_duplicate=True),
        Output(f"{INPUT_HEADER_ID}-subtitle", "children"),
        Output(INPUT_MAIN_CONTENT_ID, "children"),
    ],
    [Input(INPUT_JOB_ID_STORE, "data")],
    [State(INPUT_HEADER_ID, "className")],
    prevent_initial_call="initial_duplicate",
)
def load_submission_content(job_id, header_class_name):
    """Load the main submission content triggered by job-id-store."""
    logging.info(
        f"Loading submission content for job {job_id}", extra={"tag": "job_submission"}
    )
    job = Job(job_id)
    logging.debug(job.start_date)

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
        logging.info(
            "No preview path found, generating new preview.", extra={"tag": "frontend"}
        )
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
    logging.info("Regenerate preview", extra={"tag": "frontend"})
    job_id = state["job_id"]

    try:
        active_form_factory.set_model(state)
    except ValueError:
        logging.debug("Model not valid", extra={"tag": "frontend"})
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
        "redirect": Output(URL_ID, "pathname"),
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
    logging.info("Form manager", extra={"tag": "frontend"})

    file_upload_error = {}

    triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0]
    logging.debug(f"Triggered id: {triggered_id}", extra={"tag": "frontend"})

    if triggered_id == active_form_factory.get_id_delete_button("crns_upload"):
        job_id = state["job_id"]
        job = Job(job_id=job_id)
        logging.debug("Delete CRNS button clicked", extra={"tag": "frontend"})
        job.delete_input_files("crn")
        active_form_factory.set_file_information(state, {}, "crns_upload")
    elif triggered_id == active_form_factory.get_id_delete_button("predictor_upload"):
        job_id = state["job_id"]
        job = Job(job_id=job_id)
        logging.debug("Delete predictor button clicked", extra={"tag": "frontend"})
        job.delete_input_files("pred")
        active_form_factory.set_file_information(state, {}, "predictor_upload")
    elif triggered_id == active_form_factory.get_id_input_file_content("crns_upload"):
        job_id = state["job_id"]
        job = Job(job_id=job_id)
        logging.debug("CRNS file uploaded", extra={"tag": "job_submission"})
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
        logging.debug("Predictor file(s) uploaded", extra={"tag": "job_submission"})
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

    output_dict["error_modal"] = False
    output_dict["error_title"] = ""
    output_dict["error_message"] = ""
    output_dict["loading_overlay"] = False
    active_form_factory.pymodel.job_id = state["job_id"]

    if triggered_id == active_form_factory.get_key_submit_button() and valid:
        logging.debug("Submit button clicked", extra={"tag": "job_submission"})
        job = Job(model=active_form_factory.pymodel)
        job.prepare_input_files()
        submission_base_path = dash.page_registry["pages.submission"]["path_template"]
        output_dict["redirect"] = submission_base_path.replace(
            "<job_id>", str(job.job_id)
        )
    else:
        output_dict["redirect"] = dash.no_update

    output_dict["selected_predictors"] = construct_selected_input(
        active_form_factory.pymodel, "predictor_upload"
    )
    output_dict["selected_crns"] = construct_selected_input(
        active_form_factory.pymodel, "crns_upload"
    )

    return output_dict
