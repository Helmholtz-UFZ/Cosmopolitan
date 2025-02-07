"""The main class is CosmopolitanJobForm and handels the input data.

It includes form definitions, input validation, and a class for managing
geometric areas.

Classes:
- CosmopolitanJobForm: WTF form for Cosmopolitan input, used for job submissions.
# Widgets for displaying form fields.
- BooleanInput: Generate input field for boolean input.
- DynamicSizeTextInput: Generate input field for Text Input.
- DynamicSizeNumberInput: Generate input field for Integer Input.
- OptionalEmail: A custom validator that allows for an empty email field.
# More complex validation of input files
- GeomArea: A class representing a geometric area defined by coordinates.
- InputFileParser: This abstract base class defines the common methods for parsing an
input file.
- PredParser: Parses an input file containing predictor data.
- CrnParser: Parses an input file containing CRN measurements.

This module is an integral part of the Cosmopolitan application and is used to manage
user inputs, validate data, and define the geometric areas for data processing of input
files.
"""

import io
import json
import logging
import math
import os
import re
import shutil
from collections import OrderedDict

import cairo
import staticmaps
from coolname import generate
from flask_wtf import FlaskForm
from markupsafe import Markup
from pyproj import Transformer
from soil_moisture_prediction.area_geometry import RectGeom
from soil_moisture_prediction.input_data import stream_dic
from soil_moisture_prediction.input_file_parser import (
    FileValidationError,
    PredictorParser,
    SoilMoistureParser,
)
from soil_moisture_prediction.pydantic_models import check_projection_format
from werkzeug.utils import secure_filename
from wtforms import (
    BooleanField,
    HiddenField,
    IntegerField,
    MultipleFileField,
    SelectMultipleField,
    StringField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    InputRequired,
    Length,
    NumberRange,
    Regexp,
    ValidationError,
)
from wtforms.widgets import CheckboxInput, NumberInput, Select, TextInput

from cosmopolitan_app.config import JOB_WORK_DIR_TEMPLATE
from cosmopolitan_app.postgres_manager import PostgresManager

logging.getLogger("PIL.PngImagePlugin").setLevel(logging.WARNING)


def json_load_4_jinja(string):
    """Wrap json.load to always return a dic, needed for selected input files."""
    if string == "":
        return {}
    return json.loads(string)


def json_dumps_4_jinja(object_to_convert):
    """Wrap json.load to always return a dic, needed for selected input files."""
    string = json.dumps(object_to_convert)
    if string == "{}":
        return ""
    return string


class BooleanInput(CheckboxInput):
    """Generate input field for boolean input."""

    def __call__(self, field, **kwargs):
        """Generate input field for Text Input."""
        if len(field.errors) == 0:
            kwargs["class"] = "form-control-input"
        else:
            kwargs["class"] = "form-control-input is-invalid"

        return super().__call__(field, **kwargs)


class DynamicSizeTextInput(TextInput):
    """Generate input field for Text Input."""

    size = 10

    def __init__(self, *args, **kwargs):
        """Remove size from kwarsgs before init."""
        if "size" in kwargs:
            self.size = kwargs["size"]
            del kwargs["size"]
        super().__init__(*args, **kwargs)

    def __call__(self, field, **kwargs):
        """Generate input field for Text Input."""
        if len(field.errors) == 0:
            kwargs["class"] = "form-control"
        else:
            kwargs["class"] = "form-control is-invalid"

        kwargs["size"] = self.size
        kwargs["style"] = "width: auto;"

        for validator in field.validators:
            if hasattr(validator, "max"):
                kwargs["size"] = validator.max
                break
        return super().__call__(field, **kwargs)


class DynamicSizeNumberInput(NumberInput):
    """Generate input field for Integer Input."""

    def __call__(self, field, **kwargs):
        """Generate input field for Text Input."""
        if len(field.errors) == 0:
            kwargs["class"] = "form-control"
        else:
            kwargs["class"] = "form-control is-invalid"

        kwargs["size"] = 5
        kwargs["style"] = "width: auto;"

        for validator in field.validators:
            if hasattr(validator, "max"):
                if validator.max is None:
                    break
                kwargs["size"] = int(math.log10(validator.max)) + 1
                break
        return super().__call__(field, **kwargs)


class SelectMultipleInput(Select):
    """Generate input field for Select."""

    def __call__(self, field, **kwargs):
        """Generate input field for Text Input."""
        self.multiple = True
        if len(field.errors) == 0:
            kwargs["class"] = "form-control"
        else:
            kwargs["class"] = "form-control is-invalid"
        return super().__call__(field, **kwargs)


class OptionalEmail(Email):
    """A custom validator that allows for an empty email field."""

    def __call__(self, form, field):
        """Only validate with content."""
        if field.data != "":
            super(OptionalEmail, self).__call__(form, field)


class CosmopolitanJobForm(FlaskForm):
    """WTF form for Cosmopolitan input.

    Here all logic for input values is set. Further the strings that display the
    erros and description. The construction of the input fields are shaped here
    as well either. The arrangment of the
    fields in done in ./templates/html/input/input.html and is defined by the
    dic object "group". The complete structure of the field is defined in
    "./templates/html/input/fields.html".
    """

    preview_area_filename = "preview_area.png"

    groups = OrderedDict(
        {
            "Query Information": ["job_id", "previous_job_id", "email"],
            "Area": [
                "area_x1",
                "area_x2",
                "area_y1",
                "area_y2",
                "area_res",
                "projection",
            ],
            "Predictor variables": [
                "pred_streams",
                "pred_files",
                "selected_pred_input",
            ],
            "CRN Measurments": ["crn_file", "selected_crn_file"],
            "Model Parameters": [
                "monte_carlo_soil_moisture",
                "monte_carlo_iterations",
                "past_prediction_as_feature",
                "monte_carlo_predictor",
                "allow_nan_in_training",
                "predictor_qmc_sampling",
                "compute_slope",
                "compute_aspect",
                "monte_carlo_predictors",
            ],
        }
    )

    job_id_regex = r"^\w+$"

    # Must be first will set input_dir on validation. Otherwise no upload is possible.
    job_id = StringField(
        "Job ID",
        default="",
        description='Identifier for your submission. Only letters, numbers and "_".',
        widget=DynamicSizeTextInput(),
        validators=[
            DataRequired(),
            Length(min=8, max=50),
            Regexp(
                job_id_regex,
                message="Username must contain only letters numbers or underscore",
            ),
        ],
    )

    previous_job_id = HiddenField(
        "Previous job id",
        default="",
    )

    email = StringField(
        "Email",
        default="",
        description="Email address to be notified when job submission is complete.",
        widget=DynamicSizeTextInput(size=20),
        validators=[OptionalEmail()],
    )

    # Must be before input files.
    area_x1 = IntegerField(
        "X1",
        default=630151,
        description="Defining the left boundrie of the area.",
        widget=DynamicSizeNumberInput(),
        validators=[InputRequired(), NumberRange(min=0, max=10_000_000)],
    )

    area_x2 = IntegerField(
        "X2",
        default=633899,
        description="Defining the right boundrie of the area.",
        widget=DynamicSizeNumberInput(),
        validators=[InputRequired(), NumberRange(min=0, max=10_000_000)],
    )

    area_y1 = IntegerField(
        "Y1",
        default=5736522,
        description="Defining the lower boundrie of the area.",
        widget=DynamicSizeNumberInput(),
        validators=[InputRequired(), NumberRange(min=0, max=10_000_000)],
    )

    area_y2 = IntegerField(
        "Y2",
        default=5741019,
        description="Defining the higher boundrie of the area.",
        widget=DynamicSizeNumberInput(),
        validators=[InputRequired(), NumberRange(min=0, max=10_000_000)],
    )

    area_res = IntegerField(
        "Resolution",
        default=250,
        description="Defining the resolution of the area.",
        widget=DynamicSizeNumberInput(),
        validators=[InputRequired(), NumberRange(min=0)],
    )

    projection = StringField(
        "Projection",
        default="EPSG:25832",
        description="The projection of the area.",
        widget=DynamicSizeTextInput(),
        validators=[DataRequired()],
    )

    stream_choices = [("remove_all", "remove all")]
    stream_choices += [(key, key.replace("_", " ")) for key in stream_dic.keys()]
    pred_streams = SelectMultipleField(
        "Predictor streams",
        choices=stream_choices,
        description=(
            "Select the predictor streams to be used. Multiple streams can be selected. "  # noqa
            "Use ctrl/cmd to select multiple streams. "
            "A new selection will override the old selection."
        ),
        widget=SelectMultipleInput(),
    )

    pred_files = MultipleFileField(
        "Predictor variable files",
        description=(
            "The predictor variables for the modell as files. "
            "Adding new files will over ride the old files."
        ),
    )

    selected_pred_input = HiddenField(
        "Selected predictor input",
        default="",
    )

    crn_file = MultipleFileField(
        "CRN variable file",
        description=(
            "The CRN mearsurment for the modell as a file. "
            "Adding a new file will over ride the old file."
        ),
    )

    selected_crn_file = HiddenField(
        "Selected CRN file",
        default="",
    )

    monte_carlo_soil_moisture = BooleanField(
        "Monte carlo simulation of CRNS data",
        description="Should a monte carlo simulation of the CRNS data be done to evaulate uncertantiy.",  # noqa
        widget=BooleanInput(),
        validators=[],
    )

    monte_carlo_predictor = BooleanField(
        "Monte carlo simulation of predictor data",
        description="Should a monte carlo simulation of the predictor data be done to evaulate uncertantiy.",  # noqa
        widget=BooleanInput(),
        validators=[],
    )

    monte_carlo_iterations = IntegerField(
        "Number of monte carlo iteration",
        default=10,
        description="Set the number of monte carlo simulations.",
        widget=DynamicSizeNumberInput(),
        validators=[InputRequired(), NumberRange(min=1, max=100)],
    )

    past_prediction_as_feature = BooleanField(
        "Past prediction as feature",
        description=(
            "Use prediction from previous timestep as predictor for the next timestep."
        ),
        widget=BooleanInput(),
        validators=[],
    )

    allow_nan_in_training = BooleanField(
        "Allow NaN in training data",
        description="Whether to allow NaN values in the training data.",
        widget=BooleanInput(),
        validators=[],
    )

    predictor_qmc_sampling = BooleanField(
        "QM sampling for predictors",
        description="Whether to use Quasi-Monte Carlo sampling for the predictors.",
        widget=BooleanInput(),
        validators=[],
    )

    compute_slope = BooleanField(
        "Compute slope",
        description="Whether to compute the slope from elevation and use as predictor.",
        widget=BooleanInput(),
        validators=[],
    )

    compute_aspect = BooleanField(
        "Compute aspect",
        description="Whether to compute the aspect from elevation and use as predictor.",  # noqa
        widget=BooleanInput(),
        validators=[],
    )

    monte_carlo_predictors = BooleanField(
        "Monte carlo simulation of predictors",
        description="Use monte carlo simulation to predict uncertainty for the predictors.",  # noqa
        widget=BooleanInput(),
        validators=[],
    )

    def __init__(self, new=False, **kwargs):
        """Init."""
        logging.debug("Init CosmopolitanJobForm")
        super().__init__(meta={"csrf": False}, **kwargs)
        self.geom_area = None
        if new:
            logging.debug("New job form")
            while True:
                self.job_id.data = "_".join(generate(3))
                if not PostgresManager.check_existence(self.job_id.data):
                    break
            self.previous_job_id.data = self.job_id.data
            self.validate_job_id(self.job_id)

    def validate_job_id(self, field):
        """Validate job id.

        The function further creates input dir for the job. If the job id was
        changed the function and moves all previously uploaded files into the
        new input dir.
        """
        logging.debug(f"Check job id {field.data}")

        if len(field.errors) == 0:
            self.input_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=self.job_id.data)
            os.makedirs(self.input_dir, exist_ok=True)

            if not re.match(self.job_id_regex, self.previous_job_id.data):
                logging.warning("Malicious attack manipulation hidden field!")
                logging.warning(f"Content hidden field {self.previous_job_id.data}")
                raise ValidationError("Use normal input field to set job id.")

            previous_input_dir = JOB_WORK_DIR_TEMPLATE.format(
                job_id=self.previous_job_id.data
            )

            if self.job_id.data != self.previous_job_id.data and os.path.isdir(
                previous_input_dir
            ):
                # Clear the destination directory
                if os.path.exists(self.input_dir):
                    shutil.rmtree(self.input_dir)
                    os.mkdir(self.input_dir)
                for file_name in os.listdir(previous_input_dir):
                    os.replace(
                        os.path.join(previous_input_dir, file_name),
                        os.path.join(self.input_dir, file_name),
                    )
                shutil.rmtree(previous_input_dir)

    def validate_geometry(self):
        """Validate the geometry of the area and create the geom_area object."""
        logging.debug("Validate geometry")
        valid = True

        if self.area_x1.data >= self.area_x2.data:
            self.area_x1.errors.append("X1 cannot be higher or equal than X2.")
            valid = False

        if self.area_y1.data >= self.area_y2.data:
            self.area_y1.errors.append("Y1 cannot be higher or equal than Y2.")
            valid = False

        max_res = min(
            self.area_y2.data - self.area_y1.data, self.area_x2.data - self.area_x1.data
        )
        if self.area_res.data > max_res / 2:
            self.area_res.errors.append(
                "Resolution cannot be higher than the half of the area."
            )
            valid = False

        self.geom_area = RectGeom(
            [
                self.area_x1.data,
                self.area_x2.data,
                self.area_y1.data,
                self.area_y2.data,
                self.area_res.data,
            ],
            build_grid=False,
        )
        # Overwrite the area values with the corrected values.
        self.area_x1.data = self.geom_area.xi
        self.area_x2.data = self.geom_area.xf
        self.area_y1.data = self.geom_area.yi
        self.area_y2.data = self.geom_area.yf

        logging.debug(f"Geometry is valid: {valid}")
        return valid

    def preview_area(self, draw_preview=True):
        """Draw a preview of the area."""
        logging.debug("Draw preview")
        width = 800
        height = 500
        if not draw_preview:
            logging.debug("Draw empty preview")
            self._draw_empty_preview(width, height)
            return

        logging.debug("Draw area preview")
        context = staticmaps.Context()
        context.set_tile_provider(staticmaps.tile_provider_OSM)

        transformer = Transformer.from_crs(
            self.projection.data, "EPSG:4326", always_xy=True
        )
        lon_min, lat_min = transformer.transform(self.geom_area.xi, self.geom_area.yi)
        lon_max, lat_max = transformer.transform(self.geom_area.xf, self.geom_area.yf)
        bbox = [
            (lat_min, lon_min),
            (lat_max, lon_min),
            (lat_max, lon_max),
            (lat_min, lon_max),
            (lat_min, lon_min),
        ]

        context.add_object(
            staticmaps.Area(
                [staticmaps.create_latlng(lat, lng) for lat, lng in bbox],
                fill_color=staticmaps.parse_color("#00FF003F"),
                width=2,
                color=staticmaps.BLUE,
            )
        )

        image = context.render_cairo(width, height)
        image.write_to_png(os.path.join(self.input_dir, self.preview_area_filename))

    def _draw_empty_preview(self, width, height):
        # Create a new Cairo surface and context
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(surface)

        # Fill background with white
        ctx.set_source_rgb(1, 1, 1)
        ctx.paint()

        # Set up text properties
        ctx.set_source_rgb(0.5, 0.5, 0.5)  # Gray color for text
        ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(32)

        # Center the text
        text = "No preview available"
        extents = ctx.text_extents(text)
        x = width / 2 - extents.width / 2
        y = height / 2 + extents.height / 2

        # Draw the text
        ctx.move_to(x, y)
        ctx.show_text(text)

        # Save the image
        surface.write_to_png(os.path.join(self.input_dir, "preview_area.png"))

    def validate_projection(self, field):
        """Check the projection format."""
        try:
            check_projection_format(field.data)
        except ValueError as e:
            raise ValidationError(str(e))

    def validate_pred_streams(self, field):
        """Check if the selected stream is valid."""
        logging.debug("Check if selected stream is valid")
        if field.errors == []:
            # Get the previously selected streams and files.
            selected_pred_input = json_load_4_jinja(self.selected_pred_input.data)

            # Remove the streams from the selected predictor inputs and only keep the
            # files.
            selected_pred_input = {
                k: v
                for k, v in selected_pred_input.items()
                if k not in (c[0] for c in self.stream_choices)
            }

            # If user selected remove only keep files.
            if "remove_all" not in field.data:
                # Add the selected streams to the selected predictor inputs.
                selected_pred_input.update(
                    {k: stream_dic[k].class_info(k) for k in field.data}
                )

            self.selected_pred_input.data = json_dumps_4_jinja(selected_pred_input)

    def check_pred_files(self, field):
        """Check the content of the files and override data with file name and hash.

        The function is not named validate_pred_files because it needs a valid geom_area
        object to parse the files. Before calling this function the geom_area object
        must be set with validate_geometry().
        """
        logging.debug("Check predictor variable files integrity")
        try:
            input_file_dic = self._validate_input_file(field, "pred")
        except ValidationError as e:
            self.pred_files.errors.append(e)
            return

        if input_file_dic is not None:
            selected_pred_input = json_load_4_jinja(self.selected_pred_input.data)
            selected_pred_input = {
                k: v
                for k, v in selected_pred_input.items()
                if k in (c[0] for c in self.stream_choices)
            }
            selected_pred_input.update(input_file_dic)
            self.selected_pred_input.data = json_dumps_4_jinja(selected_pred_input)

    def validate_selected_pred_input(self, field):
        """Check if files exist in upload dir."""
        logging.debug("Check if selected predictor files exist.")
        files = []
        for pred, info in json_load_4_jinja(field.data).items():
            if pred in (c[0] for c in self.stream_choices):
                continue
            files.append(info["file_path"])

        self._validate_selected_input_files(files)

    def check_crn_file(self, field):
        """Check the content of the files and override data with file name and hash.

        The function is not named validate_crn_file because it needs a valid geom_area
        object to parse the file. Before calling this function the geom_area object
        must be set with validate_geometry().
        """
        logging.debug("Check crn variable files integrity")
        try:
            input_file_dic = self._validate_input_file(field, "crn")
        except ValidationError as e:
            self.crn_file.errors.append(e)
            return
        if input_file_dic is not None:
            self.selected_crn_file.data = json.dumps(input_file_dic)

    def validate_selected_crn_file(self, field):
        """Check if files exist in upload dir."""
        logging.debug("Check if selected crns files exist.")
        self._validate_selected_input_files(list(json_load_4_jinja(field.data)))

    def validate(self, extra_validators=None):
        """
        Validate the form data and perform custom validation checks.

        Returns:
            bool: True if the form data is valid; False otherwise.

        This method validates the form data and performs custom validation
        checks. It checks that the areas (X1, Y1, X2, Y2) are in the correct
        order, ensures that predictor files and CRN measurement files are
        selected, and handles file cleanup. Additional validation functions can
        be provided through the `extra_validators` parameter.
        """
        logging.debug("Final validation of form")
        if not super().validate():
            logging.debug("Not all field are valid")
            for field in self._fields:
                if len(getattr(self, field).errors) > 0:
                    logging.debug(f"{field}: {getattr(self, field).errors}")

            if (
                self.area_x1.errors
                or self.area_x2.errors
                or self.area_y1.errors
                or self.area_y2.errors
                or self.area_res.errors
                or self.projection.errors
            ):
                logging.debug("Area fields are invalid")
            else:
                logging.debug("Area fields are valid")
                draw_preview = self.validate_geometry()
                self.preview_area(draw_preview=draw_preview)
            return False
        else:
            logging.debug("All field are valid")
            draw_preview = self.validate_geometry()
            form_validt = draw_preview

            # Check files now after geometry is valid.
            self.check_crn_file(self.crn_file)
            self.check_pred_files(self.pred_files)

            if len(self.selected_pred_input.data) == 0:
                self.pred_files.errors.append("Chose one or more predictor files.")
                self.pred_streams.errors.append("Chose one or more predictor streams.")
                form_validt = False

            if len(self.selected_crn_file.data) == 0:
                self.crn_file.errors.append("Chose one or more CRN Measurment files.")
                form_validt = False

            if form_validt:
                self._input_parameters()

            self.preview_area(draw_preview=draw_preview)

            return form_validt

    def _validate_input_file(self, field, input_type):
        """Check the content of the files and override data with file name and hash."""
        well_formed = True
        input_file_dic = {}
        # Check if form has not file attached.
        if field.data[0].filename == "":
            logging.debug("No file send")
            return

        # Check if job id is valid and input dir is defined.
        if self.input_dir is None:
            raise ValidationError("First set a valide job id!")

        for file_name in os.listdir(self.input_dir):
            if input_type in file_name:
                os.remove(os.path.join(self.input_dir, file_name))

        if input_type == "crn" and len(field.data) > 1:
            raise ValidationError("Only one file can be uploaded for CRN data.")

        # Upload file and parse
        for upload_file in field.data:
            # Set correct parser
            if input_type == "crn":
                parser = SoilMoistureParser(self.geom_area)
            elif input_type == "pred":
                parser = PredictorParser(self.geom_area)

            new_filename = input_type + "_" + secure_filename(upload_file.filename)
            if new_filename in (c[0] for c in self.stream_choices):
                new_filename = new_filename + "_file"

            input_file_path = os.path.join(self.input_dir, new_filename)
            # Make text stream from upload file.
            io_buffer = io.BufferedReader(upload_file.stream)
            text_stream = io.TextIOWrapper(io_buffer, encoding="utf-8", newline="")

            # Parse file and write to input dir.
            try:
                with open(input_file_path, "w") as file:
                    for row in parser.parse(text_stream):
                        file.write(
                            ",".join([str(e) for e in row if e is not None]) + "\n"
                        )
            except FileValidationError as e:
                os.remove(input_file_path)
                well_formed = False
                err_msg = f"File {new_filename} is invalid.<br>" + str(e)
                break

            if input_type == "crn":
                input_file_dic[new_filename] = parser.get_file_information()
            elif input_type == "pred":
                predictor_information = parser.get_file_information()
                predictor_information["file_path"] = new_filename
                input_file_dic[predictor_information["predictor_name"]] = (
                    predictor_information
                )

        # If any file was invalid remove all input files.
        if not well_formed:
            for file_name in input_file_dic:
                try:
                    os.remove(os.path.join(self.input_dir, file_name))
                except FileNotFoundError:
                    pass

        if not well_formed:
            raise ValidationError(Markup(err_msg))
        else:
            return input_file_dic

    def _validate_selected_input_files(self, uploaded_files):
        """Check if files exist in upload dir."""
        # Check if job id is valid and input dir is defined.
        if self.input_dir is None:
            raise ValidationError("First set a valide job id!")

        for uploaded_file in uploaded_files:
            # Ignore stream choices
            logging.debug(f"Check if {uploaded_file} exist.")
            if uploaded_file in (c[0] for c in self.stream_choices):
                continue

            if not os.path.isfile(os.path.join(self.input_dir, uploaded_file)):
                raise ValidationError("Upload files with form.")

    def _input_parameters(self, write=True):
        """Write the input parameters for the background model into the input dir."""
        predictors = {}
        for predictor, info in json.loads(self.selected_pred_input.data).items():
            if predictor in (c[0] for c in self.stream_choices):
                predictors[predictor] = None
            else:
                predictors[predictor] = info

        soil_moisture_data = list(json.loads(self.selected_crn_file.data))[0]

        parameters = {
            "geometry": [
                self.area_x1.data,
                self.area_x2.data,
                self.area_y1.data,
                self.area_y2.data,
                self.area_res.data,
            ],
            "projection": self.projection.data,
            "predictors": predictors,
            "soil_moisture_data": soil_moisture_data,
            "monte_carlo_soil_moisture": self.monte_carlo_soil_moisture.data,
            "monte_carlo_predictor": self.monte_carlo_predictor.data,
            "monte_carlo_iterations": self.monte_carlo_iterations.data,
            "past_prediction_as_feature": self.past_prediction_as_feature.data,
            "allow_nan_in_training": self.allow_nan_in_training.data,
            "monte_carlo_predictors": self.monte_carlo_predictors.data,
            "predictor_qmc_sampling": self.predictor_qmc_sampling.data,
            "compute_slope": self.compute_slope.data,
            "compute_aspect": self.compute_aspect.data,
            "what_to_plot": {
                "predictors": True,
                "pred_correlation": True,
                "day_measurements": True,
                "day_predictor_importance": True,
                "day_prediction_map": True,
                "alldays_predictor_importance": True,
                "prediction_distance": True,
            },
            "save_results": True,
            "save_input_data": True,
        }

        if write:
            with open(
                os.path.join(self.input_dir, "parameters.json"), "w", encoding="UTF-8"
            ) as f_handle:
                json.dump(parameters, f_handle, indent=4)
                f_handle.write("\n")
        else:
            return parameters
