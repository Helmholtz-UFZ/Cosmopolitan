"""Dash form for the cosmopolitan job."""

import logging
import os

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, callback_context, html
from dash.exceptions import PreventUpdate
from flask import url_for

from cosmopolitan_app.form_factory import (
    FormFactory,
    active_form_factory,
    active_form_template_factory,
    construct_selected_input,
)
from cosmopolitan_app.job import Job
from cosmopolitan_app.layouts import create_header

dash.register_page(
    __name__,
    path_template="/input/<job_id>",
)


def layout(job_id):
    """Layout for the input page."""
    logging.info(f"Create input page for job_id: {job_id}")
    job = Job(job_id=job_id)
    if job.status not in ["PENDING", "FAILED"]:
        if job.status == "RUNNING":
            header_mes = "Job is running. You can only spawn a new job."
        elif job.status == "COMPLETED":
            header_mes = "Job is completed. You can only spawn a new job."
        header = create_header(
            "Input",
            header_mes,
            bg_color="bg-danger",
        )
        base_path_submission = dash.page_registry["pages.input"]["path_template"]
        submission_path = base_path_submission.replace("<job_id>", str(job_id))
        return [
            header,
            dbc.Row(
                dbc.Col(
                    [
                        html.Div(
                            "You can find more information about your job in the submission page.",  # noqa
                        ),
                        html.A("Submission page", href=submission_path),
                    ],
                    className="col-11 col-xl-8 mx-auto",
                )
            ),
        ]

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

    header = create_header(
        "Input",
        "Define new input",
        bg_color="bg-info",
    )

    return [
        header,
        dbc.Row(
            dbc.Col(
                form_layout,
                id="form-container",
                className="col-11 col-xl-8 mx-auto",
            )
        ),
    ]


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
    },
    inputs=active_form_factory.produce_callback_inputs(),
    state={
        active_form_template_factory.job_id_key: Input(
            active_form_template_factory.job_id_key, "children"
        ),
    },
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
    active_form_factory.pymodel.job_id = state["job_id"]

    if triggered_id == active_form_factory.get_key_submit_button() and valid:
        logging.debug("Submit button clicked")
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
