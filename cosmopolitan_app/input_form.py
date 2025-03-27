"""Dash form for the cosmopolitan job."""

import logging
import os
import re
from collections import OrderedDict
from datetime import datetime
from typing import Annotated, Any, ClassVar, List, Literal, Tuple, Type, get_args

import dash_bootstrap_components as dbc
from coolname import generate
from dash import Dash, Input, Output, State, callback, dcc, html
from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator, BaseModel, Field, field_validator
from soil_moisture_prediction.input_data import stream_dic
from soil_moisture_prediction.pydantic_models import InputParameters

from cosmopolitan_app.config import JOB_WORK_DIR_TEMPLATE
from cosmopolitan_app.postgres_manager import PostgresManager


def flatten_list(nested_list: List[Any]) -> List[str]:
    """Flatten a nested list."""
    flattened: List[Any] = []
    for item in nested_list:
        if isinstance(item, list):
            flattened.extend(flatten_list(item))
        else:
            if not isinstance(item, str):
                continue
            flattened.append(item)
    return flattened


def validate_job_id(job_id):
    """Validate job id.

    The function further creates input dir for the job. If the job id was
    changed the function and moves all previously uploaded files into the
    new input dir.
    """
    logging.debug(f"Check job id {job_id}")

    job_id_regex = r"^\w+$"
    print(job_id)
    if not re.match(job_id_regex, job_id):
        raise ValueError("Username must contain only letters numbers or underscore")

    min_job_id_length = 8
    max_job_id_length = 50

    if len(job_id) < min_job_id_length or len(job_id) > max_job_id_length:
        raise ValueError(
            f"Job id must be between {min_job_id_length} and {max_job_id_length} characters"  # noqa
        )

    if PostgresManager.check_existence(job_id):
        raise ValueError("Job id already exists")

    input_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=job_id)
    os.makedirs(input_dir, exist_ok=True)


def check_email(email: str) -> str:
    """Validate an email address using the email-validator library allow empty email."""
    if email == "":
        return email
    try:
        validate_email(email, check_deliverability=True)  # Checks syntax and domain
        return email  # Return email if valid
    except EmailNotValidError as e:
        raise ValueError(f"Invalid email: {e}")


class ModelWebsite(InputParameters):
    """Model for the website form."""

    email: Annotated[
        str,
        Field(
            "test@test.com",
            description="Email address to be notified when job submission is complete.",
            title="Email",
            type="email",
        ),
        AfterValidator(check_email),
    ]

    job_id: Annotated[
        str,
        Field(
            "poised_python_of_wonder",
            description='Identifier for your submission. Only letters, numbers and "_".',  # noqa
            title="Job ID",
            type="text",
        ),
        AfterValidator(validate_job_id),
    ]

    date_range: Annotated[
        Tuple[str, str],
        Field(
            ("2021-01-01", "2021-01-31"),
            description="Choose a date range for the CRNS measurements.",
            title="Date range",
            type="date-picker",
        ),
    ]

    stream_choices: ClassVar[List[str]] = list(stream_dic.keys())
    pred_streams: Annotated[
        List[Literal[tuple(stream_choices)]],
        Field(
            ["elevation_bkg", "bdod_5-15cm"],
            description=("Select which the predictor source should to be used"),
            title="Predictor streams",
            type="dropdown-checklist",
        ),
    ]

    predictor_upload: Annotated[
        List[str],
        Field(
            [],
            description=("Upload a files with the predictor data"),
            title="Predictor upload",
            type="multiple-file-upload",
        ),
    ]

    @field_validator("date_range")
    @classmethod
    def check_date_range(cls, date_range):
        """Ensure both dates are in YYYY-MM-DD format and the start date is before the end date."""  # noqa
        date_format = "%Y-%m-%d"

        try:
            start_date = datetime.strptime(date_range[0], date_format)
            end_date = datetime.strptime(date_range[1], date_format)
        except ValueError:
            raise ValueError(
                f"Both dates must be in the format YYYY-MM-DD. Got {date_range}"
            )

        if start_date > end_date:
            raise ValueError(
                f"Start date {date_range[0]} must be before end date {date_range[1]}."
            )

        return date_range


while True:
    job_id = "_".join(generate(3))
    if not PostgresManager.check_existence(job_id):
        break

default_model = ModelWebsite()
default_model.job_id = job_id
default_values = default_model.model_dump()
try:
    test_model = ModelWebsite(**default_values)
except ValueError:
    raise ValueError("Default values are not valid")


class FormFactory:
    """Factory class to generate a dash form from a Pydantic model."""

    def __init__(self, pymodel: Type[BaseModel], layout: OrderedDict):
        """Init."""
        self.pymodel = pymodel
        self.type_to_component = {
            "email": dbc.Input,
            "text": dbc.Input,
            "float": dbc.Input,
            "integer": dbc.Input,
            "dropdown-checklist": dbc.DropdownMenu,
            "date-picker": dcc.DatePickerRange,
            "checkbox": dbc.Checkbox,
        }
        self.layout = layout
        self.fields_website = flatten_list(layout.values())
        self.form_layout = []
        self.fieldtypes_not_to_validate = [
            "checkbox",
            "dropdown-checklist",
            "date-picker",
        ]

    def create_component(self, field_name: Any) -> Any:
        """Create the component."""
        if not isinstance(field_name, str):
            return field_name
        field = ModelWebsite.model_fields[field_name]
        field_type = field.json_schema_extra["type"]
        try:
            component_class = self.type_to_component[field_type]
        except KeyError:
            raise ValueError("Unkown field_type")

        props = {}

        id = f"{field_name}-input"
        value = field.default if field.default is not None else ""

        if field_type in ["text", "email"]:
            props["type"] = "text" if field_type == "text" else "email"
            props["id"] = id
            props["value"] = value
            props["html_size"] = len(value) + 5
            props["style"] = {"width": "auto"}
        elif field_type in ["float", "integer"]:
            props["type"] = "number"
            props["step"] = 1 if field_type == "integer" else "any"
            props["required"] = True
            props["id"] = id
            props["value"] = value
            props["html_size"] = len(str(value)) + 5
            props["style"] = {"width": "auto"}
        elif field_type == "dropdown-checklist":
            props["label"] = field.title
            choices = get_args(get_args(field.annotation)[0])
            options = []
            prefix = "foobar"
            for choice in choices:
                label = choice.replace("_", " ")
                if not label.startswith(prefix):
                    prefix = label.split(" ")[0]
                    if len(options) > 0:
                        previous_label = options[-1]["label"]
                        options[-1]["label"] = [html.Div(previous_label), html.Hr()]
                options.append({"label": label, "value": choice})
            # options = [{"label": choice, "value": choice} for choice in choices]
            props["children"] = [
                dbc.Checklist(
                    options,
                    id=id,
                    value=value,
                    inline=False,
                    style={"max-height": "300px", "overflow-y": "auto"},
                    className="ms-2",
                )
            ]
        elif field_type == "date-picker":
            props["id"] = id
            props["start_date"] = value[0]
            props["end_date"] = value[1]
            props["initial_visible_month"] = value[1]
        elif field_type == "checkbox":
            props["id"] = id
            props["value"] = value
            props["label"] = field.title
        else:
            raise ValueError(f"Unknown field type {field_type}")

        if field_type == "checkbox":
            content = [
                component_class(**props),
                dbc.FormText(field.description),
            ]
        elif field_type == "date-picker":
            content = [
                dbc.Label(field.title),
                html.Br(),
                component_class(**props),
                html.Br(),
                dbc.FormText(field.description),
            ]
        else:
            content = [
                dbc.Label(field.title),
                component_class(**props),
                dbc.FormText(field.description),
                dbc.FormFeedback(id=f"{field_name}-feedback"),
            ]
        return content

    def generate_form(self) -> List[Any]:
        """Generate the form layout."""
        for group_name, row in self.layout.items():
            card_layout = []
            for field_names in row:
                card_layout.append(
                    dbc.Row(
                        [
                            dbc.Col(self.create_component(field_name))
                            for field_name in field_names
                        ],
                        class_name="m-2",
                    )
                )

            self.form_layout.append(
                dbc.Card(
                    [
                        dbc.CardHeader(group_name, class_name="w-100 text-center"),
                        dbc.CardBody(card_layout),
                    ],
                    class_name="my-2 d-flex justify-content-center align-items-center",
                )
            )
        self.form_layout.append(
            dbc.Row(
                dbc.Col(
                    dbc.Button("Submit", id="submit-button", color="primary"),
                    class_name="m-2 d-flex justify-content-center align-items-center",
                ),
            )
        )

        return self.form_layout

    def produce_callback_outputs(self) -> dict:
        """Produce the callback outputs."""
        output_dict = {}
        for field_name in self.fields_website:
            field_type = ModelWebsite.model_fields[field_name].json_schema_extra["type"]
            if field_type in self.fieldtypes_not_to_validate:
                continue
            output_dict[f"{field_name}-valid"] = Output(f"{field_name}-input", "valid")
            output_dict[f"{field_name}-invalid"] = Output(
                f"{field_name}-input", "invalid"
            )
            output_dict[f"{field_name}-children"] = Output(
                f"{field_name}-feedback", "children"
            )
            output_dict[f"{field_name}-type"] = Output(f"{field_name}-feedback", "type")

        return output_dict

    def produce_callback_inputs(self, use_state=False) -> dict:
        """Produce the callback inputs."""
        input_dict = {}
        if use_state:
            callback_context = State
        else:
            callback_context = Input
        for field_name in self.fields_website:
            field_type = ModelWebsite.model_fields[field_name].json_schema_extra["type"]
            if field_type in self.fieldtypes_not_to_validate:
                continue
            input_dict[field_name] = callback_context(f"{field_name}-input", "value")
        return input_dict

    def validate_callback(self, data):
        """Validate the callback."""
        exceptions = {}
        try:
            ModelWebsite(**data)
        except ValueError as e:
            for error in e.errors():
                exceptions[error["loc"][0]] = error["msg"]

        output_dict = {}
        for field_name in self.fields_website:
            field_type = ModelWebsite.model_fields[field_name].json_schema_extra["type"]
            if field_type in self.fieldtypes_not_to_validate:
                continue
            if field_name in exceptions:
                output_dict[f"{field_name}-valid"] = False
                output_dict[f"{field_name}-invalid"] = True
                output_dict[f"{field_name}-children"] = exceptions[field_name]
                output_dict[f"{field_name}-type"] = "invalid"
            else:
                output_dict[f"{field_name}-valid"] = True
                output_dict[f"{field_name}-invalid"] = False
                output_dict[f"{field_name}-children"] = ""
                output_dict[f"{field_name}-type"] = "valid"
        return output_dict

    def produce_callback_input_button(self) -> dict:
        """Produce the callback input for the submit button."""
        return {"submit": Input("submit-button", "n_clicks")}

    def get_submit_key(self) -> str:
        """Get the submit key."""
        return "submit"


job_id_information = [
    html.Div("Job ID", className="text-center fw-bold fs-4"),
    html.Div("foobar", id="job_id", className="text-center"),
    html.Div(id="initial-trigger", style={"display": "none"}),
]

selected_predictors = [
    html.H2("Selected Predictors", className="text-center"),
    html.Div(id="selected-predictors", className="text-center"),
]

form_layout = OrderedDict(
    {
        "Job Information": [[job_id_information], ["email"]],
        "Area of Interest": [
            ["area_x1", "area_x2"],
            ["area_y1", "area_y2"],
            ["area_resolution", "projection"],
            ["date_range"],
        ],
        "Predictors": [
            ["pred_streams"],
            [html.Hr()],
            [selected_predictors],
        ],
        # "CRNS Measurments": [["pred_streams"]],
        "Model Parameters": [
            ["monte_carlo_soil_moisture"],
            ["monte_carlo_predictors"],
            ["monte_carlo_iterations"],
            ["past_prediction_as_feature"],
            ["allow_nan_in_training"],
            ["predictor_qmc_sampling"],
            ["compute_slope"],
            ["compute_aspect"],
        ],
    }
)

form_factory = FormFactory(ModelWebsite, form_layout)


@callback(Output("job_id", "children"), Input("initial-trigger", "id"))
def init(_):
    """Validate the form."""
    while True:
        job_id = "_".join(generate(3))
        if not PostgresManager.check_existence(job_id):
            break
    return job_id


@callback(
    Output("selected-predictors", "children"),
    Input("pred_streams-input", "value"),
)
def list_predictors(streams):
    """Validate the form."""
    content = []
    for stream in streams:
        content.append(
            dbc.ListGroupItem(
                html.Div(
                    [
                        html.Div(stream, className="fw-bold"),
                        html.Small(
                            stream_dic[stream].class_info(stream),
                            style={"white-space": "pre-line"},
                            className="text-muted",
                        ),
                    ],
                    className="ms-2 me-auto",
                ),
                className="d-flex justify-content-between align-items-start",
            )
        )
    return dbc.ListGroup(content, numbered=True, className="text-start")


@callback(
    output=form_factory.produce_callback_outputs(),
    inputs=form_factory.produce_callback_inputs(),
)
def validate(**input):
    """Validate the form."""
    return form_factory.validate_callback(input)


@callback(
    output=[],
    state=form_factory.produce_callback_inputs(use_state=True),
    inputs=form_factory.produce_callback_input_button(),
)
def submit(**state):
    """Submit the form."""
    state.pop(form_factory.get_submit_key())
    model = ModelWebsite(**state)
    print(model)


if __name__ == "__main__":
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

    app.layout = dbc.Row(
        dbc.Col(
            form_factory.generate_form(),
            class_name="m-4",
            width=6,
        ),
        class_name="d-flex justify-content-center align-items-center",
    )

    app.run(debug=True)
