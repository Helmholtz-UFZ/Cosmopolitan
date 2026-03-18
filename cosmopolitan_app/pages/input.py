"""Configure your prediction job parameters and upload input data.

This page provides a comprehensive form where you can:
- Upload cosmic ray neutron sensor (CRNS) measurement data
- Upload predictor variable files (environmental data)
- Define your prediction area by specifying geographic coordinates
- Set time ranges and other prediction parameters
- Preview your prediction area before submission

The form validates your inputs and shows a live preview of the geographic area where
soil moisture will be predicted. Once all required data is provided and validated,
you can proceed to the submission page.

NOTE: This docstring is displayed on the documentation webpage.
"""

import json
import logging
import os

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, callback_context, html
from dash.exceptions import PreventUpdate
from dash_form_factory import FormFactory
from flask import url_for
from soil_moisture_prediction.pydantic_models import PredictorInformation

from cosmopolitan_app.constants import (
    CHECK_INPUT_BUTTON_INPUT_ID,
    CRNS_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID,
    CRNS_UPLOAD_INPUT_ID,
    DELETE_CRNS_UPLOAD_BUTTON_INPUT_ID,
    DELETE_PREDICTOR_UPLOAD_BUTTON_INPUT_ID,
    HEADER_DIV_INPUT_ID,
    HEADER_SUBTITLE_DIV_INPUT_ID,
    HIDDEN_CRNS_UPLOAD_INPUT_INPUT_ID,
    HIDDEN_PREDICTOR_UPLOAD_INPUT_INPUT_ID,
    JOB_STORE_INPUT_ID,
    LOADING_OVERLAY_MODAL_SHARED_ID,
    MAIN_CONTENT_DIV_INPUT_ID,
    PREDICTOR_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID,
    PREDICTOR_UPLOAD_INPUT_ID,
    URL_LOCATION_SHARED_ID,
)
from cosmopolitan_app.form_template_factory import (
    FormTemplateFactory,
    active_form_factory,
    active_form_template_factory,
    construct_selected_input,
)
from cosmopolitan_app.job import Job
from cosmopolitan_app.layouts import landing_page_layout_column
from cosmopolitan_app.pydantic_models import ModelWebsite
from cosmopolitan_app.utils import swap_classes

log = logging.getLogger(__name__)

dash.register_page(
    __name__,
    path_template="/input/<job_id>",
)


def preprocess_form_data(form_data: dict) -> None:
    """Transform raw form state into clean model dict.

    Mutates form_data in-place. Reads hidden inputs for file uploads,
    deserializes JSON, and injects predictors, soil_moisture_data,
    predictor_upload, and crns_upload so set_model() can pick them up
    via the generic path.
    """
    hidden_pred = form_data[HIDDEN_PREDICTOR_UPLOAD_INPUT_INPUT_ID]
    predictor_upload_raw = json.loads(hidden_pred) if hidden_pred.strip() else {}
    predictor_upload = {}
    for key, value in predictor_upload_raw.items():
        predictor_upload[value["predictor_name"]] = PredictorInformation(
            **{k: v for k, v in value.items() if k in PredictorInformation.model_fields}
        )

    hidden_crns = form_data[HIDDEN_CRNS_UPLOAD_INPUT_INPUT_ID]
    crns_upload = json.loads(hidden_crns) if hidden_crns.strip() else {}
    try:
        soil_moisture_data = list(crns_upload.keys())[0]
    except IndexError:
        soil_moisture_data = ""

    predictors = dict.fromkeys(form_data["pred_streams"]) | predictor_upload

    form_data["predictors"] = predictors
    form_data["soil_moisture_data"] = soil_moisture_data
    form_data["predictor_upload"] = predictor_upload_raw
    form_data["crns_upload"] = crns_upload


def build_display_model(form_data: dict, job_id: str) -> ModelWebsite:
    """Construct a ModelWebsite from preprocessed form_data without validators.

    Used for display purposes only (e.g. construct_selected_input).
    Do NOT pass the result to Job() — use a validated model instead.
    """
    model_dict = {}
    for field_name in ModelWebsite.model_fields:
        field_type = ModelWebsite.model_fields[field_name].json_schema_extra["type"]
        if field_type == "date-picker":
            model_dict[field_name] = (
                form_data[f"{field_name}_start_date"],
                form_data[f"{field_name}_end_date"],
            )
        else:
            try:
                model_dict[field_name] = form_data[field_name]
            except KeyError:
                pass
    model = ModelWebsite.model_construct(**model_dict)
    model.__dict__["job_id"] = job_id
    return model


def layout(job_id):
    """Layout for input page."""
    return landing_page_layout_column(
        "Input",
        HEADER_DIV_INPUT_ID,
        JOB_STORE_INPUT_ID,
        job_id,
        MAIN_CONTENT_DIV_INPUT_ID,
    )


@callback(
    [
        Output(HEADER_DIV_INPUT_ID, "className", allow_duplicate=True),
        Output(HEADER_SUBTITLE_DIV_INPUT_ID, "children"),
        Output(MAIN_CONTENT_DIV_INPUT_ID, "children"),
    ],
    [Input(JOB_STORE_INPUT_ID, "data")],
    [State(HEADER_DIV_INPUT_ID, "className")],
    prevent_initial_call="initial_duplicate",
)
def load_submission_content(job_id, header_class_name):
    """Load the main submission content triggered by job-id-store."""
    log.info(f"Loading submission content for job {job_id}")
    job = Job(job_id)
    log.debug(job.start_date)

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
        log.info("No preview path found, generating new preview.")
        job.preview_area()
        preview_path = job.get_preview_path()
    preview_file_name = os.path.basename(preview_path)
    preview_src = url_for("serve_file", job_id=job.job_id, filename=preview_file_name)

    template_factory = FormTemplateFactory(
        job_id=job.job_id,
        active=True,
        preview_src=preview_src,
        model=job.model,
    )
    form_layout = template_factory.generate_template()
    factory = FormFactory(job.model, form_layout)
    form = factory.process_layout(factory.layout)

    content = dbc.Row(
        dbc.Col(
            form,
            className="col-11 col-xl-8 mx-auto",
        )
    )

    return header_class_name, header_subtitle, content


# Clientside callback: open loading overlay instantly in the browser.
dash.clientside_callback(
    "function(n) { return !!n; }",
    Output(LOADING_OVERLAY_MODAL_SHARED_ID, "is_open", allow_duplicate=True),
    Input(CHECK_INPUT_BUTTON_INPUT_ID, "n_clicks"),
    prevent_initial_call=True,
)


# ---------------------------------------------------------------------------
# File upload callback
# ---------------------------------------------------------------------------


@callback(
    output={
        HIDDEN_CRNS_UPLOAD_INPUT_INPUT_ID: Output(
            HIDDEN_CRNS_UPLOAD_INPUT_INPUT_ID, "value"
        ),
        HIDDEN_PREDICTOR_UPLOAD_INPUT_INPUT_ID: Output(
            HIDDEN_PREDICTOR_UPLOAD_INPUT_INPUT_ID, "value"
        ),
        CRNS_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID: Output(
            CRNS_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID, "children", allow_duplicate=True
        ),
        PREDICTOR_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID: Output(
            PREDICTOR_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID,
            "children",
            allow_duplicate=True,
        ),
    },
    inputs={
        "crns_upload_contents": Input(CRNS_UPLOAD_INPUT_ID, "contents"),
        "predictor_upload_contents": Input(PREDICTOR_UPLOAD_INPUT_ID, "contents"),
        DELETE_CRNS_UPLOAD_BUTTON_INPUT_ID: Input(
            DELETE_CRNS_UPLOAD_BUTTON_INPUT_ID, "n_clicks"
        ),
        DELETE_PREDICTOR_UPLOAD_BUTTON_INPUT_ID: Input(
            DELETE_PREDICTOR_UPLOAD_BUTTON_INPUT_ID, "n_clicks"
        ),
    },
    state={
        "crns_upload_filename": State(CRNS_UPLOAD_INPUT_ID, "filename"),
        "predictor_upload_filename": State(PREDICTOR_UPLOAD_INPUT_ID, "filename"),
        HIDDEN_CRNS_UPLOAD_INPUT_INPUT_ID: State(
            HIDDEN_CRNS_UPLOAD_INPUT_INPUT_ID, "value"
        ),
        HIDDEN_PREDICTOR_UPLOAD_INPUT_INPUT_ID: State(
            HIDDEN_PREDICTOR_UPLOAD_INPUT_INPUT_ID, "value"
        ),
        # fmt: off
        active_form_template_factory.job_id_key: State(  # nocheck
            active_form_template_factory.job_id_key,
            "children",  # nocheck
        ),
        # fmt: on
    },
    prevent_initial_call=True,
)
def file_upload_callback(**state):
    """Handle file upload and delete actions."""
    log.info("File upload callback")

    triggered_ids = {
        t["prop_id"].split(".")[0]
        for t in callback_context.triggered
        if t["value"] is not None
    }
    log.debug(f"File upload triggered by: {triggered_ids}")

    job_id = state["job_id"]

    output_dict = {
        HIDDEN_CRNS_UPLOAD_INPUT_INPUT_ID: state[HIDDEN_CRNS_UPLOAD_INPUT_INPUT_ID],
        HIDDEN_PREDICTOR_UPLOAD_INPUT_INPUT_ID: state[
            HIDDEN_PREDICTOR_UPLOAD_INPUT_INPUT_ID
        ],
        CRNS_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID: "",
        PREDICTOR_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID: "",
    }

    if DELETE_CRNS_UPLOAD_BUTTON_INPUT_ID in triggered_ids:
        job = Job(job_id=job_id)
        log.debug("Delete CRNS button clicked")
        job.delete_input_files("crn")
        output_dict[HIDDEN_CRNS_UPLOAD_INPUT_INPUT_ID] = json.dumps({})

    elif DELETE_PREDICTOR_UPLOAD_BUTTON_INPUT_ID in triggered_ids:
        job = Job(job_id=job_id)
        log.debug("Delete predictor button clicked")
        job.delete_input_files("pred")
        output_dict[HIDDEN_PREDICTOR_UPLOAD_INPUT_INPUT_ID] = json.dumps({})

    elif CRNS_UPLOAD_INPUT_ID in triggered_ids:
        job = Job(job_id=job_id)
        log.debug("CRNS file uploaded")
        job.delete_input_files("crn")
        file_name = state["crns_upload_filename"]
        file_content = state["crns_upload_contents"]
        try:
            file_name, file_information = job.safe_input_file(
                file_name, file_content, "crn", upload=True
            )
            output_dict[HIDDEN_CRNS_UPLOAD_INPUT_INPUT_ID] = json.dumps(
                {file_name: file_information}
            )
        except ValueError as e:
            output_dict[CRNS_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID] = str(e)

    elif PREDICTOR_UPLOAD_INPUT_ID in triggered_ids:
        job = Job(job_id=job_id)
        log.debug("Predictor file(s) uploaded")
        job.delete_input_files("pred")
        file_names = state["predictor_upload_filename"]
        file_contents = state["predictor_upload_contents"]
        uploaded_file_information = {}
        try:
            for file_name, content in zip(file_names, file_contents):
                file_name, file_information = job.safe_input_file(
                    file_name, content, "pred", upload=True
                )
                uploaded_file_information[file_name] = file_information
            output_dict[HIDDEN_PREDICTOR_UPLOAD_INPUT_INPUT_ID] = json.dumps(
                uploaded_file_information
            )
        except ValueError as e:
            output_dict[PREDICTOR_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID] = str(e)

    return output_dict


# ---------------------------------------------------------------------------
# Preview callback
# ---------------------------------------------------------------------------


@callback(
    output={
        # fmt: off
        active_form_template_factory.area_preview_key: Output(  # nocheck
            active_form_template_factory.area_preview_key,
            "src",  # nocheck
        ),
        # fmt: on
    },
    state={
        **active_form_factory.produce_callback_inputs(use_state=True),
        HIDDEN_CRNS_UPLOAD_INPUT_INPUT_ID: State(
            HIDDEN_CRNS_UPLOAD_INPUT_INPUT_ID, "value"
        ),
        HIDDEN_PREDICTOR_UPLOAD_INPUT_INPUT_ID: State(
            HIDDEN_PREDICTOR_UPLOAD_INPUT_INPUT_ID, "value"
        ),
        # fmt: off
        active_form_template_factory.job_id_key: State(  # nocheck
            active_form_template_factory.job_id_key,
            "children",  # nocheck
        ),
        # fmt: on
    },
    inputs={
        # fmt: off
        active_form_template_factory.new_area_preview_key: Input(  # nocheck
            active_form_template_factory.new_area_preview_key,
            "n_clicks",  # nocheck
        ),
        # fmt: on
    },
)
def regenerate_preview(**state):
    """Regenerate the preview."""
    log.info("Regenerate preview")
    job_id = state["job_id"]

    preprocess_form_data(state)
    try:
        validated_model = active_form_factory.set_model(state)
    except ValueError:
        log.debug("Model not valid")
        raise PreventUpdate

    validated_model.__dict__["job_id"] = job_id
    job = Job(model=validated_model)
    file_name = job.preview_area()
    image_src = url_for("serve_file", job_id=job.job_id, filename=file_name)

    return {"area_preview": image_src}


# ---------------------------------------------------------------------------
# Form validation callback
# ---------------------------------------------------------------------------


@callback(
    output={
        **active_form_factory.produce_callback_outputs(),
        CRNS_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID: Output(
            CRNS_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID, "children", allow_duplicate=True
        ),
        PREDICTOR_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID: Output(
            PREDICTOR_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID,
            "children",
            allow_duplicate=True,
        ),
        # fmt: off
        active_form_template_factory.selected_crns_key: Output(  # nocheck
            active_form_template_factory.selected_crns_key,
            "children",  # nocheck
        ),
        active_form_template_factory.selected_predictors_key: Output(  # nocheck
            active_form_template_factory.selected_predictors_key,
            "children",  # nocheck
        ),
        # fmt: on
        "redirect": Output(URL_LOCATION_SHARED_ID, "pathname"),
        "loading_overlay": Output(
            LOADING_OVERLAY_MODAL_SHARED_ID, "is_open", allow_duplicate=True
        ),
    },
    inputs={
        **active_form_factory.produce_callback_inputs(),
        HIDDEN_CRNS_UPLOAD_INPUT_INPUT_ID: Input(
            HIDDEN_CRNS_UPLOAD_INPUT_INPUT_ID, "value"
        ),
        HIDDEN_PREDICTOR_UPLOAD_INPUT_INPUT_ID: Input(
            HIDDEN_PREDICTOR_UPLOAD_INPUT_INPUT_ID, "value"
        ),
        CHECK_INPUT_BUTTON_INPUT_ID: Input(CHECK_INPUT_BUTTON_INPUT_ID, "n_clicks"),
    },
    state={
        # fmt: off
        active_form_template_factory.job_id_key: State(  # nocheck
            active_form_template_factory.job_id_key,
            "children",  # nocheck
        ),
        # fmt: on
    },
    prevent_initial_call="initial_duplicate",
)
def form_validation_callback(**state):
    """Validate form inputs and handle submission."""
    log.info("Form validation callback")

    triggered_ids = {
        t["prop_id"].split(".")[0]
        for t in callback_context.triggered
        if t["value"] is not None
    }
    log.debug(f"Triggered ids: {triggered_ids}")

    # Preprocessing: inject predictors, soil_moisture_data, uploads into form_data
    preprocess_form_data(state)

    valid, output_dict = active_form_factory.validate_callback(state)

    # Route file upload field validation errors to their feedback divs.
    # Model validators (e.g. check_soil_moisture_data) produce errors for
    # fields not in fields_website. validate_callback returns them as
    # unhandled exceptions with key "<field_name>_feedback_children".
    crns_feedback_key = "crns_upload_feedback_children"
    if crns_feedback_key in output_dict:
        output_dict[CRNS_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID] = output_dict.pop(
            crns_feedback_key
        )
    else:
        output_dict[CRNS_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID] = ""

    pred_feedback_key = "predictor_upload_feedback_children"
    if pred_feedback_key in output_dict:
        output_dict[PREDICTOR_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID] = output_dict.pop(
            pred_feedback_key
        )
    else:
        output_dict[PREDICTOR_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID] = ""

    output_dict["loading_overlay"] = False

    job_id = state["job_id"]

    if CHECK_INPUT_BUTTON_INPUT_ID in triggered_ids and valid:
        log.debug("Submit button clicked")
        validated_model = active_form_factory.set_model(state)
        validated_model.__dict__["job_id"] = job_id
        job = Job(model=validated_model)
        job.prepare_input_files()
        submission_base_path = dash.page_registry["pages.submission"]["path_template"]
        output_dict["redirect"] = submission_base_path.replace(
            "<job_id>", str(job.job_id)
        )
    else:
        output_dict["redirect"] = dash.no_update

    # Display model for showing current selections (even when invalid)
    display_model = build_display_model(state, job_id)
    output_dict["selected_predictors"] = construct_selected_input(
        display_model, "predictor_upload"
    )
    output_dict["selected_crns"] = construct_selected_input(
        display_model, "crns_upload"
    )

    return output_dict
