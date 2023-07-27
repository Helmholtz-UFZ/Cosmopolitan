#!/usr/bin/python3
"""Module for a Cosmopolitan Job."""


import datetime
import os
import hashlib
from collections import OrderedDict
import re

from coolname import generate

from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename

from wtforms import StringField, MultipleFileField, BooleanField, HiddenField
from wtforms.validators import (
    DataRequired,
    Length,
    ValidationError,
    Regexp,
    StopValidation,
)
from wtforms.widgets import TextInput, Input


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


def job_id_exist(job_id):
    """Check if job id already exist."""
    # TODO
    # Just for testing SQL DB will handle job storage
    existing_jobs = ["quaint-manatee-of-illegal-fertility"]
    return job_id in existing_jobs


class DynamicSizeTextInput(TextInput):
    """Generate input field for Text Input."""

    def __call__(self, field, **kwargs):
        """Generate input field for Text Input."""
        if len(field.errors) == 0:
            kwargs["class"] = "form-control"
        else:
            kwargs["class"] = "form-control is-invalid"

        kwargs["size"] = 10
        for validator in field.validators:
            if hasattr(validator, "max"):
                kwargs["size"] = validator.max
                break
        return super().__call__(field, **kwargs)


class CosmopolitanJob:
    """This class represents a job submission by the user.

    It handles input from a Flask application, performs input integrity checks,
    submits jobs to a cluster, and formats the output for the user.
    """

    def __init__(
        self,
        job_id=None,
        form=None,
    ):
        """Init class either by id, by html form or make a new one."""
        if job_id:
            vprint(f"Load submission {job_id}", verbose_level=2)
            # TODO Build function that loads existing Job.
            raise NotImplementedError
        elif form:
            vprint("Set from form", verbose_level=2)
            self._set_from_form(form)
        else:
            vprint("Make blank job", verbose_level=2)
            self._blank_job()

    def __str__(self):
        """Represent class as string."""
        return self.job_id

    def _blank_job(self):
        while True:
            job_form = CosmopolitanJobForm()
            if job_id_exist(job_form.job_id.data):
                vprint(f"Job id: {job_form.job_id.data} already exist", verbose_level=3)
                continue
            break
        self.form = job_form
        self.job_id = job_form.job_id.data

    def _set_from_form(self, form):
        if type(form) is not CosmopolitanJobForm:
            raise TypeError("Form must be a CosmopolitanJobForm")

        self.form = form
        self.input = {}

        for name, field in self.form._fields.items():
            if name == "csrf_token":
                continue
            self.input[name] = field.data


class CosmopolitanJobForm(FlaskForm):
    """WTF form for Cosmopolitan input.

    Here all logic for input values is set. Further the strings that display the
    erros and description. The construction of the input fields are shaped here
    as well either by the defaults of using widgets. The arrangment of the
    fields in done in ./templates/html/input/input.html and is defined by the
    dic object "group". The complete structure of the field is defined in
    "./templates/html/input/fields.html".
    """

    groups = OrderedDict(
        {
            "Query Information": ["job_id", "previous_job_id"],
            "Independent variables": ["indep_var_files", "selected_indep_var_files"],
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
        "Selected files",
        default="",
    )

    indep_var_files = MultipleFileField(
        "Independent variable files",
        description=(
            "The independent variables for the modell as files. "
            "Adding new files will over ride the old files."
        ),
    )

    selected_indep_var_files = HiddenField(
        "Selected files",
        default="",
    )

    request = None
    input_dir = None

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.job_id.data = "_".join(generate(3))
        self.previous_job_id.data = self.job_id.data

    def validate_job_id(self, field):
        """Validate job id."""
        vprint("Check job id", verbose_level=3)
        if job_id_exist(field.data):
            raise ValidationError("Job id already exist")
        if len(field.errors) == 0:
            self.input_dir = os.path.join(INPUT_DIR, self.job_id.data)
            if not os.path.isdir(self.input_dir):
                os.mkdir(self.input_dir)

            if not re.match(job_id_regex, self.previous_job_id.data):
                vprint("Malicous atack manipulation hidden field!", verbose_level=0)
                vprint(
                    f"Content hidden field {self.previous_job_id.data}", verbose_level=0
                )
                return

            previous_input_dir = os.path.join(INPUT_DIR, self.previous_job_id.data)
            if self.input != self.previous_job_id and os.path.isdir(previous_input_dir):
                for file_name in os.listdir(previous_input_dir):
                    os.replace(
                        os.path.join(previous_input_dir, file_name),
                        os.path.join(self.input_dir, file_name),
                    )
                os.remove(previous_input_dir)

    def validate_selected_indep_var_files(self, field):
        """Check if files exist in upload dir."""
        vprint("Check if selected independent variable files exist.", verbose_level=3)
        # # Check if job id is valid and input dir is defined.
        if self.input_dir is None:
            raise ValidationError("First set a valide job id!")
            return
        for file in field.data.split():
            vprint(os.path.join(self.input_dir, file))
            if not os.path.isfile(os.path.join(self.input_dir, file)):
                raise ValidationError("Upload files with form.")

    def validate_indep_var_files(self, field):
        """Check the content of the files and override data with file name and hash."""
        vprint("Check independent variable files integrity", verbose_level=3)
        # Check if form has not file atached.
        if field.data[0].filename == "":
            vprint("No file send", verbose_level=3)
            return
        # # Check if job id is valid and input dir is defined.
        if self.input_dir is None:
            raise ValidationError("First set a valide job id!")
            return

        for file_name in os.listdir(self.input_dir):
            os.remove(os.path.join(self.input_dir, file_name))
        new_data = []
        for indep_var_file in field.data:
            new_filename = secure_filename(indep_var_file.filename)
            indep_var_file.save(os.path.join(UPLOAD_DIR, new_filename))
            with open(
                os.path.join(UPLOAD_DIR, new_filename), "r", encoding="UTF-8"
            ) as f_handle:
                new_data.append([new_filename, f_handle.read()])

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
            self.selected_indep_var_files.data = " ".join([e[0] for e in new_data])

    def _is_identical(self, data):
        vprint("Check if files are identical", verbose_level=3)
        return len({e[1] for e in data}) == 1, "Uploaded files are not identical."
