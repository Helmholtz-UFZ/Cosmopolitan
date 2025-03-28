"""Dash form for the cosmopolitan job."""

from collections import OrderedDict
from typing import Any, List, Type, get_args

import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html
from pydantic import BaseModel

from cosmopolitan_app.pydantic_models import ModelWebsite


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
