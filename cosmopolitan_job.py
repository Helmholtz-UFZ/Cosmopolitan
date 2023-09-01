#!/usr/bin/python3
"""Module for a Cosmopolitan Job."""

import subprocess
from time import sleep

from db_manager import DataBaseManager, JobTable
from config import vprint
from cosmopolitan_job_form import CosmopolitanJobForm


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


class SshError(Exception):
    """Raised if ssh call repetidly failed."""

    pass


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
        """Delete the job in the data base.

        This method uses a DataBaseManager instance to delete the job entry from
        the database based on the job's unique identifier ('job_id').
        """
        vprint(f"Delet job {self.job_id}", verbose_level=2)
        db_manager = DataBaseManager()
        db_manager.delete_job(self.job_id)

    def submit(self):
        """Submit job to cluster."""
        vprint(f"Submit job {self.job_id}.", verbose_level=2)
        call_str = f"cluster_api/submit_job.sh {self.job_id}"
        vprint(call_str, verbose_level=3)
        out = self._ssh_call(call_str)
        vprint(out, verbose_level=3)
        self.submitted = True
        self.save()

    def _ssh_call(self, call_str):
        for i in range(1, 4):
            try:
                completed_process = subprocess.run(
                    call_str.split(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                )
                break
            except subprocess.CalledProcessError as exc:
                if i < 3:
                    sleep(2)
                    continue
                error_str = (
                    f"ERROR ssh call\nCommand\n{call_str}\nstdout:\n"
                    f"{exc.stdout.decode('UTF8')}\nstderr:\n{exc.stderr.decode('UTF8')}"
                )
                raise SshError(error_str)
        return completed_process.stdout.decode("UTF8")
