#!/usr/bin/python3
"""Module for a Cosmopolitan Job."""

import json
import logging
import os
from datetime import date

from cosmopolitan_app.config import (
    DAYS_DELETE_NOT_SUMBITTED,
    DAYS_DELETE_SUMBITTED,
    WEB_INPUT_DIR,
)
from cosmopolitan_app.cosmopolitan_job_form import CosmopolitanJobForm
from cosmopolitan_app.db_manager import DataBaseManager, JobTable
from cosmopolitan_app.utils import (
    InvalidJobID,
    NotFinishedException,
    NotSubmittedException,
    ssh_call,
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
    jobs to a cluster, and formats the output for the user.
    """

    form = None
    job_id = None
    start_date = None
    input_data = None
    submitted = False
    cluster_job_id = None
    email = None
    notified_end = False
    logs = None
    status = None
    version = None

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
                self._load_job(job_id)
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

    def _load_job(self, job_id):
        logging.debug("Load job")
        db_manager = DataBaseManager()
        class_attributes = get_attributes(CosmopolitanJob)
        for name, value in db_manager.get_job_columns(job_id).items():
            if name not in class_attributes:
                raise AttributeError(f"CosmopolitanJob has no attribute named {name}")
            setattr(self, name, value)
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

        self.form.previous_job_id.data = self.form.job_id.data

    def _blank_job(self):
        db_manager = DataBaseManager()
        while True:
            job_form = CosmopolitanJobForm()
            if db_manager.check_existence(job_form.job_id.data):
                logging.debug(
                    f"Job id: {job_form.job_id.data} already exist", verbose_level=3
                )
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
        self.job_id = self.form.job_id.data
        self.email = self.form.email.data
        self.start_date = date.today()

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

    def save(self):
        """Save the job information to the database.

        This method retrieves the attributes of the current CosmopolitanJob
        instance. It then uses a DataBaseManager instance to add the collected
        data as a new entry in the database.
        """
        logging.debug(f"Save job {self.job_id}")
        column_names = JobTable.__table__.columns.keys()
        data_to_insert = {name: getattr(self, name) for name in column_names}
        db_manager = DataBaseManager()
        db_manager.add_entry(data_to_insert)

    def delete(self):
        """
        Delete the job in the data base.

        This method uses a DataBaseManager instance to delete the job entry from
        the database based on the job's unique identifier ('job_id').
        """
        logging.debug(f"Delete job {self.job_id}")
        db_manager = DataBaseManager()
        db_manager.delete_job(self.job_id)

    def submit(self):
        """Submit job to cluster."""
        logging.debug(f"Submit job {self.job_id}.")
        call_str = f"submit_job.sh {self.job_id}"
        out = ssh_call(call_str)
        self.submitted = True
        self.cluster_job_id = out.split()[-1]
        self.status = "PENDING"
        self.logs = ""
        self.save()

    def check_status(self):
        """Check status of job on the cluster."""
        logging.info(f"See progress of job {self.job_id}.")
        if self.status in ["COMPLETED", "FAILED"]:
            return
        call_str = f"check_status.sh {self.job_id} {self.cluster_job_id}"
        out = ssh_call(call_str)
        self.status = out.split()[0]
        self.logs = "\n".join(out.split("\n")[1:])
        if self.status == "COMPLETED":
            logging.debug("Job completed.")
            call_str = f"get_results.sh {self.job_id}"
            out = ssh_call(call_str)
        self.save()

    def get_paratameters_rfo_prediction(self):
        """Return parameter to load a RFo prediction model."""
        if not self.submitted:
            raise NotSubmittedException(self.job_id)

        if self.status != "COMPLETED":
            raise NotFinishedException(self.job_id)

        working_dir = os.path.join(WEB_INPUT_DIR, self.job_id)

        with open(os.path.join(working_dir, "parameters.json"), "r") as f_handle:
            input_data = json.loads(f_handle.read())

        return input_data, working_dir, True

    def time_to_life(self):
        """Return the number of days after which this job will be deleted."""
        days_passed = (date.today() - self.start_date).days
        if not self.submitted:
            return DAYS_DELETE_SUMBITTED - days_passed
        else:
            return DAYS_DELETE_NOT_SUMBITTED - days_passed
