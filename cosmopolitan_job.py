#!/usr/bin/python3
"""Module for a Cosmopolitan Job."""


import datetime
import os
from collections import OrderedDict
import re
import math

from coolname import generate

from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename

from wtforms import StringField, MultipleFileField, HiddenField, IntegerField
from wtforms.widgets import TextInput, NumberInput
from wtforms.validators import (
    DataRequired,
    Length,
    ValidationError,
    Regexp,
    InputRequired,
    NumberRange,
)

from db_manager import DataBaseManager, JobTable


DEV_MODE = True
# 0 means silence, 3 is highest level of verbosity
VERBOSE_LEVEL = 3
WORK_DIR = "./"
# Directory where files are first uploaded and then checked
UPLOAD_DIR = os.path.join(WORK_DIR, "upload")
# The directory for the input files that have been validated.
INPUT_DIR = os.path.join(WORK_DIR, "input")


def check_verbose_level(verbose_level):
    """Check if verbose levl is in correct form."""
    if not isinstance(verbose_level, int):
        raise ValueError("verbose level must be an integer")
    if 0 > verbose_level > 3:
        raise ValueError("verbose level must be between 0 and 3")


def vprint(msg, verbose_level=0):
    """Print to verbose."""
    check_verbose_level(verbose_level)
    msg = datetime.datetime.today().strftime("[%d/%b/%Y %H:%M:%S] - - ") + str(msg)
    if verbose_level <= VERBOSE_LEVEL:
        if DEV_MODE:
            print(msg)
        else:
            # TODO Logging
            raise NotImplementedError


def get_attributes(clazz):
    """Retrieve a list of non-method attributes (instance variables) of a class."""
    return [
        name
        for name, attr in clazz.__dict__.items()
        if not name.startswith("__")
        and not callable(attr)
        and not type(attr) is staticmethod
    ]


class CosmopolitanJob:
    """This class represents a job submission by the user.

    It handles input from a Flask application, performs input integrity checks,
    submits jobs to a cluster, and formats the output for the user.
    """

    job_id = None
    form = None
    input_data = None
    submission_date = None
    submitted = False
    email = None
    email_status = None
    err_msg = None
    finished = False
    version = None

    def __init__(
        self,
        job_id=None,
        form=None,
    ):
        """Init class either by id, by html form or make a new one."""
        if job_id:
            vprint(f"Load submission {job_id}", verbose_level=2)
            self._load_job(job_id)
        elif form:
            vprint("Set from form", verbose_level=2)
            self._set_from_form(form)
        else:
            vprint("Make blank job", verbose_level=2)
            self._blank_job()

    def __str__(self):
        """Represent class as string."""
        return self.job_id

    def _load_job(self, job_id):
        db_manager = DataBaseManager()
        class_attributes = get_attributes(CosmopolitanJob)
        for name, value in db_manager.get_job_columns(job_id).items():
            if name not in class_attributes:
                raise AttributeError(f"CosmopolitanJob has no attribute named {name}")
            setattr(self, name, value)

        self.form = CosmopolitanJobForm()

        for name, field in self.form._fields.items():
            if name == "csrf_token":
                continue
            if field.type == "MultipleFileField" or name == "previous_job_id":
                continue
            else:
                field.data = self.input_data[name]

        self.form.previous_job_id.data = self.form.job_id.data

    def _blank_job(self):
        db_manager = DataBaseManager()
        while True:
            job_form = CosmopolitanJobForm()
            if db_manager.check_existence(job_form.job_id.data):
                vprint(f"Job id: {job_form.job_id.data} already exist", verbose_level=3)
                continue
            break
        self.form = job_form
        self.job_id = job_form.job_id.data

    def _set_from_form(self, form):
        if type(form) is not CosmopolitanJobForm:
            raise TypeError("Form must be a CosmopolitanJobForm")

        self.form = form
        self.input_data = {}
        self.job_id = self.form.job_id.data

        for name, field in self.form._fields.items():
            if name == "csrf_token":
                continue
            if field.type == "MultipleFileField" or name == "previous_job_id":
                continue
            else:
                self.input_data[name] = field.data

    def save(self):
        """Save the job information to the database.

        This method retrieves the attributes of the current CosmopolitanJob
        instance. It then uses a DataBaseManager instance to add the collected
        data as a new entry in the database.
        """
        column_names = JobTable.__table__.columns.keys()
        data_to_insert = {name: getattr(self, name) for name in column_names}
        db_manager = DataBaseManager()
        db_manager.add_entry(data_to_insert)


class DynamicSizeTextInput(TextInput):
    """Generate input field for Text Input."""

    def __call__(self, field, **kwargs):
        """Generate input field for Text Input."""
        if len(field.errors) == 0:
            kwargs["class"] = "form-control"
        else:
            kwargs["class"] = "form-control is-invalid"

        kwargs["size"] = 10
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
            "Query Information": ["job_id", "previous_job_id"],
            "Predictor variables": ["pred_files", "selected_pred_files"],
            "CRN Measurments": ["crn_files", "selected_crn_files"],
            "Area": ["area_x1", "area_x2", "area_y1", "area_y2", "area_res"],
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

    area_x1 = IntegerField(
        "X1",
        default=1,
        description="Defining the left side of the area.",
        widget=DynamicSizeNumberInput(),
        validators=[InputRequired(), NumberRange(min=0, max=10_000_000)],
    )

    area_x2 = IntegerField(
        "X2",
        default=2,
        description="Defining the right side of the area.",
        widget=DynamicSizeNumberInput(),
        validators=[InputRequired(), NumberRange(min=0, max=10_000_000)],
    )

    area_y1 = IntegerField(
        "Y1",
        default=3,
        description="Defining the lower side of the area.",
        widget=DynamicSizeNumberInput(),
        validators=[InputRequired(), NumberRange(min=0, max=10_000_000)],
    )

    area_y2 = IntegerField(
        "Y2",
        default=4,
        description="Defining the higher side of the area.",
        widget=DynamicSizeNumberInput(),
        validators=[InputRequired(), NumberRange(min=0, max=10_000_000)],
    )

    area_res = IntegerField(
        "Resolution",
        default=4,
        description="Defining the resolution of the area.",
        widget=DynamicSizeNumberInput(),
        validators=[InputRequired(), NumberRange(min=0)],
    )

    request = None
    input_dir = None

    def __init__(self, new=True):
        """Init."""
        super().__init__()
        if new:
            self.job_id.data = "_".join(generate(3))
            self.previous_job_id.data = self.job_id.data

    def validate_job_id(self, field):
        """Validate job id.

        The function further creates input dir for the job. If the job id was
        changed the function and moves all previously uploaded files into the
        new input dir.
        """
        vprint("Check job id", verbose_level=3)
        db_manager = DataBaseManager()
        if db_manager.check_existence(field.data):
            raise ValidationError("Job id already exist")

        if len(field.errors) == 0:
            self.input_dir = os.path.join(INPUT_DIR, self.job_id.data)
            if not os.path.isdir(self.input_dir):
                os.mkdir(self.input_dir)

            if not re.match(self.job_id_regex, self.previous_job_id.data):
                vprint("Malicious attack manipulation hidden field!", verbose_level=0)
                vprint(
                    f"Content hidden field {self.previous_job_id.data}", verbose_level=0
                )
                raise ValidationError("Use normal input field to set job id.")

            previous_input_dir = os.path.join(INPUT_DIR, self.previous_job_id.data)

            if self.job_id.data != self.previous_job_id.data and os.path.isdir(
                previous_input_dir
            ):
                for file_name in os.listdir(previous_input_dir):
                    os.replace(
                        os.path.join(previous_input_dir, file_name),
                        os.path.join(self.input_dir, file_name),
                    )
                os.remove(previous_input_dir)

    def validate_pred_files(self, field):
        """Check the content of the files and override data with file name and hash."""
        vprint("Check predictor variable files integrity", verbose_level=3)
        selected_files = self._validate_input_file(field, "pred_")
        if selected_files is not None:
            self.selected_pred_files.data = selected_files

    def validate_selected_pred_files(self, field):
        """Check if files exist in upload dir."""
        vprint("Check if selected predictor variable files exist.", verbose_level=3)
        self._validate_selected_input_files(field)

    def validate_crn_files(self, field):
        """Check the content of the files and override data with file name and hash."""
        vprint("Check predictor variable files integrity", verbose_level=3)
        selected_files = self._validate_input_file(field, "crn_")
        if selected_files is not None:
            self.selected_pred_files.data = selected_files

    def validate_selected_crn_files(self, field):
        """Check if files exist in upload dir."""
        vprint("Check if selected predictor variable files exist.", verbose_level=3)
        self._validate_selected_input_files(field)

    def validate(self, extra_validators=None):
        """Perform custom validation to ensure that the area variables are well formed."""
        if not super().validate():
            return False

        if self.area_x1.data >= self.area_x2.data:
            self.area_x1.errors.append("X1 cannot be higher or equal than X2.")
            return False

        if self.area_y1.data >= self.area_y2.data:
            self.area_y1.errors.append("Y1 cannot be higher or equal than Y2.")
            return False

        return True

    def _validate_input_file(self, field, input_type):
        """Check the content of the files and override data with file name and hash."""
        # Check if form has not file attached.
        if field.data[0].filename == "":
            vprint("No file send", verbose_level=3)
            return
        # Check if job id is valid and input dir is defined.
        if self.input_dir is None:
            raise ValidationError("First set a valide job id!")

        for file_name in os.listdir(self.input_dir):
            if input_type in file_name:
                os.remove(os.path.join(self.input_dir, file_name))

        new_data = []
        for input_file in field.data:
            new_filename = input_type + "_" + secure_filename(input_file.filename)
            input_file.save(os.path.join(UPLOAD_DIR, new_filename))
            with open(
                os.path.join(UPLOAD_DIR, new_filename), "r", encoding="UTF-8"
            ) as f_handle:
                try:
                    new_data.append([new_filename, f_handle.read()])
                except UnicodeDecodeError:
                    raise ValidationError("File must be utf-8 encoded.")


        # Check if all files are well formed
        well_formed, err_msg = self._is_identical(new_data)

        # Delete or move uploaded files
        for entry in new_data:
            file_name = entry[0]
            if well_formed:
                os.replace(
                    os.path.join(UPLOAD_DIR, file_name),
                    os.path.join(self.input_dir, file_name),
                )
            else:
                os.remove(os.path.join(UPLOAD_DIR, file_name))

        # Store new data
        # field.data = [[e[0], str(hashlib.md5(e[1].encode('utf-8')))] for e in new_data]

        if not well_formed:
            raise ValidationError(err_msg)
        else:
            return " ".join([e[0] for e in new_data])

    def _validate_selected_input_files(self, field):
        """Check if files exist in upload dir."""
        # Check if job id is valid and input dir is defined.
        if self.input_dir is None:
            raise ValidationError("First set a valide job id!")

        for uploaded_file in field.data.split():
            if not os.path.isfile(os.path.join(self.input_dir, uploaded_file)):
                raise ValidationError("Upload files with form.")

    def _is_identical(self, data):
        vprint("Check if files are identical", verbose_level=3)
        return len({e[1] for e in data}) == 1, "Uploaded files are not identical."
