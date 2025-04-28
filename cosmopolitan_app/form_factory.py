"""Dash form for the cosmopolitan job."""

import json
from collections import OrderedDict
from typing import Any, Dict, List, Tuple, Type, Union, get_args

import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html

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

    def __init__(self, pymodel: Type[ModelWebsite], layout: OrderedDict):
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
            "multiple-file-upload": dcc.Upload,
            "file-upload": dcc.Upload,
        }
        self.layout = layout
        self.fields_website = flatten_list(layout.values())
        self.form_layout = []
        self.fieldtypes_not_to_validate = [
            "checkbox",
            "dropdown-checklist",
            "date-picker",
            "multiple-file-upload",
            "file-upload",
        ]
        self.feedback_id_format = "{field_name}_feedback"
        self.hidden_id_format = "hidden_{field_name}_input"
        self.delete_id_format = "delete_{field_name}_input"
        self.id_submit_button = "submit_button"

    def create_component(self, field_name: Any, muted: bool = False) -> Any:
        """Create the component."""
        if not isinstance(field_name, str):
            return field_name
        field = self.pymodel.model_fields[field_name]

        field_type = field.json_schema_extra["type"]
        try:
            component_class = self.type_to_component[field_type]
        except KeyError:
            raise ValueError(f"Unkown field_type: {field_type}")

        props = {}

        id_feedback = self.feedback_id_format.format(field_name=field_name)
        try:
            value = getattr(self.pymodel, field_name)
        except AttributeError:
            value = field.default
            # value = field.default if field.default is not None else ""

        if field_type in ["text", "email"]:
            props["type"] = "text" if field_type == "text" else "email"
            props["id"] = field_name
            props["value"] = value
            props["html_size"] = len(value) + 5
            props["style"] = {"width": "auto"}
            if muted:
                props["disabled"] = True
                props["style"].update({"background-color": "#e9ecef"})
        elif field_type in ["float", "integer"]:
            props["type"] = "number"
            props["step"] = 1 if field_type == "integer" else "any"
            props["required"] = True
            props["id"] = field_name
            props["value"] = value
            props["html_size"] = len(str(value)) + 5
            props["style"] = {"width": "auto"}
            if muted:
                props["disabled"] = True
                props["style"].update({"background-color": "#e9ecef"})
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
                options.append({"label": label, "value": choice, "disabled": muted})
            # options = [{"label": choice, "value": choice} for choice in choices]
            checklist_props = {
                "options": options,
                "value": value,
                "id": field_name,
                "inline": False,
                "style": {"max-height": "300px", "overflow-y": "auto"},
                "className": "ms-2",
            }
            props["children"] = [dbc.Checklist(**checklist_props)]
        elif field_type == "date-picker":
            props["id"] = field_name
            props["start_date"] = value[0]
            props["end_date"] = value[1]
            props["initial_visible_month"] = value[1]
            if muted:
                props["disabled"] = True
        elif field_type == "checkbox":
            props["id"] = field_name
            props["value"] = value
            props["label"] = field.title
            if muted:
                props["disabled"] = True
        elif field_type == "multiple-file-upload":
            props["id"] = field_name
            props["multiple"] = True
            props["children"] = dbc.Button("Browse files", color="primary")
        elif field_type == "file-upload":
            props["id"] = field_name
            props["multiple"] = False
            props["children"] = dbc.Button("Browse files", color="primary")
        else:
            raise ValueError(f"Unknown field type {field_type}")

        if field_type == "checkbox":
            content = [
                component_class(**props),
                dbc.FormText(field.description),
                html.Br(),
                dbc.FormText(
                    "",
                    id=id_feedback,
                    className="text-danger",
                ),
            ]
        elif field_type == "date-picker":
            content = [
                dbc.Label(field.title),
                html.Br(),
                component_class(**props),
                html.Br(),
                dbc.FormText(field.description),
                dbc.FormFeedback(id=id_feedback),
            ]
        elif field_type in ["multiple-file-upload", "file-upload"]:
            file_information = ";".join([",".join(info) for info in value])
            content = [
                dbc.Label(field.title),
                component_class(**props),
                dcc.Input(
                    id=self.hidden_id_format.format(field_name=field_name),
                    type="text",
                    value=file_information,
                    style={"display": "none"},
                ),
                dbc.Button(
                    "Delete files",
                    id=self.delete_id_format.format(field_name=field_name),
                    color="warning",
                    className="my-2",
                ),
                html.Br(),
                dbc.FormText(field.description),
                html.Br(),
                dbc.FormText(
                    "",
                    id=id_feedback,
                    className="text-danger",
                ),
            ]
        else:
            content = [
                dbc.Label(field.title),
                component_class(**props),
                dbc.FormText(field.description),
                dbc.FormFeedback(id=id_feedback),
            ]
        return content

    def generate_form(self, muted: bool = False) -> List[Any]:
        """Generate the form layout.

        Args:
            muted: If True, all form elements will be display-only without interaction.
        """
        self.form_layout = []
        for group_name, row in self.layout.items():
            card_layout = []
            for field_names in row:
                col = [
                    dbc.Col(
                        self.create_component(field_name, muted=muted),
                    )
                    for field_name in field_names
                ]
                card_layout.append(
                    dbc.Row(
                        col,
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
                    dbc.Button(
                        "Submit",
                        id=self.id_submit_button,
                        color="secondary" if muted else "primary",
                        disabled=muted,
                    ),
                    class_name="m-2 d-flex justify-content-center align-items-center",  # noqa
                ),
            )
        )

        return self.form_layout

    def produce_callback_outputs(self) -> dict:
        """Produce the callback outputs."""
        output_dict = {}
        for field_name in self.fields_website:
            field_type = ModelWebsite.model_fields[field_name].json_schema_extra["type"]
            id_feedback = self.feedback_id_format.format(field_name=field_name)
            if field_type not in self.fieldtypes_not_to_validate:
                output_dict[f"{field_name}_valid"] = Output(field_name, "valid")
                output_dict[f"{field_name}_invalid"] = Output(field_name, "invalid")
            output_dict[f"{id_feedback}_children"] = Output(id_feedback, "children")
            output_dict[f"{id_feedback}_type"] = Output(id_feedback, "type")

        return output_dict

    def produce_callback_inputs(self, use_state: bool = False) -> dict:
        """Produce the callback inputs."""
        input_dict = {}
        if use_state:
            callback_context = State
        else:
            callback_context = Input

        for field_name in self.fields_website:
            field_type = ModelWebsite.model_fields[field_name].json_schema_extra["type"]
            if field_type in ["multiple-file-upload", "file-upload"]:
                hidden_id = self.hidden_id_format.format(field_name=field_name)
                delete_id = self.delete_id_format.format(field_name=field_name)
                input_dict[field_name] = callback_context(hidden_id, "value")
                input_dict[f"{field_name}_content"] = callback_context(
                    field_name, "contents"
                )
                input_dict[f"{field_name}_filename"] = callback_context(
                    field_name, "filename"
                )
                input_dict[f"{field_name}_delete"] = callback_context(
                    delete_id, "n_clicks"
                )
            elif field_type == "date-picker":
                input_dict[f"{field_name}_start_date"] = callback_context(
                    field_name, "start_date"
                )
                input_dict[f"{field_name}_end_date"] = callback_context(
                    field_name, "end_date"
                )
            else:
                input_dict[field_name] = callback_context(field_name, "value")

        input_dict[self.id_submit_button] = callback_context(
            self.id_submit_button, "n_clicks"
        )
        return input_dict

    def validate_callback(
        self, form_data: dict, file_upload_error: dict
    ) -> Tuple[bool, dict]:
        """Validate the callback."""
        exceptions = {}
        try:
            self.set_model(form_data)
        except ValueError as e:
            for error in e.errors():
                msg = error["msg"]
                locs = error["loc"]
                if len(locs) == 0:
                    # This should be a model validator that manually passed the location
                    locs = error["ctx"]["loc_tuple"]

                for loc in locs:
                    exceptions[loc] = msg

        exceptions.update(file_upload_error)
        valid = True if len(exceptions) == 0 else False

        output_dict = {}
        for field_name in self.fields_website:
            field_type = ModelWebsite.model_fields[field_name].json_schema_extra["type"]
            id_feedback = self.feedback_id_format.format(field_name=field_name)
            if field_name in exceptions:
                msg = exceptions.pop(field_name)
                if field_type not in self.fieldtypes_not_to_validate:
                    output_dict[f"{field_name}_valid"] = False
                    output_dict[f"{field_name}_invalid"] = True
                output_dict[f"{id_feedback}_children"] = msg
                output_dict[f"{id_feedback}_type"] = "invalid"
            else:
                if field_type not in self.fieldtypes_not_to_validate:
                    output_dict[f"{field_name}_valid"] = True
                    output_dict[f"{field_name}_invalid"] = False
                output_dict[f"{id_feedback}_children"] = ""
                output_dict[f"{id_feedback}_type"] = "valid"

        if len(exceptions) > 0:
            raise ValueError(f"Unhandeled form validation errors: {exceptions}")

        return valid, output_dict

    def set_model(self, form_data: dict) -> None:
        """Set the model from the form data."""
        model_dict = {}
        for field_name in self.pymodel.model_fields:
            if field_name == "predictors":
                predictors_stream = {
                    stream: None for stream in form_data["pred_streams"]
                }
                predictor_upload = (
                    json.loads(form_data["predictor_upload"])
                    if form_data["predictor_upload"].strip()
                    else {}
                )
                model_dict["predictors"] = predictors_stream | predictor_upload
            elif field_name == "predictor_upload":
                model_dict["predictor_upload"] = (
                    json.loads(form_data["predictor_upload"])
                    if form_data["predictor_upload"].strip()
                    else {}
                )
            elif field_name == "soil_moisture_data":
                crns_upload = (
                    json.loads(form_data["crns_upload"])
                    if form_data["crns_upload"].strip()
                    else {}
                )
                try:
                    model_dict["soil_moisture_data"] = list(crns_upload.keys())[0]
                except IndexError:
                    model_dict["soil_moisture_data"] = ""
            elif field_name == "crns_upload":
                model_dict["crns_upload"] = (
                    json.loads(form_data["crns_upload"])
                    if form_data["crns_upload"].strip()
                    else {}
                )
            elif field_name == "date_range":
                model_dict["date_range"] = [
                    form_data["date_range_start_date"],
                    form_data["date_range_end_date"],
                ]
            else:
                try:
                    model_dict[field_name] = form_data[field_name]
                except KeyError:
                    pass

        self.pymodel = ModelWebsite(**model_dict)

    def get_file_content(
        self, state: Dict[str, Any], field_name: str
    ) -> Union[Tuple[str, str], Tuple[list, list]]:
        """Get the file(s) content and filename(s) from the state."""
        id_content = f"{field_name}_content"
        id_filename = f"{field_name}_filename"

        return state[id_content], state[id_filename]

    def set_file_information(
        self, state: Dict[str, Any], upload_info: Dict[str, str], field_name: str
    ) -> None:
        """Set the file information in the state."""
        id = self.hidden_id_format.format(field_name=field_name)
        state[id] = json.dumps(upload_info)

    def get_file_information(
        self, state: Dict[str, Any], field_name: str
    ) -> Dict[str, str]:
        """Get the file information from the state."""
        id = self.hidden_id_format.format(field_name=field_name)
        try:
            return json.loads(state[id])
        except (KeyError, json.JSONDecodeError):
            return {}

    def get_id_input_file_content(self, field_name) -> str:
        """Get the id of the input file content."""
        return f"{field_name}_content"

    def get_id_delete_button(self, field_name) -> str:
        """Get the id of the delete button."""
        return self.delete_id_format.format(field_name=field_name)

    def get_key_submit_button(self) -> str:
        """Get the key of the submit button."""
        return self.id_submit_button
