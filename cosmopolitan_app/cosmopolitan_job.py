#!/usr/bin/python3
"""Module for a Cosmopolitan Job."""

import json
import logging
import multiprocessing
import os
import shutil
import time
import traceback
from copy import deepcopy
from datetime import date
from logging.config import dictConfig
from test.mock_input import valid_form_data

import requests
from flask import Flask
from requests.exceptions import ConnectionError, Timeout
from soil_moisture_prediction.smp_cli import main

from cosmopolitan_app.config import (
    CLUSTER_AUTHORITY,
    CLUSTER_LOG_DIR,
    COMPUTATION_SCRIPT_TEMPLATE,
    DAYS_DELETE_NOT_SUMBITTED,
    DAYS_DELETE_SUMBITTED,
    DEBUG,
    LOAD_SCRIPT_TEMPLATE,
    WEB_WORK_DIR,
    slurm_default_parameters,
    slurm_header,
)
from cosmopolitan_app.cosmopolitan_job_form import CosmopolitanJobForm
from cosmopolitan_app.db_manager import DataBaseManager, JobNotFound, JobTable
from cosmopolitan_app.logger import get_logger_config_compuation, get_logger_config_web
from cosmopolitan_app.utils import (
    InvalidJobID,
    NoSlurmConnectionException,
    NotFinishedException,
    NotSubmittedException,
    lock_task,
)

LOG_SUFFIX = "logs"


def start_computation(work_dir):
    """Start a computation job."""
    dictConfig(get_logger_config_compuation(work_dir))
    try:
        main(verbosity="debug", work_dir=work_dir)
    except Exception as e:  # noqa
        dictConfig(get_logger_config_web(DEBUG))
        logging.error(f"Computation failed:\n{repr(e)}\n\n{traceback.format_exc()}")
    dictConfig(get_logger_config_web(DEBUG))
    logging.info("Computation finished.")


def run_test_job():
    """Run a test job to check if the computation works."""
    # Create a minimal Flask app for the context of CosmopolitanJobForm
    app = Flask("mock")
    with app.app_context():
        try:
            job = CosmopolitanJob(job_id=valid_form_data["job_id"])
            job.delete()
        except JobNotFound:
            pass

        logging.debug("Create form")
        form = CosmopolitanJobForm(formdata=valid_form_data, new=False)
        if not form.validate():
            raise ValueError("Test job form is not valid")
        job = CosmopolitanJob(form=form)
        job.save()
        logging.debug("Submit job")
        job.submit()

        for _ in range(1000):
            time.sleep(10)
            job.check_status()
            if job.status == "COMPLETED":
                logging.debug("Job finished.")
                break
            if job.status == "FAILED":
                raise ValueError("Job failed.")
        else:
            # One last chance if just started
            if job.status == "RUNNING":
                time.sleep(10)
                job.check_status()
            # Eve is presumably clocked with jobs or somethin hung up
            if job.status in ["PENDING", "RUNNING"]:
                raise ValueError("Job did not finish in time.")
            elif job.status == "COMPLETED":
                logging.debug("Job finished.")
            elif job.status == "FAILED":
                raise ValueError("Job failed.")
            else:
                raise ValueError(f"Job has unkown status {job.status}.")


@lock_task
def check_health_of_computation():
    """Start a test job and store the result in the DB."""
    logging.info("Start health check.")
    try:
        run_test_job()
    except Exception as e:  # noqa
        messsage = f"{repr(e)}\n\n{traceback.format_exc()}"
        logging.error(f"Health check failed:\n{messsage}")
        DataBaseManager.write_health(
            503,
            messsage,
        )
    else:
        DataBaseManager.write_health(
            200,
            "",
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
    status = "PENDING"
    version = None
    file_names = None

    def __init__(
        self,
        job_id=None,
        form=None,
        base_work_dir=WEB_WORK_DIR,
    ):
        """Init class either by id, by html form or make a new one."""
        # The class can be intilized backend for loading and saving. Depending on this
        # the work is not the same as the enviroment variable WEB_WORK_DIR.
        self.base_work_dir = base_work_dir
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
        working_dir = os.path.join(self.base_work_dir, self.job_id)
        if not os.path.isdir(working_dir):
            os.mkdir(working_dir)

        for f_name in self.file_names:
            if f_name in os.listdir(working_dir):
                continue
            with open(os.path.join(working_dir, f_name), "bw") as f_handle:
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
        working_dir = os.path.join(self.base_work_dir, self.job_id)
        if name == "file_names":
            return list(os.listdir(working_dir))
        if name == "files":
            value = []
            for f_name in os.listdir(working_dir):
                with open(os.path.join(working_dir, f_name), "rb") as f_handle:
                    value.append(f_handle.read())
            return value
        if name == "logs":
            log_file = os.path.join(working_dir, LOG_SUFFIX)
            if os.path.isfile(log_file):
                with open(os.path.join(working_dir, LOG_SUFFIX), "r") as f_handle:
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
        working_dir = os.path.join(self.base_work_dir, self.job_id)
        if not keep_work_dir:
            shutil.rmtree(working_dir)
        if delete_db:
            DataBaseManager.delete_job(self.job_id)

    def _submit_slurm(self, mode, depends_on=None):
        """Submit job using slurm rest api.

        The method build the url and json to send with the request. The method takes a
        mode "load", "comp", "safe" and a slurm job id to build the correct request.
        """
        logging.debug(f"Submit {mode}.")
        url = f"{CLUSTER_AUTHORITY}/slurmrest/slurm/v0.0.38/job/submit"
        job_para = deepcopy(slurm_default_parameters)
        name = f"{self.job_id}-{mode}"
        job_para["job"]["name"] = name
        if mode == "comp":
            job_para["job"]["standard_output"] += f"{self.job_id}/{LOG_SUFFIX}"
            job_para["job"]["standard_error"] = job_para["job"]["standard_output"]
            job_para["script"] = COMPUTATION_SCRIPT_TEMPLATE.format(job_id=self.job_id)
            job_para["job"]["partition"] = "compute"
        elif mode in ["load", "save"]:
            job_para["job"][
                "standard_output"
            ] += f"{CLUSTER_LOG_DIR}/{name}.{LOG_SUFFIX}"
            job_para["job"]["standard_error"] = job_para["job"]["standard_output"]
            job_para["script"] = LOAD_SCRIPT_TEMPLATE.format(
                job_id=self.job_id, mode=mode
            )
            job_para["job"]["partition"] = "transfer"
        else:
            raise ValueError("The submission mode can be 'comp', 'load', 'save'")

        if depends_on is not None:
            job_para["job"]["dependency"] = f"afterany:{depends_on}"

        logging.debug(json.dumps(job_para, indent=2))
        logging.debug(url)
        try:
            response = requests.post(
                url, json=job_para, headers=slurm_header, timeout=5
            )
        except (ConnectionError, Timeout):
            logging.warning("Slurm submit failed.")
            logging.warning("Can not connect to server.")
            logging.warning(f"URL: {url}")
            raise NoSlurmConnectionException(self.job_id)

        if response.status_code == 200:
            self.status = "PENDING"
            self.logs = ""
            return response.json()["job_id"]
        elif response.status_code == 404:
            logging.warning("Slurm submit failed.")
            logging.warning("Can not connect to server.")
            logging.warning(f"URL: {url}")
            raise NoSlurmConnectionException(self.job_id)
        else:
            logging.warning("Slurm submit failed.")
            logging.warning(f"URL: {url}")
            logging.warning(f"Status code: {response.status_code}")
            logging.warning(json.dumps(job_para, indent=2))
            logging.warning(json.dumps(response.json(), indent=2))
            try:
                logging.warning(json.dumps(response.json(), indent=2))
                self.logs = f"""Slurm error:
                {json.dumps(response.json()['errors'], indent=2)}"""
            except requests.exceptions.JSONDecodeError:
                logging.warning("No json returned!")
                self.logs = f"Slurm error:\nStatus code: {response.status_code}"
            self.status = "FAILED"
            return None

    def submit(self):
        """Start job in a nother subprocess."""
        logging.info(f"Submit job {self.job_id}.")
        if DataBaseManager.set_submitted(self.job_id):
            self.submitted = True
            self.status = "RUNNING"
            try:
                working_dir = os.path.join(self.base_work_dir, self.job_id)
                job = multiprocessing.Process(
                    target=start_computation, args=(working_dir,)
                )
                job.start()
            except Exception as e:  # noqa
                messsage = f"{repr(e)}\n\n{traceback.format_exc()}"
                logging.error(f"Job {self.job_id} failed to start.\n{messsage}")
                self.status = "FAILED"
            self.save()

    def submit_eve(self):
        """Submit job to cluster."""
        logging.info(f"Submit job {self.job_id}.")
        self.submitted = True
        self.cluster_job_id = None
        cluster_job_id = self._submit_slurm("load")
        if cluster_job_id is not None:
            self.cluster_job_id = self._submit_slurm("comp", depends_on=cluster_job_id)
        if self.cluster_job_id is not None:
            self._submit_slurm("save", depends_on=self.cluster_job_id)

        self.save_attributes(["status", "logs", "submitted", "cluster_job_id"])

    def _check_status(self, mode="slurm"):
        """Check status in current slurm manager or slurm db."""
        logging.debug(f"Check status at {mode}.")
        url = f"{CLUSTER_AUTHORITY}/slurmrest/{mode}/v0.0.38/job/{self.cluster_job_id}"
        try:
            response = requests.get(url, headers=slurm_header, timeout=5)
        except (ConnectionError, Timeout):
            logging.warning("Slurm check status failed.")
            logging.warning("Can not connect to server.")
            logging.warning(f"URL: {url}")
            raise NoSlurmConnectionException(self.job_id)

        if response.status_code != 200:
            logging.warning("Check status failed.")
            logging.warning(f"Status code: {response.status_code}")
            logging.warning(f"URL: {url}")
            logging.warning("Response:")
            try:
                logging.warning(json.dumps(response.json(), indent=2))
            except IndexError:
                logging.warning("No json returned!")
            response.raise_for_status()

        try:
            status = response.json()["jobs"][0]["job_state"]
        except IndexError:
            if response.json()["errors"][0]["description"] == "Nothing found":
                if mode == "slurm":
                    return self._check_status("slurmdb")
                else:
                    return None
            logging.warning("Check status failed.")
            logging.warning(f"Status code: {response.status_code}")
            logging.warning(f"URL: {url}")
            logging.warning("Response:")
            logging.warning(json.dumps(response.json()["errors"], indent=2))
            status = "FAILED"

        return status

    def check_status_eve(self):
        """Check status of job on the cluster."""
        logging.info(f"See progress of job {self.job_id}.")
        if self.status in ["COMPLETED", "FAILED"]:
            return

        status = self._check_status()

        self.status = status
        logging.debug(f"Status: {status}")
        self.save_attributes(["status"])

        if self.status in ["COMPLETED", "FAILED"]:
            # Reload to get results
            self.load()

    def get_paratameters_rfo_prediction(self):
        """Return parameter to load a RFo prediction model."""
        if not self.submitted:
            raise NotSubmittedException(self.job_id)

        if self.status != "COMPLETED":
            raise NotFinishedException(self.job_id)

        working_dir = os.path.join(self.base_work_dir, self.job_id)

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
