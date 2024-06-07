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

from soil_moisture_prediction.pydantic_models import InputParamaters
from soil_moisture_prediction.smp_cli import main

from cosmopolitan_app.config import (
    DAYS_DELETE_NOT_SUMBITTED,
    DAYS_DELETE_SUMBITTED,
    DEBUG,
    WEB_WORK_DIR,
)
from cosmopolitan_app.cosmopolitan_job_form import CosmopolitanJobForm
from cosmopolitan_app.db_manager import DataBaseManager, JobNotFound, JobTable
from cosmopolitan_app.logger import get_logger_config_compuation, get_logger_config_web
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
        send_submission_mail(job)
        dictConfig(
            get_logger_config_compuation(os.path.join(job.working_dir, LOG_FILE_NAME))
        )
        try:
            main(verbosity="debug", work_dir=job.working_dir)
            job.status = "COMPLETED"
        except Exception as e:  # noqa
            dictConfig(get_logger_config_web(DEBUG))
            job.status = "FAILED"
            logging.error(f"Computation failed:\n{repr(e)}\n\n{traceback.format_exc()}")
        dictConfig(get_logger_config_web(DEBUG))
        logging.info("Computation finished.")
        job.save()
        send_finished_mail(job)
    except Exception as e:  # noqa
        dictConfig(get_logger_config_web(DEBUG))
        logging.error(
            f"Job {job.job_id} failed:\n{repr(e)}\n\n{traceback.format_exc()}"
        )


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

    It handles input from a Flask application, performs input integrity checks, submits
    jobs, and formats the output for the user.
    """

    form = None
    job_id = None
    start_date = None
    input_data = None
    submitted = False
    email = None
    notified_end = False
    logs = None
    status = "PENDING"
    version = None
    file_names = None

    def __init__(
        self,
        job_id=None,
        form=None,
    ):
        """Init class either by id, by html form or make a new one."""
        if job_id is not None:
            logging.debug(f"Load submission {job_id}")
            form = CosmopolitanJobForm()
            form.job_id.data = job_id
            if form.job_id.validate(form):
                self.job_id = job_id
                self.load()
            else:
                raise InvalidJobID(job_id)
        elif form is not None:
            logging.debug("Set from form")
            self._set_from_form(form)
        else:
            logging.debug("Make blank job")
            self._blank_job()

    def __str__(self):
        """Represent class as string."""
        return self.job_id

    def load(self):
        """Load job from database and store files in working dir."""
        logging.debug("Load job")

        # Get data from database
        class_attributes = get_attributes(CosmopolitanJob)
        for name, value in DataBaseManager.get_job_columns(self.job_id).items():
            if name == "files":
                files = value
                continue
            if name not in class_attributes:
                raise AttributeError(f"CosmopolitanJob has no attribute named {name}")
            setattr(self, name, value)

        # Copy files to working directory
        self.working_dir = os.path.join(WEB_WORK_DIR, self.job_id)
        os.makedirs(self.working_dir, exist_ok=True)

        for f_name in self.file_names:
            if f_name in os.listdir(self.working_dir):
                continue
            with open(os.path.join(self.working_dir, f_name), "bw") as f_handle:
                f_handle.write(files[self.file_names.index(f_name)])

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
            if name in ["selected_pred_files", "selected_crn_files"]:
                field.data = json.dumps(self.input_data[name])
            else:
                field.data = self.input_data[name]

    def _blank_job(self):
        while True:
            job_form = CosmopolitanJobForm()
            if DataBaseManager.check_existence(job_form.job_id.data):
                logging.debug(f"Job id: {job_form.job_id.data} already exist")
                continue
            break
        self.form = job_form
        self.job_id = job_form.job_id.data
        self.start_date = date.today()

    def _set_from_form(self, form):
        if type(form) is not CosmopolitanJobForm:
            raise TypeError("Form must be a CosmopolitanJobForm")

        self.form = form
        self.input_data = {}
        self.start_date = date.today()
        self.job_id = self.form.job_id.data
        self.working_dir = os.path.join(WEB_WORK_DIR, self.job_id)
        self.email = self.form.email.data

        for name, field in self.form._fields.items():
            if name == "csrf_token":
                continue
            if field.type == "MultipleFileField" or name in [
                "previous_job_id",
                "email",
                "job_id",
            ]:
                continue
            if name in ["selected_pred_files", "selected_crn_files"]:
                self.input_data[name] = json.loads(field.data)
            else:
                self.input_data[name] = field.data

    def _get_column_data(self, name):
        if name == "file_names":
            return list(os.listdir(self.working_dir))
        if name == "files":
            value = []
            for f_name in os.listdir(self.working_dir):
                with open(os.path.join(self.working_dir, f_name), "rb") as f_handle:
                    value.append(f_handle.read())
            return value
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
        these attributes. It then uses a DataBaseManager instance to add the collected
        data as to the respective column in the database.
        If the job can not be found in data base safe all attributes.
        """
        logging.debug(
            f"Save attributes {', '.join(attribute_list)} to job {self.job_id}"
        )
        data_to_insert = {name: self._get_column_data(name) for name in attribute_list}
        try:
            DataBaseManager.update_column(self.job_id, data_to_insert)
        except JobNotFound:
            self.save()

    def save(self):
        """Save the job information to the database.

        This method retrieves the attributes of the current CosmopolitanJob
        instance. It then uses a DataBaseManager instance to add the collected
        data as a new entry in the database.
        """
        logging.debug(f"Save job {self.job_id}")
        column_names = JobTable.__table__.columns.keys()
        data_to_insert = {name: self._get_column_data(name) for name in column_names}
        DataBaseManager.add_entry(data_to_insert)

    def delete(self, keep_work_dir=False, delete_db=True):
        """
        Delete the job in the data base.

        This method uses a DataBaseManager instance to delete the job entry from
        the database based on the job's unique identifier ('job_id').
        """
        logging.debug(f"Delete job {self.job_id}")
        if not keep_work_dir:
            shutil.rmtree(self.working_dir)
        if delete_db:
            DataBaseManager.delete_job(self.job_id)

    def submit(self):
        """Start job in a nother subprocess."""
        logging.info(f"Submit job {self.job_id}.")
        if DataBaseManager.set_submitted(self.job_id):
            self.submitted = True
            self.status = "RUNNING"
            self.save()
            try:
                job = multiprocessing.Process(target=start_computation, args=(self,))
                job.start()
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
            input_parameters = InputParamaters(**json.loads(f_handle.read()))

        return input_parameters, self.working_dir, True

    def time_to_life(self):
        """Return the number of days after which this job will be deleted."""
        days_passed = (date.today() - self.start_date).days
        if not self.submitted:
            return DAYS_DELETE_SUMBITTED - days_passed
        else:
            return DAYS_DELETE_NOT_SUMBITTED - days_passed
