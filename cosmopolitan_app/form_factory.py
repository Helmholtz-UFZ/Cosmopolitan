"""Dash form for the cosmopolitan job."""

import json
from collections import OrderedDict
from typing import Any, Dict, List, Tuple, Type, Union, get_args

import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html
from pydantic_core import ValidationError
from soil_moisture_prediction.input_data import stream_dic

from cosmopolitan_app.constants import CHECK_INPUT_ID
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

    def __init__(
        self, pymodel: Type[ModelWebsite], layout: OrderedDict, active: bool = True
    ):
        """Init."""
        self.pymodel = pymodel
        self.layout = layout
        self.active = active
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
        self.fields_website = flatten_list(layout.values())
        self.form_layout = []
        self.fieldtypes_not_to_validate = [
            "checkbox",
            "dropdown-checklist",
            "date-picker",
            "multiple-file-upload",
            "file-upload",
        ]
        if self.active:
            self.id_format = "{field_name}"
            self.feedback_id_format = "{field_name}_feedback"
            self.hidden_id_format = "hidden_{field_name}"
            self.file_name_id_format = "{field_name}_filename"
            self.delete_id_format = "delete_{field_name}"
            self.start_date_id_format = "{field_name}_start_date"
            self.end_date_id_format = "{field_name}_end_date"
            self.id_check_input_button = CHECK_INPUT_ID
        else:
            self.id_format = ""
            self.feedback_id_format = ""
            self.hidden_id_format = ""
            self.file_name_id_format = ""
            self.delete_id_format = ""
            self.id_check_input_button = ""

    def new_layout(self, layout: OrderedDict) -> None:
        """Set a new layout."""
        self.layout = layout
        self.fields_website = flatten_list(layout.values())
        self.form_layout = []

    def create_component(self, field_name: Any) -> Any:
        """Create the component."""
        if not isinstance(field_name, str):
            return field_name
        field = ModelWebsite.model_fields[field_name]

        field_type = field.json_schema_extra["type"]
        try:
            component_class = self.type_to_component[field_type]
        except KeyError:
            raise ValueError(f"Unkown field_type: {field_type}")

        props = {}

        id_feedback = self.feedback_id_format.format(field_name=field_name)
        id_field = self.id_format.format(field_name=field_name)
        try:
            value = getattr(self.pymodel, field_name)
        except AttributeError:
            value = field.default

        if field_type in ["text", "email"]:
            props["type"] = "text" if field_type == "text" else "email"
            props["id"] = id_field
            props["value"] = value
            props["html_size"] = len(value) + 5
            props["style"] = {"width": "auto"}
            if not self.active:
                props["disabled"] = True
                props["style"].update({"background-color": "#e9ecef"})
        elif field_type in ["float", "integer"]:
            props["type"] = "number"
            props["step"] = 1 if field_type == "integer" else "any"
            props["required"] = True
            props["id"] = id_field
            props["value"] = value
            props["html_size"] = len(str(value)) + 5
            props["style"] = {"width": "auto"}
            if not self.active:
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
                options.append(
                    {"label": label, "value": choice, "disabled": not self.active}
                )
            checklist_props = {
                "options": options,
                "value": value,
                "id": id_field,
                "inline": False,
                "style": {"max-height": "300px", "overflow-y": "auto"},
                "className": "ms-2",
            }
            props["children"] = [dbc.Checklist(**checklist_props)]
        elif field_type == "date-picker":
            props["id"] = id_field
            props["start_date"] = value[0]
            props["end_date"] = value[1]
            props["initial_visible_month"] = value[1]
            if not self.active:
                props["disabled"] = True
        elif field_type == "checkbox":
            props["id"] = id_field
            props["value"] = value
            props["label"] = field.title
            if not self.active:
                props["disabled"] = True
        elif field_type in ["multiple-file-upload", "file-upload"]:
            props["id"] = id_field
            props["multiple"] = field_type == "multiple-file-upload"
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
                dbc.FormText(id=id_feedback, className="text-danger"),
            ]
        elif field_type in ["multiple-file-upload", "file-upload"]:
            # file_information = ";".join([",".join(info) for info in value])
            file_information = json.dumps(value) if value else "{}"
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

    def generate_form(self) -> List[Any]:
        """Generate the form layout."""
        for group_name, row in self.layout.items():
            card_layout = []
            for field_names in row:
                col = [
                    dbc.Col(
                        self.create_component(field_name),
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
                        dbc.CardHeader(group_name, class_name="w-100 text-center fs-4"),
                        dbc.CardBody(card_layout),
                    ],
                    class_name="my-2 d-flex justify-content-center align-items-center",
                )
            )

        if self.active:
            self.form_layout.append(
                dbc.Row(
                    dbc.Col(
                        dbc.Button(
                            "Check input",
                            id=self.id_check_input_button,
                            color="primary",
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
                output_dict[f"{id_feedback}_type"] = Output(id_feedback, "type")
            output_dict[f"{id_feedback}_children"] = Output(id_feedback, "children")
            if field_type in [
                "multiple-file-upload",
                "file-upload",
            ]:
                hidden_id = self.hidden_id_format.format(field_name=field_name)
                output_dict[hidden_id] = Output(hidden_id, "value")

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
            id_field = self.id_format.format(field_name=field_name)
            if field_type in ["multiple-file-upload", "file-upload"]:
                hidden_id = self.hidden_id_format.format(field_name=field_name)
                delete_id = self.delete_id_format.format(field_name=field_name)
                filename_id = self.file_name_id_format.format(field_name=field_name)

                input_dict[hidden_id] = callback_context(hidden_id, "value")
                input_dict[id_field] = callback_context(field_name, "contents")
                input_dict[filename_id] = callback_context(field_name, "filename")
                input_dict[delete_id] = callback_context(delete_id, "n_clicks")
            elif field_type == "date-picker":
                id_start_date = self.start_date_id_format.format(field_name=field_name)
                id_end_date = self.end_date_id_format.format(field_name=field_name)
                input_dict[id_start_date] = callback_context(field_name, "start_date")
                input_dict[id_end_date] = callback_context(field_name, "end_date")
            else:
                input_dict[id_field] = callback_context(field_name, "value")

        input_dict[self.id_check_input_button] = callback_context(
            self.id_check_input_button, "n_clicks"
        )
        return input_dict

    def validate_callback(
        self, form_data: dict, file_upload_error: dict
    ) -> Tuple[bool, dict]:
        """Validate the callback."""
        exceptions = {}
        try:
            self.set_model(form_data)
        except ValidationError as e:
            for error in e.errors():
                msg = error["msg"].replace("Value error, ", "")
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
                    output_dict[f"{id_feedback}_type"] = "invalid"
                output_dict[f"{id_feedback}_children"] = msg
            else:
                if field_type not in self.fieldtypes_not_to_validate:
                    output_dict[f"{field_name}_valid"] = True
                    output_dict[f"{field_name}_invalid"] = False
                    output_dict[f"{id_feedback}_type"] = "valid"
                output_dict[f"{id_feedback}_children"] = ""

            if field_type in [
                "multiple-file-upload",
                "file-upload",
            ]:
                hidden_id = self.hidden_id_format.format(field_name=field_name)
                output_dict[hidden_id] = form_data[hidden_id]

        if len(exceptions) > 0:
            raise ValueError(f"Unhandeled form validation errors: {exceptions}")

        return valid, output_dict

    def set_model(self, form_data: dict) -> None:
        """Set the model from the form data."""
        model_dict = {}
        for field_name in ModelWebsite.model_fields:
            field_type = ModelWebsite.model_fields[field_name].json_schema_extra["type"]
            if field_name == "predictors":
                predictors_stream = {
                    stream: None for stream in form_data["pred_streams"]
                }
                hidden_id = self.hidden_id_format.format(field_name="predictor_upload")
                predictor_upload_wrong_keys = (
                    json.loads(form_data[hidden_id])
                    if form_data[hidden_id].strip()
                    else {}
                )
                predictor_upload = {}
                for key, value in predictor_upload_wrong_keys.items():
                    predictor_name = value["predictor_name"]
                    predictor_upload[predictor_name] = value

                model_dict["predictors"] = predictors_stream | predictor_upload
            elif field_name == "soil_moisture_data":
                hidden_id = self.hidden_id_format.format(field_name="crns_upload")
                crns_upload = (
                    json.loads(form_data[hidden_id])
                    if form_data[hidden_id].strip()
                    else {}
                )
                try:
                    model_dict["soil_moisture_data"] = list(crns_upload.keys())[0]
                except IndexError:
                    model_dict["soil_moisture_data"] = ""
            elif field_type in ["multiple-file-upload", "file-upload"]:
                hidden_id = self.hidden_id_format.format(field_name=field_name)
                model_dict[field_name] = (
                    json.loads(form_data[hidden_id])
                    if form_data[hidden_id].strip()
                    else {}
                )
            elif field_type == "date-picker":
                id_start_date = self.start_date_id_format.format(field_name=field_name)
                id_end_date = self.end_date_id_format.format(field_name=field_name)
                model_dict[field_name] = [
                    form_data[id_start_date],
                    form_data[id_end_date],
                ]
            else:
                try:
                    model_dict[field_name] = form_data[field_name]
                except KeyError:
                    pass

        # Try to set model with the data from the form.
        try:
            self.pymodel = ModelWebsite(**model_dict)
        except ValidationError as e:
            # If there are any validation errors, we need to set default values for any
            # missing or invalid fields. Otherwise, there will be a mismatch between the
            # form and the model. If a field is invalid and the user continues to edit
            # the form, any subsequent edits will not be reflected in the model.
            for error in e.errors():
                locs = error["loc"]
                if len(locs) == 0:
                    # This should be a model validator that manually passed the location
                    locs = error["ctx"]["loc_tuple"]

                field = locs[0]
                if field in ModelWebsite.__fields__:
                    default = ModelWebsite.__fields__[field].get_default()
                    model_dict[field] = default
            self.pymodel = ModelWebsite(**model_dict)
            raise

    def get_file_content(
        self, state: Dict[str, Any], field_name: str
    ) -> Union[Tuple[str, str], Tuple[list, list]]:
        """Get the file(s) content and filename(s) from the state."""
        id_content = self.id_format.format(field_name=field_name)
        id_filename = self.file_name_id_format.format(field_name=field_name)

        return state[id_filename], state[id_content]

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
            file_information_dict = json.loads(state[id])
        except (KeyError, json.JSONDecodeError):
            file_information_dict = {}

        return file_information_dict.items()

    def get_id_input_file_content(self, field_name) -> str:
        """Get the id of the input file content."""
        return self.id_format.format(field_name=field_name)

    def get_id_delete_button(self, field_name) -> str:
        """Get the id of the delete button."""
        return self.delete_id_format.format(field_name=field_name)

    def get_key_submit_button(self) -> str:
        """Get the key of the submit button."""
        return self.id_check_input_button


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
                    style={"white-space": "pre-line"},
                    className="" if coverage_okay else "text-danger",
                ),
                html.Small(
                    general_info,
                    style={"white-space": "pre-line"},
                    className="text-muted",
                ),
            ]
        else:
            content = [
                html.Div(input_name, className="fw-bold"),
                html.Small(
                    general_info,
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


class FormTemplateFactory:
    """Class to create the form layout."""

    def __init__(
        self,
        job_id: str = "foo_bar",
        active: bool = True,
        preview_src: str = "",
        selected_crns: Any = "",
        selected_predictors: Any = "",
    ) -> None:
        """Init."""
        self.active = active
        self.preview_src = preview_src
        self.job_id = job_id
        self.selected_crns = selected_crns
        self.selected_predictors = selected_predictors
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

    def generate_template(self) -> OrderedDict:
        """Create form layout template."""
        job_id_information = [
            html.Div("Job ID", className="text-center fw-bold fs-4"),
            html.Div(self.job_id, id=self.job_id_key, className="text-center"),
        ]

        selected_predictors = [
            html.H5("Selected Predictors", className="text-center"),
            html.Div(
                self.selected_predictors,
                id=self.selected_predictors_key,
                className="text-center",
            ),
        ]

        selected_crns = [
            html.H5("Selected CRNS measurements", className="text-center"),
            html.Div(
                self.selected_crns, id=self.selected_crns_key, className="text-center"
            ),
        ]

        area_preview_elements = [
            html.H5("Area preview:"),
            dbc.Spinner(
                html.Img(
                    id=self.area_preview_key,
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
                        "Generate preview",
                        id=self.new_area_preview_key,
                        color="primary",
                        class_name="my-2",
                        style={"width": "auto"},
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

        form_template = OrderedDict()

        form_template["Job Information"] = [[job_id_information], ["email"]]

        form_template["Area of Interest"] = [
            ["area_x1", "area_x2"],
            ["area_y1", "area_y2"],
            ["area_resolution", "projection"],
            [area_preview],
        ]

        form_template["CRNS Measurements"] = []
        if self.active:
            form_template["CRNS Measurements"] += [[crns_data_base]]
        form_template["CRNS Measurements"] += [["date_range"]]
        if self.active:
            form_template["CRNS Measurements"] += [
                ["train_data"],
                ["station_data"],
                ["rover_data"],
            ]
        if self.active:
            form_template["CRNS Measurements"] += [[html.Hr()], ["crns_upload"]]
        form_template["CRNS Measurements"] += [[html.Hr()], [selected_crns]]

        form_template["Predictors"] = []
        if self.active:
            form_template["Predictors"] += [["pred_streams"]]
            form_template["Predictors"] += [
                [html.Hr()],
                ["predictor_upload"],
                [html.Hr()],
            ]
        form_template["Predictors"] += [[selected_predictors]]

        form_template["Model Parameters"] = [
            ["monte_carlo_soil_moisture"],
            ["monte_carlo_predictors"],
            ["monte_carlo_iterations"],
            ["past_prediction_as_feature"],
            ["allow_nan_in_training"],
            ["predictor_qmc_sampling"],
            ["compute_slope"],
            ["compute_aspect"],
        ]

        return form_template


active_form_template_factory = FormTemplateFactory(active=True)
active_form_template = active_form_template_factory.generate_template()
active_form_factory = FormFactory(ModelWebsite, active_form_template)

muted_form_template_factory = FormTemplateFactory(active=False)
muted_form_template = muted_form_template_factory.generate_template()
muted_form_factory = FormFactory(ModelWebsite, muted_form_template, active=False)
