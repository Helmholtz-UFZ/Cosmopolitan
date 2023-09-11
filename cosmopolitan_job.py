#!/usr/bin/python3
"""Module for a Cosmopolitan Job."""

from datetime import date
import json

from db_manager import DataBaseManager, JobTable
from config import vprint, ssh_call
from cosmopolitan_job_form import CosmopolitanJobForm
from cosmopolitan_job_output_presentation import CosmopolitanJobOutputPresentation


def get_attributes(clazz):
    """Retrieve a list of non-method attributes (instance variables) of a class."""
    return [
        name
        for name, attr in clazz.__dict__.items()
        if not name.startswith("__")
        and not callable(attr)
        and not type(attr) is staticmethod
    ]


class InvalidJobID(Exception):
    """Raised by CosmopolitanJob if init with invalid job id."""

    pass


class CosmopolitanJob:
    """This class represents a job submission by the user.

    It handles input from a Flask application, performs input integrity checks,
    submits jobs to a cluster, and formats the output for the user.
    """

    form = None
    output_presentation = None
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
        if job_id:
            vprint(f"Load submission {job_id}", verbose_level=2)
            form = CosmopolitanJobForm()
            form.job_id.data = job_id
            if form.job_id.validate(form):
                self._load_job(job_id)
            else:
                raise InvalidJobID(f"{job_id} is not a valid job_id.")
        elif form:
            vprint("Set from form", verbose_level=2)
            self._set_from_form(form)
        else:
            vprint("Make blank job", verbose_level=2)
            self._blank_job()
        self.output_presentation = CosmopolitanJobOutputPresentation()

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
            else:
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
                vprint(f"Job id: {job_form.job_id.data} already exist", verbose_level=3)
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
            else:
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
        vprint(f"Save job {self.job_id}", verbose_level=2)
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
        vprint(f"Delet job {self.job_id}", verbose_level=2)
        db_manager = DataBaseManager()
        db_manager.delete_job(self.job_id)

    def submit(self):
        """Submit job to cluster."""
        vprint(f"Submit job {self.job_id}.", verbose_level=2)
        call_str = f"submit_job.sh {self.job_id}"
        out = ssh_call(call_str)
        self.submitted = True
        self.cluster_job_id = out.split()[-1]
        self.status = "RUNNING"
        self.save()

    def check_status(self):
        """Check status of job on the cluster."""
        vprint(f"See progress of job {self.job_id}.", verbose_level=2)
        if self.status in ["COMPLETED", "FAILED"]:
            return
        call_str = f"check_status.sh {self.job_id} {self.cluster_job_id}"
        out = ssh_call(call_str)
        self.status = out.split()[0]
        if self.status == "COMPLETED":
            call_str = f"get_results.sh {self.job_id}"
            out = ssh_call(call_str)

        self.logs = "\n".join(out.split("\n")[1:])
        self.save()
