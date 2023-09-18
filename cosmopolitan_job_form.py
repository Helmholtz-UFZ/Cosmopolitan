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
import csv
import json
import math
import os
import re
import shutil
from collections import OrderedDict
from datetime import date

from coolname import generate
from flask_wtf import FlaskForm
from markupsafe import Markup
from werkzeug.utils import secure_filename
from wtforms import (
    BooleanField,
    HiddenField,
    IntegerField,
    MultipleFileField,
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
from wtforms.widgets import CheckboxInput, NumberInput, TextInput

from config import WEB_INPUT_DIR, WEB_OUTPUT_DIR, WEB_UPLOAD_DIR
from db_manager import DataBaseManager


def json_load_4_jinja(string):
    """Wrap json.load to always return a dic, needed for selected input files."""
    if string == "":
        return {}
    return json.loads(string)


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

    groups = OrderedDict(
        {
            "Query Information": ["job_id", "previous_job_id", "email"],
            "Area": ["area_x1", "area_x2", "area_y1", "area_y2", "area_res"],
            "Predictor variables": ["pred_files", "selected_pred_files"],
            "CRN Measurments": ["crn_files", "selected_crn_files"],
            "Monte carlo": ["monte_carlo_simulation", "monte_carlo_iterations"],
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

    pred_files = MultipleFileField(
        "Predictor variable files",
        description=(
            "The predictor variables for the modell as files. "
            "Adding new files will over ride the old files."
        ),
    )

    selected_pred_files = HiddenField(
        "Selected predictor variable files",
        default="",
    )

    crn_files = MultipleFileField(
        "CRN variable files",
        description=(
            "The CRN mearsurment for the modell as files. "
            "Adding new files will over ride the old files."
        ),
    )

    selected_crn_files = HiddenField(
        "Selected CRN files",
        default="",
    )

    monte_carlo_simulation = BooleanField(
        "Monte carlo simulation",
        description="Should a monte carolo simulation be done to evaulate uncertantiy.",
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

    request = None
    input_dir = None
    upload_dir = None
    output_dir = None
    geom_area = None
    logger = None

    def __init__(self, logger, new=True):
        """Init."""
        super().__init__()
        self.logger = logger
        if new:
            self.job_id.data = "_".join(generate(3))
            self.previous_job_id.data = self.job_id.data

    def validate_job_id(self, field):
        """Validate job id.

        The function further creates input dir for the job. If the job id was
        changed the function and moves all previously uploaded files into the
        new input dir.
        """
        self.logger.debug("Check job id")
        db_manager = DataBaseManager()
        if db_manager.check_existence(field.data):
            raise ValidationError("Job id already exist")

        if len(field.errors) == 0:
            self.input_dir = os.path.join(WEB_INPUT_DIR, self.job_id.data)
            if not os.path.isdir(self.input_dir):
                os.mkdir(self.input_dir)

            self.upload_dir = os.path.join(WEB_UPLOAD_DIR, self.job_id.data)
            if not os.path.isdir(self.upload_dir):
                os.mkdir(self.upload_dir)
            else:
                shutil.rmtree(self.upload_dir)
                os.mkdir(self.upload_dir)

            self.output_dir = os.path.join(WEB_OUTPUT_DIR, self.job_id.data)
            if not os.path.isdir(self.output_dir):
                os.mkdir(self.output_dir)
            else:
                shutil.rmtree(self.output_dir)
                os.mkdir(self.output_dir)

            if not re.match(self.job_id_regex, self.previous_job_id.data):
                self.logger.warning(
                    "Malicious attack manipulation hidden field!", verbose_level=0
                )
                self.logger.warning(
                    f"Content hidden field {self.previous_job_id.data}", verbose_level=0
                )
                raise ValidationError("Use normal input field to set job id.")

            previous_input_dir = os.path.join(WEB_INPUT_DIR, self.previous_job_id.data)

            if self.job_id.data != self.previous_job_id.data and os.path.isdir(
                previous_input_dir
            ):
                for file_name in os.listdir(previous_input_dir):
                    os.replace(
                        os.path.join(previous_input_dir, file_name),
                        os.path.join(self.input_dir, file_name),
                    )
                os.remove(previous_input_dir)

    def validate_area_res(self, field):
        """Give instance a GeomArea to validate the input files."""
        self.geom_area = GeomArea(
            self.area_x1.data,
            self.area_x2.data,
            self.area_y1.data,
            self.area_y2.data,
            self.area_res.data,
        )

    def validate_pred_files(self, field):
        """Check the content of the files and override data with file name and hash."""
        self.logger.debug("Check predictor variable files integrity")
        input_file_dic = self._validate_input_file(field, "pred")
        if input_file_dic is not None:
            self.selected_pred_files.data = json.dumps(input_file_dic)

    def validate_selected_pred_files(self, field):
        """Check if files exist in upload dir."""
        self.logger.debug("Check if selected predictor variable files exist.")
        self._validate_selected_input_files(field)

    def validate_crn_files(self, field):
        """Check the content of the files and override data with file name and hash."""
        self.logger.debug("Check crn variable files integrity")
        input_file_dic = self._validate_input_file(field, "crn")
        if input_file_dic is not None:
            self.selected_crn_files.data = json.dumps(input_file_dic)

    def validate_selected_crn_files(self, field):
        """Check if files exist in upload dir."""
        self.logger.debug("Check if selected predictor variable files exist.")

        self._validate_selected_input_files(field)

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
        if not super().validate():
            if self.upload_dir is not None:
                shutil.rmtree(self.upload_dir)
            # for field in self._fields:
            #     print(getattr(self, field).errors)
            return False

        form_validt = True
        if self.area_x1.data >= self.area_x2.data:
            self.area_x1.errors.append("X1 cannot be higher or equal than X2.")
            form_validt = False

        if self.area_y1.data >= self.area_y2.data:
            self.area_y1.errors.append("Y1 cannot be higher or equal than Y2.")
            form_validt = False

        if (
            len(self.selected_pred_files.data) == 0
            and self.pred_files.data[0].filename == ""
        ):
            self.pred_files.errors.append("Chose one or more predictor files.")
            form_validt = False

        if (
            len(self.selected_crn_files.data) == 0
            and self.pred_files.data[0].filename == ""
        ):
            self.crn_files.errors.append("Chose one or more CRN Measurment files.")
            form_validt = False

        if form_validt:
            self._input_parameters()

        if self.upload_dir is not None:
            shutil.rmtree(self.upload_dir)

        # for field in self._fields:
        #     print(getattr(self, field).errors)
        return form_validt

    def _validate_input_file(self, field, input_type):
        """Check the content of the files and override data with file name and hash."""
        well_formed = True
        input_file_dic = {}
        # Check if form has not file attached.
        if field.data[0].filename == "":
            self.logger.debug("No file send")
            return
        # Check if job id is valid and input dir is defined.
        if self.input_dir is None:
            raise ValidationError("First set a valide job id!")

        for file_name in os.listdir(self.input_dir):
            if input_type in file_name:
                os.remove(os.path.join(self.input_dir, file_name))

        # Set correct parser
        if input_type == "crn":
            parser = CrnParser(self.geom_area)
        elif input_type == "pred":
            parser = PredParser(self.geom_area)

        # Upload file and parse
        for upload_file in field.data:
            new_filename = input_type + "_" + secure_filename(upload_file.filename)
            upload_file_path = os.path.join(self.upload_dir, new_filename)
            input_file_path = os.path.join(self.input_dir, new_filename)
            upload_file.save(upload_file_path)
            try:
                # Will generate the input file and check file integrity.
                file_information = parser.parse(upload_file_path, input_file_path)
            except ValidationError as e:
                well_formed = False
                err_msg = f"File {upload_file.filename} is invalid.<br>" + str(e)
                break
            input_file_dic[new_filename] = file_information

        # Delete uploaded files and if any file was invalid remove all input files.
        for file_name in input_file_dic:
            os.remove(os.path.join(self.upload_dir, file_name))
            if not well_formed:
                try:
                    os.remove(os.path.join(self.input_dir, file_name))
                except FileNotFoundError:
                    pass

        if not well_formed:
            raise ValidationError(Markup(err_msg))
        else:
            return input_file_dic

    def _validate_selected_input_files(self, field):
        """Check if files exist in upload dir."""
        # Check if job id is valid and input dir is defined.
        if self.input_dir is None:
            raise ValidationError("First set a valide job id!")

        for uploaded_file in json_load_4_jinja(field.data):
            if not os.path.isfile(os.path.join(self.input_dir, uploaded_file)):
                raise ValidationError("Upload files with form.")

    def _input_parameters(self):
        """Write the input parameters for the background model into the input dir."""
        parameters = {
            "Geometry": [
                self.area_x1.data,
                self.area_x2.data,
                self.area_y1.data,
                self.area_y2.data,
                self.area_res.data,
            ],
            "Predictors": json.loads(self.selected_pred_files.data),
            "SM": json.loads(self.selected_crn_files.data),
            "MC": self.monte_carlo_simulation.data,
            "mci": self.monte_carlo_iterations.data,
            "what_to_plot": {
                "predictors": False,
                "pred_correlation": False,
                "day_measurements": False,
                "day_feature_imp": False,
                "day_prediction_map": True,
                "alldays_feature_imp": True,
            },
        }
        with open(
            os.path.join(self.input_dir, "parameters.json"), "w", encoding="UTF-8"
        ) as f_handle:
            json.dump(parameters, f_handle, indent=4)
            f_handle.write("\n")


class GeomArea:
    """A class representing a geometric area defined by coordinates.

    This class allows you to define a 2D rectangular area using its bottom-left
    (x1, y1) and top-right (x2, y2) coordinates. The resolution of the area can
    also be specified. It provides methods to determine if another area covers
    it completely, if a point is contained within it, and to expand the area to
    include additional points.

    Attributes:
    - x1, y1: The x and y coordinates of the bottom-left corner of the area.
    - x2, y2: The x and y coordinates of the top-right corner of the area.
    - res: The resolution of the area.

    Methods:
    - __init__(x1, x2, y1, y2, res): Initialize a new GeomArea instance with
    given coordinates and resolution.
    - cover(other): Check if this area is completely covered by another area.
    - contain(x, y): Check if a given point is inside this area.
    - expand(x, y): Expand the area to include a specified point.
    """

    def __init__(self, x1, x2, y1, y2, res):
        """Initialize a geometric area with specified coordinates and resolution.

        Parameters:
        - x1, x2: x-coordinates that define the left and right boundaries of the area.
        - y1, y2: y-coordinates that define the bottom and top boundaries of the area.
        - res: Resolution of the area.
        """
        self.x1 = x1
        self.x2 = x2
        self.y1 = y1
        self.y2 = y2
        self.res = res

    def __str__(self):
        """Print nice."""
        return f"x1:{self.x1}, x2:{self.x2}, y1:{self.y1}, y2:{self.y2}"

    def covered_by(self, other):
        """Check if this area is completely covered by another area.

        Parameters:
        - other: Instance of GeomArea that will define the area to be covered.

        Returns:
        - True if this area is completely covered by the other area, False
        otherwise.
        """
        if (
            self.x1 >= other.x1
            and self.x2 <= other.x2
            and self.y1 >= other.y1
            and self.y2 <= other.y2
        ):
            return True
        return False

    def contain(self, x, y, margin_multi_res=5):
        """Check if a given point is inside this area.

        Parameters:
        - x: x-coordinate of the point.
        - y: y-coordinate of the point.

        Returns:
        - True if the point is inside this area, False otherwise.
        """
        margin = self.res * margin_multi_res
        if (
            self.x1 - margin <= x <= self.x2 + margin
            and self.y1 - margin <= y <= self.y2 + margin
        ):
            return True
        return False

    def expand(self, x, y):
        """Expand the area to include a given point (x, y).

        Parameters:
        - x: x-coordinate of the point to be included in the expanded area.
        - y: y-coordinate of the point to be included in the expanded area.
        """
        self.x1 = min(self.x1, x)
        self.x2 = max(self.x2, x)
        self.y1 = min(self.y1, y)
        self.y2 = max(self.y2, y)


class InputFileParser:
    """This abstract base class defines the common methods for parsing an input file."""

    file_information = None

    def __init__(self, geom_area):
        """Set parse_geom_area so that every point added expands area."""
        self.input_geom_area = geom_area
        self.parse_geom_area = GeomArea(
            float("inf"), -float("inf"), float("inf"), -float("inf"), 0
        )

    def _check_coordinate(self, cell, row, row_index):
        min_coordinate = 0
        max_coordinate = 10000000000
        try:
            coor = float(cell)
        except ValueError:
            raise ValidationError(
                f"Cell ''{cell}'' is not a decimal number."
                f"Row number {row_index} '{','.join(row)}'."
            )
        if coor < min_coordinate or coor >= max_coordinate:
            raise ValidationError(
                f"Cell '{cell}' needs to be between {min_coordinate} "
                f"and {max_coordinate}."
                f"Row number {row_index} '{','.join(row)}'."
            )

        return coor

    def _check_first_line(self):
        raise NotImplementedError

    def _check_row(self):
        raise NotImplementedError

    def _get_file_information(self):
        raise NotImplementedError

    def _check_validty_area(self):
        raise NotImplementedError

    def parse(self, file_path, out_file_path):
        """Parse the input file and write valid rows to the output file."""
        with open(file_path, "r") as in_file, open(out_file_path, "w") as out_file:
            # Guess the delimiter
            sniffer = csv.Sniffer()
            try:
                dialect = sniffer.sniff(in_file.read(10 * 1024))
            except csv.Error as e:
                if str(e) == "Could not determine delimiter":
                    raise ValidationError(str(e))
            in_file.seek(0)

            csv_reader = csv.reader(in_file, dialect=dialect)
            csv_writer = csv.writer(out_file)
            first_line = next(csv_reader)

            row = self._check_first_line(first_line)
            if row:
                out_file.write(",".join(row))

            for row_index, row in enumerate(csv_reader, start=2):
                row = self._check_row(row, row_index)
                if row:
                    csv_writer.writerow(row)
        self._check_validty_area()

        return self._get_file_information()


class PredParser(InputFileParser):
    """
    Parses an input file containing predictor data.

    This class extends InputFileParser and provides specific functionality for
    validation of predictor data. At the end, a global check is performed so
    that the predictor file must cover the input GeomArea completely, including
    a margin.

    Methods:
        parse(file_path, out_file_path):
            Parses the input file and writes valid predictor data to
            the output file.

    Attributes:
        file_information (dict):
            Information about the file contents (type and unit).
    """

    file_information = {"type": "", "unit": ""}

    def _check_first_line(self, comments):
        if not comments[0][0] == "#":
            row = self._check_row(comments, 1)
        else:
            information = {
                info.split("=")[0]: info.split("=")[1]
                for info in comments[0][2:].split()
            }
            if information.keys() != self.file_information.keys():
                raise ValidationError(
                    f"Unkown predictor information in comment line.<br>{comments}"
                )
            else:
                self.file_information = information
            row = None

        return row

    def _check_row_length(self, row, row_index):
        row_length = 3
        if len(row) != row_length:
            raise ValidationError(
                f"Row number {row_index} '{','.join(row)}' has not correct number "
                f"of columns {row_length}."
            )

    def _check_predictor(self, cell, row, row_index):
        try:
            predictor = float(cell)
        except ValueError:
            raise ValidationError(
                f"Cell '{cell}' is not a decimal number. "
                f"Row number {row_index} '{','.join(row)}'."
            )

        return predictor

    def _check_row(self, row, row_index):
        self._check_row_length(row, row_index)
        x = self._check_coordinate(row[0], row, row_index)
        y = self._check_coordinate(row[1], row, row_index)
        self._check_predictor(row[2], row, row_index)

        if self.input_geom_area.contain(x, y):
            self.parse_geom_area.expand(x, y)
            return row

    def _get_file_information(self):
        return self.file_information

    def _check_validty_area(self):
        if not self.input_geom_area.covered_by(self.parse_geom_area):
            raise ValidationError(
                "The file does not cover the user defined area completely"
            )


class CrnParser(InputFileParser):
    """
    Parses an input file containing CRN measurements.

    This class extends InputFileParser and provides specific functionality for
    CRN measurements validation.

    Attributes:
        days (set):
            Set of unique days in the input file.
        data_points (int):
            Number of valid data points in the user-defined area.

    Methods:
        parse(file_path, out_file_path):
            Parses the input file and writes valid CRN measurements to
            the output file.
    """

    days = set()
    data_points = 0

    def _check_first_line(self, headers):
        header_row = [
            "EPSG_UTM_x",
            "EPSG_UTM_y",
            "Day",
            "soil_moisture",
            "err_low",
            "err_high",
        ]

        if not headers == header_row:
            row = self._check_row(headers, 1)
        else:
            row = headers

        return row

    def _check_row_length(self, row, row_index):
        row_length = 6
        if len(row) != row_length:
            raise ValidationError(
                f"Row number {row_index} '{','.join(row)}' has not correct number "
                f"of columns {row_length}."
            )

    def _check_soil_moisture(self, cell, row, row_index, negativ):
        if not negativ:
            min_soil_moisture = 0
            max_soil_moisture = 1
        else:
            min_soil_moisture = -1
            max_soil_moisture = 0

        try:
            soil_moisture = float(cell)
        except ValueError:
            raise ValidationError(
                f"Cell '{cell}' is not a decimal number. "
                f"Row number {row_index} '{','.join(row)}'."
            )
        if soil_moisture < min_soil_moisture or soil_moisture >= max_soil_moisture:
            raise ValidationError(
                f"Cell '{cell}' needs to be between {min_soil_moisture} and"
                f"{max_soil_moisture}. "
                f"Row number {row_index} '{','.join(row)}'."
            )

        return soil_moisture

    def _check_day(self, cell, row, row_index):
        if not re.match(r"^[0-9]{8}$", row[2]):
            raise ValidationError(
                f"Cell '{row[2]}' is not a day in the format like:'20220323'.<br>"
                f"Row number {row_index} '{','.join(row)}'."
            )
        try:
            day = date(int(row[2][0:4]), int(row[2][4:6]), int(row[2][6:8]))
        except ValueError:
            raise ValidationError(
                f"Cell '{row[2]}' is not a day in the format like:'20220323'.<br>"
                f"Row number {row_index} '{','.join(row)}'."
            )
        return day

    def _check_row(self, row, row_index):
        self._check_row_length(row, row_index)
        x = self._check_coordinate(row[0], row, row_index)
        y = self._check_coordinate(row[1], row, row_index)
        day = self._check_day(row[2], row, row_index)
        self._check_soil_moisture(row[3], row, row_index, False)
        self._check_soil_moisture(row[4], row, row_index, True)
        self._check_soil_moisture(row[5], row, row_index, False)

        if self.input_geom_area.contain(x, y):
            self.parse_geom_area.expand(x, y)
            self.days.add(day.strftime("%Y%m%d"))
            self.data_points += 1
            return row

    def _get_file_information(self):
        return list(self.days)

    def _check_validty_area(self):
        if self.data_points == 0:
            raise ValidationError("No CRN measurments are in the user defined area!")
