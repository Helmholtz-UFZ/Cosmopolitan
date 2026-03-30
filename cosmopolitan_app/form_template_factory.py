"""Form template layout and selected input display."""

import json
from typing import Any, List

import dash_bootstrap_components as dbc
from dash import dcc, html
from dash_form_factory import FormFactory, InputField
from soil_moisture_prediction.input_data import stream_dic

from cosmopolitan_app.constants import (
    CHECK_INPUT_BUTTON_INPUT_ID,
    CRNS_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID,
    CRNS_UPLOAD_INPUT_ID,
    DELETE_CRNS_UPLOAD_BUTTON_INPUT_ID,
    DELETE_PREDICTOR_UPLOAD_BUTTON_INPUT_ID,
    HIDDEN_CRNS_UPLOAD_INPUT_INPUT_ID,
    HIDDEN_PREDICTOR_UPLOAD_INPUT_INPUT_ID,
    PREDICTOR_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID,
    PREDICTOR_UPLOAD_INPUT_ID,
)
from cosmopolitan_app.pydantic_models import ModelWebsite


def construct_selected_input(
    model: ModelWebsite, input_type: str, full_info: bool = False
) -> dbc.ListGroup:
    """Construct html view of the selected inputs (predictors and crns data)."""
    selected_input = []
    chosen_input = {}
    crns_data_info_dict = {
        "station_data": ModelWebsite.model_fields["station_data"].description,
        "rover_data": ModelWebsite.model_fields["rover_data"].description,
        "train_data": ModelWebsite.model_fields["train_data"].description,
    }

    if input_type == "predictor_upload":
        file_dict = model.predictor_upload
    else:
        file_dict = model.crns_upload

    for file_name, file_info in file_dict.items():
        if input_type == "predictor_upload":
            general_info = (
                f"Unit: {file_info['unit']}\n"
                f"With deviation: {file_info['std_deviation']}\n"
                f"Constant: {file_info['constant']}\n"
                f"Predictor name: {file_info['predictor_name']}\n"
            )
            coverage = f"Coverage: {file_info['coverage']:.2f}%\n"
            chosen_input[file_name] = (general_info, coverage)
        else:
            general_info = f"Time steps: {', '.join(file_info['time_steps'])}\n"
            coverage = f"Number of measurements: {file_info['num_data_points']}\n"
            chosen_input[file_name] = (general_info, coverage)

    if input_type == "predictor_upload":
        for stream in model.pred_streams:
            chosen_input[stream] = (stream_dic[stream].class_info(stream), None)
    else:
        for source_name, crns_info in crns_data_info_dict.items():
            if getattr(model, source_name):
                chosen_input[source_name] = (crns_info, None)

    for input_name, input_info in chosen_input.items():
        general_info, coverage = input_info
        if full_info and coverage is not None:
            try:
                file_info = file_dict[input_name]
                coverage_percentage = file_info["coverage"]
                coverage_okay = coverage_percentage > 50
            except KeyError:
                coverage_okay = True
            content = [
                html.Div(input_name, className="fw-bold"),
                html.Div(
                    coverage,
                    # no Bootstrap class for white-space: pre-line
                    style={"white-space": "pre-line"},
                    className="" if coverage_okay else "text-danger",
                ),
                html.Small(
                    general_info,
                    # no Bootstrap class for white-space: pre-line
                    style={"white-space": "pre-line"},
                    className="text-muted",
                ),
            ]
        else:
            content = [
                html.Div(input_name, className="fw-bold"),
                html.Small(
                    general_info,
                    # no Bootstrap class for white-space: pre-line
                    style={"white-space": "pre-line"},
                    className="text-muted",
                ),
            ]

        selected_input.append(
            dbc.ListGroupItem(
                html.Div(content),
                className="d-flex align-items-start",
            )
        )
    return dbc.ListGroup(selected_input, numbered=True, className="text-start")


def create_file_upload_component(
    field_name: str,
    upload_id: str,
    hidden_id: str,
    delete_id: str,
    feedback_id: str,
    multiple: bool = False,
    value: Any = None,
) -> list:
    """Build file upload components: Upload+hidden input+delete button+feedback."""
    field = ModelWebsite.model_fields[field_name]
    if value is None:
        value = field.default
    file_information = json.dumps(value) if value else "{}"

    return [
        dbc.Label(field.title),
        dcc.Upload(
            id=upload_id,  # nocheck
            multiple=multiple,
            children=dbc.Button(
                [html.I(className="bi bi-upload me-1"), "Browse files"], color="primary"
            ),
        ),
        dcc.Input(
            id=hidden_id,  # nocheck
            type="text",
            value=file_information,
            className="d-none",
        ),
        dbc.Button(
            [html.I(className="bi bi-trash me-1"), "Delete files"],
            id=delete_id,  # nocheck
            color="warning",
            className="my-2",
        ),
        html.Br(),
        dbc.FormText(field.description),
        html.Br(),
        dbc.FormText(
            "",
            id=feedback_id,  # nocheck
            className="text-danger",
        ),
    ]


def _make_card(title: str, rows: list) -> dbc.Card:
    """Build a card with a header and rows of columns."""
    card_rows = []
    for row in rows:
        cols = [dbc.Col(item) for item in row]
        card_rows.append(dbc.Row(cols, className="m-2"))
    return dbc.Card(
        [
            dbc.CardHeader(title, className="w-100 text-center fs-4"),
            dbc.CardBody(card_rows),
        ],
        className="my-2 d-flex justify-content-center align-items-center",
    )


class FormTemplateFactory:
    """Class to create the form layout as a Dash component tree."""

    def __init__(
        self,
        job_id: str = "foo_bar",
        active: bool = True,
        preview_src: str = "",
        selected_crns: Any = "",
        selected_predictors: Any = "",
        model: Any = None,
    ) -> None:
        """Init."""
        self.active = active
        self.preview_src = preview_src
        self.job_id = job_id
        self.selected_crns = selected_crns
        self.selected_predictors = selected_predictors
        self.model = model
        if active:
            self.job_id_key = "job_id"
            self.selected_predictors_key = "selected_predictors"
            self.selected_crns_key = "selected_crns"
            self.area_preview_key = "area_preview"
            self.new_area_preview_key = "new_area_preview"
        else:
            self.job_id_key = ""
            self.selected_predictors_key = ""
            self.selected_crns_key = ""
            self.area_preview_key = ""
            self.new_area_preview_key = ""

    def generate_template(self) -> List[Any]:
        """Create form layout as a Dash component tree with InputField placeholders."""
        job_id_information = [
            html.Div("Job ID", className="text-center fw-bold fs-4"),
            html.Div(
                self.job_id,
                id=self.job_id_key,  # nocheck
                className="text-center",
            ),
        ]

        selected_predictors = [
            html.H5("Selected Predictors", className="text-center"),
            html.Div(
                self.selected_predictors,
                id=self.selected_predictors_key,  # nocheck
                className="text-center",
            ),
        ]

        selected_crns = [
            html.H5("Selected CRNS measurements", className="text-center"),
            html.Div(
                self.selected_crns,
                id=self.selected_crns_key,  # nocheck
                className="text-center",
            ),
        ]

        area_preview_elements = [
            html.H5("Area preview:"),
            dbc.Spinner(
                html.Img(
                    id=self.area_preview_key,  # nocheck
                    className="col-6 mx-auto d-block",
                    src=self.preview_src,
                    alt="area preview",
                ),
            ),
        ]
        if self.active:
            area_preview_elements.append(
                html.Div(
                    dbc.Button(
                        [html.I(className="bi bi-image me-1"), "Generate preview"],
                        id=self.new_area_preview_key,  # nocheck
                        color="primary",
                        className="my-2 w-auto",
                    ),
                    className="d-flex justify-content-center",
                )
            )
        area_preview = dbc.Row(area_preview_elements, className="text-center pt-2")

        crns_data_base = dbc.Row(
            [
                html.H5("Use CRNS data from TimeIO:"),
                dbc.FormText("Select the CRNS data to use for the prediction."),
                dbc.FormText(
                    "If you whish to use your own data, upload it in the file upload section."  # noqa
                ),
                dbc.FormText(
                    "If you dont want to use any data from the data base uncheck all checkboxes."  # noqa
                ),
            ],
            className="text-center pt-2",
        )

        # --- Build cards ---
        cards = []

        # Job Information
        cards.append(
            _make_card(
                "Job Information",
                [
                    [job_id_information],
                    [InputField("email")],
                ],
            )
        )

        # Area of Interest
        cards.append(
            _make_card(
                "Area of Interest",
                [
                    [InputField("area_x1"), InputField("area_x2")],
                    [InputField("area_y1"), InputField("area_y2")],
                    [InputField("area_resolution"), InputField("projection")],
                    [area_preview],
                ],
            )
        )

        # CRNS Measurements
        crns_rows = []
        if self.active:
            crns_rows.append([crns_data_base])
        crns_rows.append([InputField("date_range")])
        if self.active:
            crns_rows.append([InputField("train_data")])
            crns_rows.append([InputField("station_data")])
            crns_rows.append([InputField("rover_data")])
        if self.active:
            crns_value = (
                getattr(self.model, "crns_upload", None) if self.model else None
            )
            crns_rows.append([html.Hr()])
            crns_rows.append(
                [
                    create_file_upload_component(
                        "crns_upload",
                        upload_id=CRNS_UPLOAD_INPUT_ID,
                        hidden_id=HIDDEN_CRNS_UPLOAD_INPUT_INPUT_ID,
                        delete_id=DELETE_CRNS_UPLOAD_BUTTON_INPUT_ID,
                        feedback_id=CRNS_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID,
                        multiple=False,
                        value=crns_value,
                    )
                ]
            )
        crns_rows.append([html.Hr()])
        crns_rows.append([selected_crns])
        cards.append(_make_card("CRNS Measurements", crns_rows))

        # Predictors
        pred_rows = []
        if self.active:
            pred_value = (
                getattr(self.model, "predictor_upload", None) if self.model else None
            )
            pred_rows.append([InputField("pred_streams")])
            pred_rows.append([html.Hr()])
            pred_rows.append(
                [
                    create_file_upload_component(
                        "predictor_upload",
                        upload_id=PREDICTOR_UPLOAD_INPUT_ID,
                        hidden_id=HIDDEN_PREDICTOR_UPLOAD_INPUT_INPUT_ID,
                        delete_id=DELETE_PREDICTOR_UPLOAD_BUTTON_INPUT_ID,
                        feedback_id=PREDICTOR_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID,
                        multiple=True,
                        value=pred_value,
                    )
                ]
            )
            pred_rows.append([html.Hr()])
        pred_rows.append([selected_predictors])
        cards.append(_make_card("Predictors", pred_rows))

        # Model Parameters
        cards.append(
            _make_card(
                "Model Parameters",
                [
                    [InputField("monte_carlo_soil_moisture")],
                    [InputField("monte_carlo_predictors")],
                    [InputField("monte_carlo_iterations")],
                    [InputField("past_prediction_as_feature")],
                    [InputField("allow_nan_in_training")],
                    [InputField("predictor_qmc_sampling")],
                    [InputField("compute_slope")],
                    [InputField("compute_aspect")],
                ],
            )
        )

        # Check input button (active only)
        if self.active:
            cards.append(
                dbc.Row(
                    dbc.Col(
                        dbc.Button(
                            [
                                html.I(className="bi bi-check-circle me-1"),
                                "Check input",
                            ],
                            id=CHECK_INPUT_BUTTON_INPUT_ID,  # nocheck
                            color="primary",
                        ),
                        className="m-2 d-flex justify-content-center align-items-center",  # noqa
                    ),
                )
            )

        return cards


active_form_template_factory = FormTemplateFactory(active=True)
active_form_layout = active_form_template_factory.generate_template()


def _grouped_checklist_formatter(
    choices: tuple[str, ...], active: bool
) -> list[dict[str, Any]]:
    """Format checklist options with Hr dividers between prefix groups."""
    options: list[dict[str, Any]] = []
    prefix: str | None = None
    for choice in choices:
        label = choice.replace("_", " ")
        if prefix is None or not label.startswith(prefix):
            prefix = label.split(" ")[0]
            if len(options) > 0:
                previous_label = options[-1]["label"]
                options[-1]["label"] = [html.Div(previous_label), html.Hr()]
        options.append({"label": label, "value": choice, "disabled": not active})
    return options


active_form_factory = FormFactory(
    ModelWebsite, active_form_layout, checklist_formatter=_grouped_checklist_formatter
)

muted_form_template_factory = FormTemplateFactory(active=False)
