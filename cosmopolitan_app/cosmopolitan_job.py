#!/usr/bin/python3
"""Module for a Cosmopolitan Job."""

import json
import logging
import multiprocessing
import os
import shutil
import traceback
from datetime import date
from logging.config import dictConfig
from smtplib import SMTPAuthenticationError
from typing import Literal

from soil_moisture_prediction.__version__ import __version__ as smp_version
from soil_moisture_prediction.pydantic_models import InputParameters
from soil_moisture_prediction.smp_cli import main
from werkzeug.datastructures import MultiDict

from cosmopolitan_app.config import (
    DAYS_DELETE_NOT_SUMBITTED,
    DAYS_DELETE_SUMBITTED,
    DEBUG,
    JOB_WORK_DIR_TEMPLATE,
)
from cosmopolitan_app.cosmopolitan_job_form import CosmopolitanJobForm
from cosmopolitan_app.logger import get_logger_config_compuation, get_logger_config_web
from cosmopolitan_app.minio_manager import delete_from_bucket, sync_workdir
from cosmopolitan_app.postgres_manager import JobNotFound, JobTable, PostgresManager
from cosmopolitan_app.utils import (
    InvalidJobID,
    NotFinishedException,
    NotSubmittedException,
    send_finished_mail,
    send_submission_mail,
)

LOG_FILE_NAME = "logs"


def start_computation(job):
    """Start a computation job."""
    try:
        try:
            send_submission_mail(job)
        except SMTPAuthenticationError:
            logging.error("Failed to send submission mail.")
        dictConfig(
            get_logger_config_compuation(os.path.join(job.working_dir, LOG_FILE_NAME))
        )
        try:
            rfo_model = main(verbosity="debug", work_dir=job.working_dir)
            if rfo_model is None:
                job.status = "FAILED"
            else:
                job.status = "COMPLETED"
        except Exception as e:  # noqa
            # Log error to log file
            logging.error("An error occurred")
            logging.error(traceback.format_exc())
            # Log error to web logs
            dictConfig(get_logger_config_web(DEBUG))
            job.status = "FAILED"
            logging.error(f"Computation failed:\n{repr(e)}\n\n{traceback.format_exc()}")
        dictConfig(get_logger_config_web(DEBUG))
        logging.info("Computation finished.")

        job.save()
        try:
            send_finished_mail(job)
        except SMTPAuthenticationError:
            logging.error("Failed to send finished mail.")
    except Exception as e:  # noqa
        dictConfig(get_logger_config_web(DEBUG))
        job.status = "FAILED"
        logging.error(
            f"Job {job.job_id} failed:\n{repr(e)}\n\n{traceback.format_exc()}"
        )
        job.save()
        try:
            send_finished_mail(job)
        except SMTPAuthenticationError:
            logging.error("Failed to send finished mail.")


def get_attributes(clazz):
    """Retrieve a list of non-method attributes (instance variables) of a class."""
    return [
        name
        for name, attr in clazz.__dict__.items()
        if not name.startswith("__")
        and not callable(attr)
        and type(attr) is not staticmethod
    ]


class CosmopolitanJob:
    """This class represents a job submission by the user.

    It handles input from a Flask application, performs input integrity checks, submits
    jobs, and formats the output for the user.
    """

    form: CosmopolitanJobForm
    job_id: str
    start_date: date
    input_data: dict
    submitted: bool
    email: str
    notified_end: bool
    logs: str
    status: Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]
    version: str
    working_dir: str

    def __init__(
        self,
        job_id=None,
        form=None,
    ):
        """Init class either by id, by html form or make a new one."""
        if job_id is not None:
            self.job_id = job_id
            self.load()
        elif form is not None:
            self.form = form
            self._set_from_form()
        else:
            self._blank_job()

    def __str__(self):
        """Represent class as string."""
        return self.job_id

    def load(self):
        """Load job from database and store files in working dir."""
        logging.info(f"Load submission {self.job_id}")
        self.form = CosmopolitanJobForm()
        self.form.job_id.data = self.job_id
        # First check if job_id is valid
        if not self.form.job_id.validate(self.form):
            raise InvalidJobID(self.job_id)
        logging.debug(f"Job id: {self.job_id} is valid")

        for name, value in PostgresManager.get_job_columns(self.job_id).items():
            setattr(self, name, value)
        logging.debug(f"Job {self.job_id} loaded from database")

        self.working_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=self.job_id)
        os.makedirs(self.working_dir, exist_ok=True)
        sync_workdir(self.job_id)
        logging.debug(f"Job {self.job_id} synced to local work directory")

        # Set form data
        self.form = CosmopolitanJobForm()
        self.form.job_id.data = self.job_id
        self.form.previous_job_id.data = self.job_id
        self.form.email.data = self.email

        for name, field in self.form._fields.items():
            if name == "csrf_token":
                continue
            if field.type == "MultipleFileField" or name in [
                "previous_job_id",
                "email",
                "job_id",
            ]:
                continue
            if name in ["selected_pred_input", "selected_crn_files"]:
                field.data = json.dumps(self.input_data[name])
            else:
                field.data = self.input_data[name]

    def _blank_job(self):
        """Create a new job with a new job id."""
        logging.info("Create new submission")
        self.form = CosmopolitanJobForm(new=True)
        self._set_from_form()

    def _set_from_form(self):
        """Set the job attributes from a form."""
        logging.info(f"Set job attributes from form {self.form.job_id.data}")
        if not self.form.job_id.validate(self.form):
            raise InvalidJobID(self.form.job_id.data)

        self.job_id = self.form.job_id.data
        self.start_date = date.today()
        self._set_input_data_from_form()
        self.submitted = False
        self.email = self.form.email.data
        self.notified_end = False
        self.logs = ""
        self.status = "PENDING"
        self.version = smp_version
        self.working_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=self.job_id)
        os.makedirs(self.working_dir, exist_ok=True)
        draw_preview = self.form.validate_geometry()
        self.form.preview_area(draw_preview=draw_preview)

    def _set_input_data_from_form(self):
        self.input_data = {}
        for name, field in self.form._fields.items():
            if name == "csrf_token":
                continue
            if field.type == "MultipleFileField" or name in [
                "previous_job_id",
                "email",
                "job_id",
            ]:
                continue
            if name in ["selected_pred_input", "selected_crn_files"]:
                if field.data == "":
                    self.input_data[name] = field.data
                else:
                    self.input_data[name] = json.loads(field.data)
            else:
                self.input_data[name] = field.data

    def _get_column_data(self, name):
        if name == "logs":
            log_file = os.path.join(self.working_dir, LOG_FILE_NAME)
            if os.path.isfile(log_file):
                with open(
                    os.path.join(self.working_dir, LOG_FILE_NAME), "r"
                ) as f_handle:
                    return f_handle.read()

        return getattr(self, name)

    def save_attributes(self, attribute_list):
        """Save specicif job information to the database.

        This method takes a list of attributes, collects the current information of
        these attributes. It then uses a PostgresManager instance to add the collected
        data as to the respective column in the database.
        If the job can not be found in data base safe all attributes.
        """
        logging.debug(
            f"Save attributes {', '.join(attribute_list)} to job {self.job_id}"
        )
        data_to_insert = {name: self._get_column_data(name) for name in attribute_list}
        try:
            PostgresManager.update_column(self.job_id, data_to_insert)
        except JobNotFound:
            self.save()

    def save(self):
        """Save the job information to the database.

        This method retrieves the attributes of the current CosmopolitanJob
        instance. It then uses a PostgresManager instance to add the collected
        data as a new entry in the database.
        """
        logging.debug(f"Save job {self.job_id}")
        column_names = JobTable.__table__.columns.keys()
        data_to_insert = {name: self._get_column_data(name) for name in column_names}
        PostgresManager.add_entry(data_to_insert)
        sync_workdir(self.job_id)

    def delete(self, delete_work_dir=True, delete_db=True):
        """
        Delete the job in the data base.

        This method uses a PostgresManager instance to delete the job entry from
        the database based on the job's unique identifier ('job_id').
        """
        logging.debug(f"Delete job {self.job_id}")
        if delete_work_dir:
            shutil.rmtree(self.working_dir)
        if delete_db:
            PostgresManager.delete_job(self.job_id)
            delete_from_bucket(self.job_id)

    def submit(self):
        """Start job in a nother subprocess."""
        logging.info(f"Submit job {self.job_id}.")
        if PostgresManager.set_submitted(self.job_id):
            self.submitted = True
            self.status = "RUNNING"
            try:
                job = multiprocessing.Process(target=start_computation, args=(self,))
                job.start()
                logging.info(f"Job started with PID: {job.pid}.")
            except Exception as e:  # noqa
                messsage = f"{repr(e)}\n\n{traceback.format_exc()}"
                logging.error(f"Job {self.job_id} failed to start.\n{messsage}")
                self.status = "FAILED"
            self.save()

    def get_parameters_rfo_prediction(self):
        """Return parameter to load a RFo prediction model."""
        if not self.submitted:
            raise NotSubmittedException(self.job_id)

        if self.status != "COMPLETED":
            raise NotFinishedException(self.job_id)

        with open(os.path.join(self.working_dir, "parameters.json"), "r") as f_handle:
            input_parameters = InputParameters(**json.loads(f_handle.read()))

        return input_parameters, self.working_dir, True

    def time_to_life(self):
        """Return the number of days after which this job will be deleted."""
        days_passed = (date.today() - self.start_date).days
        if self.submitted:
            return DAYS_DELETE_SUMBITTED - days_passed
        else:
            return DAYS_DELETE_NOT_SUMBITTED - days_passed

    def copy_output_files(self, parent_work_dir):
        """Remove all output files from the working directory."""
        logging.info(f"Remove output files of job {self.job_id}.")
        for file in os.listdir(parent_work_dir):
            if file.startswith(("crn_", "pred_")):
                source_path = os.path.join(parent_work_dir, file)
                target_path = os.path.join(self.working_dir, file)
                shutil.copy(source_path, target_path)

    def spawn(self) -> "CosmopolitanJob":
        """Clone the job."""
        logging.info(f"Spawn job {self.job_id}.")
        new_form = CosmopolitanJobForm(formdata=MultiDict(self.form.data))
        i = 1
        while True:
            new_form.job_id.data = f"{self.job_id}_child_{i}"
            if not PostgresManager.check_existence(new_form.job_id.data):
                new_form.previous_job_id.data = new_form.job_id.data
                # Without valdiation the attribute input_dir is not set would cause an
                # error when instantiating the CosmopolitanJob class
                new_form.validate_job_id(new_form.job_id)
                break
            i += 1

        new_job = CosmopolitanJob(form=new_form)
        new_job.copy_output_files(self.working_dir)
        new_job.save()
        return new_job
