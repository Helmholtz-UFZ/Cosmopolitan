"""Dash form for the cosmopolitan job."""

import logging
import os

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, callback_context
from dash.exceptions import PreventUpdate
from flask import url_for

from cosmopolitan_app.form_factory import (
    FormFactory,
    FormTemplateFactory,
    construct_selected_input,
)
from cosmopolitan_app.job import Job
from cosmopolitan_app.layouts import create_header
from cosmopolitan_app.pydantic_models import ModelWebsite

dash.register_page(__name__)

form_template_factory = FormTemplateFactory(active=True)
form_template = form_template_factory.generate_template()
form_factory = FormFactory(ModelWebsite, form_template)


def layout():
    """Layout for the input page."""
    logging.info("Create input page")
    job = Job()

    preview_path = job.get_preview_path()
    preview_file_name = os.path.basename(preview_path)
    preview_src = url_for("serve_file", job_id=job.job_id, filename=preview_file_name)

    form_template_factory.preview_src = preview_src
    form_template_factory.job_id = job.job_id
    form_template = form_template_factory.generate_template()

    form_factory.new_layout(form_template)

    form_layout = form_factory.generate_form()

    header = create_header(
        "Input",
        "Define new input",
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
        form_template_factory.area_preview_key: Output(
            form_template_factory.area_preview_key, "src"
        )
    },
    state={
        **form_factory.produce_callback_inputs(use_state=True),
        form_template_factory.job_id_key: Input(
            form_template_factory.job_id_key, "children"
        ),
    },
    inputs={
        form_template_factory.new_area_preview_key: Input(
            form_template_factory.new_area_preview_key, "n_clicks"
        )
    },
)
def regenerate_preview(**state):
    """Regenerate the preview."""
    logging.info("Regenerate preview")
    job_id = state["job_id"]

    try:
        form_factory.set_model(state)
    except ValueError:
        logging.debug("Model not valid")
        raise PreventUpdate

    form_factory.pymodel.job_id = job_id
    job = Job(model=form_factory.pymodel)
    file_name = job.preview_area()
    image_src = url_for("serve_file", job_id=job.job_id, filename=file_name)

    return {"area_preview": image_src}


@callback(
    output={
        **form_factory.produce_callback_outputs(),
        form_template_factory.selected_crns_key: Output(
            form_template_factory.selected_crns_key, "children"
        ),
        form_template_factory.selected_predictors_key: Output(
            form_template_factory.selected_predictors_key, "children"
        ),
        "redirect": Output("url", "pathname"),
    },
    inputs=form_factory.produce_callback_inputs(),
    state={
        form_template_factory.job_id_key: Input(
            form_template_factory.job_id_key, "children"
        ),
    },
)
def form_manager(**state):
    """Wrap all input logic of the form into one callback."""
    logging.info("Form manager")

    job_id = state["job_id"]
    job = Job(job_id=job_id)
    file_upload_error = {}

    triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0]
    logging.debug(f"Triggered id: {triggered_id}")
    if triggered_id == form_factory.get_id_delete_button("crns_upload"):
        logging.debug("Delete CRNS button clicked")
        job.delete_input_files("crn")
        form_factory.set_file_information(state, {}, "crns_upload")
    elif triggered_id == form_factory.get_id_delete_button("predictor_upload"):
        logging.debug("Delete predictor button clicked")
        job.delete_input_files("pred")
        form_factory.set_file_information(state, {}, "predictor_upload")
    elif triggered_id == form_factory.get_id_input_file_content("crns_upload"):
        logging.debug("CRNS file uploaded")
        job.delete_input_files("crn")

        file_name, file_content = form_factory.get_file_content(state, "crns_upload")
        try:
            file_name, file_information = job.safe_input_file(
                file_name, file_content, "crn", upload=True
            )
        except ValueError as e:
            file_upload_error["crns_upload"] = str(e)

        form_factory.set_file_information(
            state, {file_name: file_information}, "crns_upload"
        )

    elif triggered_id == form_factory.get_id_input_file_content("predictor_upload"):
        logging.debug("Predictor file(s) uploaded")
        job.delete_input_files("pred")

        uploaded_file_information = {}
        try:
            for file_name, content in zip(
                *form_factory.get_file_content(state, "predictor_upload")
            ):
                file_name, file_information = job.safe_input_file(
                    file_name, content, "pred", upload=True
                )
                uploaded_file_information[file_name] = file_information
        except ValueError as e:
            file_upload_error["predictor_upload"] = str(e)

        form_factory.set_file_information(
            state, uploaded_file_information, "predictor_upload"
        )

    valid, output_dict = form_factory.validate_callback(state, file_upload_error)
    form_factory.pymodel.job_id = job.job_id

    if triggered_id == form_factory.get_key_submit_button() and valid:
        logging.debug("Submit button clicked")
        job = Job(model=form_factory.pymodel)
        job.prepare_input_files()
        output_dict["redirect"] = f"/submission/{job.job_id}"
    else:
        output_dict["rerirect"] = dash.no_update

    output_dict["selected_predictors"] = construct_selected_input(
        form_factory.pymodel, "predictor_upload"
    )
    output_dict["selected_crns"] = construct_selected_input(
        form_factory.pymodel, "crns_upload"
    )

    return output_dict
