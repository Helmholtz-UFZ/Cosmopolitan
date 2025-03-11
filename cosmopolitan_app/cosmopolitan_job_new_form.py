"""Dash form for the cosmopolitan job."""

import logging
import os
import re
from collections import OrderedDict
from typing import Annotated, Any, List, Type

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, callback
from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator, BaseModel, Field
from soil_moisture_prediction.pydantic_models import InputParameters

from cosmopolitan_app.config import JOB_WORK_DIR_TEMPLATE
from cosmopolitan_app.postgres_manager import PostgresManager

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])


def validate_job_id(job_id):
    """Validate job id.

    The function further creates input dir for the job. If the job id was
    changed the function and moves all previously uploaded files into the
    new input dir.
    """
    logging.debug(f"Check job id {job_id}")

    job_id_regex = r"^\w+$"
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
    """Validate an email address using the email-validator library."""
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
            "test@gmail.com",
            description="Please enter a valid gmail address",
            title="Email",
            type="email",
        ),
        AfterValidator(check_email),
    ]

    job_id: Annotated[
        str,
        Field(
            "test_job",
            description='Identifier for your submission. Only letters, numbers and "_".',  # noqa
            title="Job ID",
            type="text",
        ),
        AfterValidator(validate_job_id),
    ]


default_model = ModelWebsite()
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
            str: dbc.Input,
            int: dbc.Input,
            float: dbc.Input,
            bool: dbc.Checkbox,
        }
        self.layout = layout
        self.fields_website = [
            item for sublist in self.layout.values() for item in sublist
        ]
        self.form_layout = []

    def generate_form(self) -> List[Any]:
        """Generate the form layout."""
        for group_name, field_names in self.layout.items():
            card_layout = []
            for field_name in field_names:
                field = ModelWebsite.model_fields[field_name]
                field_type = field.annotation
                try:
                    component_class = self.type_to_component[field_type]
                except KeyError:
                    raise ValueError("Unkown field_type")

                props = {
                    "id": f"{field_name}-input",
                    "value": field.default if field.default is not None else "",
                }

                if field_type is str:
                    props["type"] = "text"
                    props["required"] = True
                elif field_type in (int, float):
                    props["type"] = "number"
                    props["step"] = 1 if field_type is int else "any"
                    props["required"] = True

                content = [
                    dbc.Label(field.title),
                    component_class(**props),
                    dbc.FormText(field.description),
                    dbc.FormFeedback(id=f"{field_name}-feedback"),
                ]
                card_layout.append(dbc.Row(content))

            self.form_layout.append(
                dbc.Card(
                    [
                        dbc.CardHeader(group_name),
                        dbc.CardBody(card_layout),
                    ],
                )
            )
        self.form_layout.append(
            dbc.Button("Submit", id="submit-button", color="primary")
        )

        return self.form_layout

    def produce_callback_outputs(self) -> dict:
        """Produce the callback outputs."""
        output_dict = {}
        for field_name in self.fields_website:
            if ModelWebsite.model_fields[field_name].annotation is bool:
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
            if ModelWebsite.model_fields[field_name].annotation is bool:
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
            if ModelWebsite.model_fields[field_name].annotation is bool:
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


form_layout = OrderedDict(
    {
        "Model parameters": [
            "segment_number",
            "lower_benefit_limit",
            "time_limit",
            "optimization_objective",
            "max_aco_iteration",
            "ant_no",
            "total_number_of_classes",
            "is_reversed",
        ],
        "Job Information": ["email"],
    }
)

form_factory = FormFactory(ModelWebsite, form_layout)


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


app.layout = dbc.Col(
    form_factory.generate_form(),
    className="m-4",
)


if __name__ == "__main__":
    app.run_server(debug=True)
