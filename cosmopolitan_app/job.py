#!/usr/bin/python3
"""Module for a Cosmopolitan Job."""

import json
import logging
import multiprocessing
import os
import shutil
import traceback
from copy import deepcopy
from datetime import date
from logging.config import dictConfig
from smtplib import SMTPAuthenticationError
from typing import Literal, Self

import cairo
import staticmaps
from coolname import generate
from pyproj import Transformer
from soil_moisture_prediction.__version__ import __version__ as smp_version
from soil_moisture_prediction.smp_cli import main

from cosmopolitan_app.config import (
    DAYS_DELETE_NOT_SUMBITTED,
    DAYS_DELETE_SUMBITTED,
    DEBUG,
    JOB_WORK_DIR_TEMPLATE,
)
from cosmopolitan_app.logger import get_logger_config_compuation, get_logger_config_web
from cosmopolitan_app.minio_manager import delete_from_bucket, sync_workdir
from cosmopolitan_app.postgres_manager import JobNotFound, JobTable, PostgresManager
from cosmopolitan_app.pydantic_models import ModelWebsite, validate_job_id
from cosmopolitan_app.utils import (
    InvalidJobID,
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


class Job:
    """This class represents a job submission by the user.

    It handles input from a Flask application, performs input integrity checks, submits
    jobs, and formats the output for the user.
    """

    job_id: str
    model: ModelWebsite
    start_date: date
    submitted: bool
    email: str
    notified_end: bool
    logs: str
    status: Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]
    version: str
    working_dir: str
    preview_area_filename: str = "preview_area.png"

    def __init__(
        self,
        job_id=None,
        model=None,
    ):
        """Init class either by id, by html form or make a new one."""
        if job_id is not None:
            self.job_id = job_id
            self.load()
        elif model is not None:
            self._init_from_model(model)
        else:
            self._blank_job()

    def __str__(self):
        """Represent class as string."""
        return self.job_id

    def load(self):
        """Load job from database and store files in working dir."""
        logging.info(f"Load submission {self.job_id}")

        try:
            validate_job_id(self.job_id)
        except ValueError:
            raise InvalidJobID(self.job_id)

        logging.debug(f"Job id: {self.job_id} is valid")

        for name, value in PostgresManager.get_job_columns(self.job_id).items():
            if name == "input_data":
                logging.debug(json.loads(value))
                self.model = ModelWebsite(**json.loads(value))
            setattr(self, name, value)

        logging.debug(f"Job {self.job_id} loaded from database")

        self.working_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=self.job_id)
        os.makedirs(self.working_dir, exist_ok=True)
        sync_workdir(self.job_id)
        logging.debug(f"Job {self.job_id} synced to local work directory")

    def _init_from_model(self, model):
        """Initialize job from model."""
        self.model = model
        self.start_date = date.today()
        self.submitted = False
        self.notified_end = False
        self.logs = ""
        self.status = "PENDING"
        self.version = smp_version
        self.working_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=self.job_id)
        os.makedirs(self.working_dir, exist_ok=True)
        self.preview_area(draw_preview=True)
        self.save()

    def _blank_job(self):
        """Create a new job with a new job id."""
        logging.info("Create new submission")

        while True:
            job_id = "_".join(generate(3))
            if not PostgresManager.check_existence(job_id):
                break

        self.job_id = job_id
        self.model = ModelWebsite(job_id=job_id)
        self.start_date = date.today()
        self.submitted = False
        self.notified_end = False
        self.logs = ""
        self.status = "PENDING"
        self.version = smp_version
        self.working_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=self.job_id)
        os.makedirs(self.working_dir, exist_ok=True)
        self.preview_area(draw_preview=True)
        self.save()

    def preview_area(self, draw_preview: bool = True):
        """Draw a preview of the area."""
        logging.debug("Draw preview")
        width = 800
        height = 500
        if not draw_preview:
            logging.debug("Draw empty preview")
            self._draw_empty_preview(width, height)
            return

        logging.debug("Draw area preview")
        context = staticmaps.Context()
        context.set_tile_provider(staticmaps.tile_provider_OSM)

        transformer = Transformer.from_crs(
            self.model.projection, "EPSG:4326", always_xy=True
        )
        lon_min, lat_min = transformer.transform(self.model.area_x1, self.model.area_y1)
        lon_max, lat_max = transformer.transform(self.model.area_x2, self.model.area_y2)
        bbox = [
            (lat_min, lon_min),
            (lat_max, lon_min),
            (lat_max, lon_max),
            (lat_min, lon_max),
            (lat_min, lon_min),
        ]

        context.add_object(
            staticmaps.Area(
                [staticmaps.create_latlng(lat, lng) for lat, lng in bbox],
                fill_color=staticmaps.parse_color("#00FF003F"),
                width=2,
                color=staticmaps.BLUE,
            )
        )

        image = context.render_cairo(width, height)
        image.write_to_png(os.path.join(self.working_dir, self.preview_area_filename))

    def _draw_empty_preview(self, width, height):
        """Draw an empty preview if geometry is not valid."""
        # Create a new Cairo surface and context
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(surface)

        # Fill background with white
        ctx.set_source_rgb(1, 1, 1)
        ctx.paint()

        # Set up text properties
        ctx.set_source_rgb(0.5, 0.5, 0.5)  # Gray color for text
        ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(32)

        # Center the text
        text = "No preview available"
        extents = ctx.text_extents(text)
        x = width / 2 - extents.width / 2
        y = height / 2 + extents.height / 2

        # Draw the text
        ctx.move_to(x, y)
        ctx.show_text(text)

        surface.write_to_png(os.path.join(self.working_dir, self.preview_area_filename))

    def _get_column_data(self, name):
        if name == "logs":
            log_file = os.path.join(self.working_dir, LOG_FILE_NAME)
            if os.path.isfile(log_file):
                with open(
                    os.path.join(self.working_dir, LOG_FILE_NAME), "r"
                ) as f_handle:
                    return f_handle.read()

        if name == "input_data":
            return json.dumps(self.model.dict())

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
        for key, value in data_to_insert.items():
            # Try to load json data into model -> assures that only vaild data is saved
            if key == "input_data":
                ModelWebsite(**json.loads(value))
                logging.debug(json.loads(value))
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

    def time_to_life(self):
        """Return the number of days after which this job will be deleted."""
        days_passed = (date.today() - self.start_date).days
        if self.submitted:
            return DAYS_DELETE_SUMBITTED - days_passed
        else:
            return DAYS_DELETE_NOT_SUMBITTED - days_passed

    def copy_output_files(self, parent_work_dir):
        """Copy output files of the job to the working directory of the job."""
        logging.info(f"Remove output files of job {self.job_id}.")
        for file in os.listdir(parent_work_dir):
            if file.startswith(("crn_", "pred_")):
                source_path = os.path.join(parent_work_dir, file)
                target_path = os.path.join(self.working_dir, file)
                shutil.copy(source_path, target_path)

    def spawn(self) -> Self:
        """Clone the job."""
        logging.info(f"Spawn job {self.job_id}.")
        new_model = deepcopy(self.model)
        i = 1
        while True:
            new_model.job_id = f"{self.job_id}_child_{i}"
            if not PostgresManager.check_existence(new_model.job_id):
                break
            i += 1

        new_job = Job(model=new_model)
        new_job.copy_output_files(self.working_dir)
        new_job.save()
        return new_job
