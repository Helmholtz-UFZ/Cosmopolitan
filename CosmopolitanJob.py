#!/usr/bin/python3
"""Module for a Cosmopolitan Job."""


import datetime
import os

from coolname import generate

from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename

from wtforms import StringField, MultipleFileField
from wtforms.validators import DataRequired, Length, ValidationError, Regexp
from wtforms.widgets import TextInput


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
            if field.type == "MultipleFileField":
                self.input[name] = field.checked_files
            else:
                self.input[name] = field.data


class CosmopolitanJobForm(FlaskForm):
    """WTF form for Cosmopolitan input."""

    job_id = StringField(
        "Job ID",
        default="_".join(generate(3)),
        description='Identifier for your submission. Only letters, numbers and "_".',
        widget=DynamicSizeTextInput(),
        validators=[
            DataRequired(),
            Length(min=8, max=50),
            Regexp(
                r"^\w+$",
                message="Username must contain only letters numbers or underscore",
            ),
        ],
    )

    indep_var_files = MultipleFileField(
        "Independent variable files",
        validators=[DataRequired()],
    )

    def validate_job_id(self, field):
        """Validate job id."""
        if job_id_exist(field.data):
            raise ValidationError("Job id already exist")

    def _check_indep_var_files(self, file_names):
        # TODO Dummy
        vprint("Check if files are identical", verbose_level=3)
        file_content_list = []
        for file_name in file_names:
            with open(
                os.path.join(UPLOAD_DIR, file_name), "r", encoding="UTF-8"
            ) as f_handle:
                file_content_list.append(f_handle.read())
        return len(set(file_content_list)) == 1

    def _check_files(self):
        """Upload files and check integrity."""
        file_names = []
        vprint("Check files integrity", verbose_level=3)
        for indep_var_file in self.indep_var_files.data:
            file_name = secure_filename(indep_var_file.filename)
            file_names.append(file_name)
            indep_var_file.save(os.path.join(UPLOAD_DIR, file_name))

        if self._check_indep_var_files(file_names):
            for file_name in file_names:
                os.replace(
                    os.path.join(UPLOAD_DIR, file_name),
                    os.path.join(INPUT_DIR, file_name),
                )
            self.indep_var_files.checked_files = file_names
            return True
        else:
            for file_name in file_names:
                os.remove(os.path.join(UPLOAD_DIR, file_name))
            self.indep_var_files.errors = ["Uploaded files are not identical."]
            return False

    def validate_on_submit(self):
        """Validate the form by the inheritence and than upload files and check.

        Make sure that html form has 'enctype="multipart/form-data' tag.
        """
        vprint("Validate form", verbose_level=2)
        if super().validate_on_submit():
            return self._check_files()
        else:
            return False


DEV_MODE = True
# 0 means silence, 3 is highest level of verbosity
VERBOSE_LEVEL = 3
WORK_DIR = "./"
# Directory where files are first uploaded and then checked
UPLOAD_DIR = os.path.join(WORK_DIR, "upload")
# The directory for the input files that have been validated.
INPUT_DIR = os.path.join(WORK_DIR, "input")
