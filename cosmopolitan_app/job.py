#!/usr/bin/python3
"""Module for a Cosmopolitan Job."""

import base64
import binascii
import glob
import io
import json
import logging
import os
import random
import shutil
import time
import traceback
from copy import deepcopy
from datetime import date, datetime
from typing import Literal, Self

import coolname
import requests
import staticmaps
from pyproj import Transformer
from soil_moisture_prediction.__version__ import __version__ as smp_version
from soil_moisture_prediction.area_geometry import RectGeom
from soil_moisture_prediction.input_file_parser import (
    FileValidationError,
    PredictorParser,
    SoilMoistureParser,
)
from werkzeug.utils import secure_filename

from cosmopolitan_app.background_job_manager import background_job_manager
from cosmopolitan_app.config import JOB_WORK_DIR_TEMPLATE, MAINTAINER_EMAIL
from cosmopolitan_app.constants import (
    DAYS_DELETE_NOT_SUMBITTED,
    DAYS_DELETE_SUMBITTED,
    LOG_FILE_NAME,
)
from cosmopolitan_app.error_handling import (
    InvalidJobID,
    JobExists,
    JobNotFound,
    MapTileDownloadError,
    NoMeasurementPointsError,
)
from cosmopolitan_app.object_storage_manager import (
    delete_directory_from_storage,
    delete_file_from_storage,
    get_files,
    save_files,
)
from cosmopolitan_app.postgres_manager import JobTable, PostgresManager
from cosmopolitan_app.pydantic_models import ModelWebsite, validate_job_id
from cosmopolitan_app.timeio_info import type_id_dict
from cosmopolitan_app.utils import send_mail

log = logging.getLogger(__name__)


def find_unique_job_id() -> str:
    """Find a unique job id."""
    seed = os.urandom(128)
    coolname.replace_random(random.Random(seed))

    while True:
        job_id = "_".join(coolname.generate(3))
        if not PostgresManager.check_existence(job_id):
            break
    return job_id


def draw_preview(
    filepath,
    min_lon,
    min_lat,
    max_lon,
    max_lat,
    types,
    start_date,
    end_date,
    max_retries=3,
    retry_delay=2.0,
):
    """Draw a preview of the area and add measurement points.

    Args:
        filepath: Path to save PNG file. If None, returns base64 encoded image.
        min_lon, min_lat, max_lon, max_lat: Bounding box coordinates
        types: List of measurement types
        start_date, end_date: Date range for measurements
        max_retries: Maximum number of retry attempts for network failures
        retry_delay: Initial delay between retries in seconds (doubles each retry)

    Returns:
        If filepath is None: base64 encoded image string
        If filepath is provided: None (writes to file)

    Raises:
        requests.exceptions.ConnectionError: If tile download fails after all retries
    """
    log.info(
        f"Draw preview for area: {min_lat}, {min_lon}, {max_lat}, {max_lon}",
        extra={"tag": "job_submission"},
    )
    width = 800
    height = 500
    context = staticmaps.Context()
    context.set_tile_provider(staticmaps.tile_provider_OSM)

    # Bbox for PostGIS query
    bbox_pg = (min_lon, min_lat, max_lon, max_lat)

    # Area polygon for staticmaps (lat, lon order)
    area_poly = [
        (min_lat, min_lon),
        (max_lat, min_lon),
        (max_lat, max_lon),
        (min_lat, max_lon),
        (min_lat, min_lon),
    ]

    # Add area polygon first
    context.add_object(
        staticmaps.Area(
            [staticmaps.create_latlng(lat, lon) for lat, lon in area_poly],
            fill_color=staticmaps.parse_color("#00FF003F"),
            width=3,
            color=staticmaps.BLUE,
        )
    )

    # Retrieve measurement points
    points_df = PostgresManager.get_measurement_points(
        bbox_pg, types, start_date, end_date, representative=True
    )

    # Map sensor type to color
    type_color = {
        "train": staticmaps.GREEN,
        "station": staticmaps.BLUE,
        "rover": staticmaps.RED,
    }

    # Add markers on top of area
    for _, row in points_df.iterrows():
        sensor_type = type_id_dict[row["sensor_id"]]
        color = type_color[sensor_type]
        context.add_object(
            staticmaps.Marker(
                staticmaps.create_latlng(row["latitude"], row["longitude"]),
                color=color,
                size=8,
            )
        )

    # Render the image with retry logic for network failures
    for attempt in range(max_retries):
        try:
            image = context.render_cairo(width, height)

            if filepath is None:
                # Return base64 encoded image
                buf = io.BytesIO()
                image.write_to_png(buf)
                buf.seek(0)
                return base64.b64encode(buf.read()).decode()
            else:
                # Write to file
                image.write_to_png(filepath)
                return None
        except (requests.exceptions.ConnectionError, ConnectionResetError) as e:
            if attempt < max_retries - 1:
                delay = retry_delay * (2**attempt)
                log.warning(
                    f"Map tile download failed (attempt {attempt + 1}/{max_retries}), "
                    f"retrying in {delay:.1f}s: {type(e).__name__}: {e}",
                    extra={"tag": "job_submission"},
                )
                time.sleep(delay)
            else:
                log.error(
                    f"Map tile download failed after {max_retries} attempts: {type(e).__name__}: {e}",  # noqa
                    extra={"tag": "job_submission"},
                )
                raise MapTileDownloadError(
                    f"Failed to download map tiles after {max_retries} attempts"
                ) from e


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
    prepared_input: bool
    logs: str
    status: Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]
    version: str
    working_dir: str
    celery_task_id: str
    preview_area_filename_template: str = "preview_area_{position}.png"
    original_file_prefix: str = "orginal"

    def __init__(
        self,
        job_id=None,
        new_job_id=None,
        model=None,
    ):
        """Init class either by id, by html form or make a new one."""
        if job_id is not None:
            self.job_id = job_id
            self.load()
        elif model is not None:
            self._init_from_model(model)
        else:
            self._blank_job(new_job_id)

    def __str__(self):
        """Represent class as string."""
        return self.job_id

    def load(self):
        """Load job from database and store files in working dir."""
        log.info(f"Load submission {self.job_id}", extra={"tag": "job_submission"})

        try:
            validate_job_id(self.job_id)
        except ValueError:
            raise InvalidJobID(self.job_id)

        log.debug(f"Job id: {self.job_id} is valid", extra={"tag": "job_submission"})

        for name, value in PostgresManager.get_job_columns(self.job_id).items():
            log.debug((f"Load column {name}"), extra={"tag": "job_submission"})
            if name == "input_data":
                self.model = ModelWebsite(**json.loads(value))
            setattr(self, str(name), value)

        log.debug(
            f"Job {self.job_id} loaded from database", extra={"tag": "job_submission"}
        )

        self.working_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=self.job_id)
        os.makedirs(self.working_dir, exist_ok=True)
        get_files(self.job_id)
        log.debug(
            f"Job {self.job_id} files downloaded from object storage",
            extra={"tag": "job_submission"},
        )

    def _init_from_model(self, model):
        """Initialize job from model."""
        self.job_id = model.job_id
        self.model = model
        self.start_date = date.today()
        self.submitted = False
        self.notified_end = False
        self.prepared_input = False
        self.logs = ""
        self.status = "PENDING"
        self.version = smp_version
        self.celery_task_id = None
        self.working_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=self.job_id)
        os.makedirs(self.working_dir, exist_ok=True)
        self.dump_parameters()
        self.save()

    def _blank_job(self, new_job_id):
        """Create a new job with a new job id."""
        log.info("Create new job", extra={"tag": "job_submission"})

        if new_job_id is None:
            job_id = find_unique_job_id()
        else:
            if PostgresManager.check_existence(new_job_id):
                raise JobExists
            job_id = new_job_id

        self.job_id = job_id
        self.model = ModelWebsite()
        self.model.job_id = job_id
        self.start_date = date.today()
        self.submitted = False
        self.notified_end = False
        self.prepared_input = False
        self.logs = ""
        self.status = "PENDING"
        self.version = smp_version
        self.celery_task_id = None
        self.working_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=self.job_id)
        shutil.rmtree(self.working_dir, ignore_errors=True)
        os.makedirs(self.working_dir, exist_ok=True)
        self.dump_parameters()
        self.save()

    def dump_parameters(self):
        """Dump the parameters of the model to the working directory."""
        log.debug("Dump parameters to JSON file", extra={"tag": "job_submission"})
        with open(
            os.path.join(self.working_dir, "parameters.json"), "w", encoding="UTF-8"
        ) as f_handle:
            f_handle.write(
                self.model.model_dump_json(
                    indent=4,
                    exclude_unset=False,
                    exclude_none=True,
                    exclude_defaults=False,
                )
            )

    def delete_item(self, item_name):
        """Delete a file or folder both locally and from object storage.

        Args:
            item_name: Name of the file or folder to delete (relative to working_dir)
        """
        log.debug(
            f"Delete item {item_name} from job {self.job_id}",
            extra={"tag": "job_submission"},
        )

        # Delete from local storage
        item_path = os.path.join(self.working_dir, item_name)
        if os.path.isfile(item_path):
            os.remove(item_path)
            # Delete file from object storage
            delete_file_from_storage(f"{self.job_id}/{item_name}")
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)
            # Delete directory from object storage
            delete_directory_from_storage(f"{self.job_id}/{item_name}")

    def preview_area(self, draw_empty: bool = True):
        """Draw a preview of the area and add measurement points."""
        log.debug("Draw preview", extra={"tag": "job_submission"})

        preview_area_wildcard = os.path.join(
            self.working_dir, self.preview_area_filename_template.format(position="*")
        )
        for file in glob.glob(preview_area_wildcard):
            file_name = os.path.basename(file)
            self.delete_item(file_name)

        # Transform area corners to lon/lat
        transformer = Transformer.from_crs(
            self.model.projection, "EPSG:4326", always_xy=True
        )

        lon1, lat1 = transformer.transform(self.model.area_x1, self.model.area_y1)
        lon2, lat2 = transformer.transform(self.model.area_x2, self.model.area_y2)
        min_lon, max_lon = min(lon1, lon2), max(lon1, lon2)
        min_lat, max_lat = min(lat1, lat2), max(lat1, lat2)

        types = []
        if self.model.train_data:
            types.append("train")
        if self.model.rover_data:
            types.append("rover")
        if self.model.station_data:
            types.append("station")

        # Get date range
        start_date, end_date = self.model.date_range

        filename = self.preview_area_filename_template.format(
            position=f"{min_lat}_{min_lon}_{max_lat}_{max_lon}_{'_'.join(types)}_{start_date}_{end_date}"  # noqa
        )
        file_path = os.path.join(self.working_dir, filename)
        # Prepare types list

        draw_preview(
            file_path,
            min_lon,
            min_lat,
            max_lon,
            max_lat,
            types,
            start_date,
            end_date,
        )
        self.save()
        return filename

    def get_preview_path(self):
        """Get the path to the preview image."""
        preview_area_wildcard = os.path.join(
            self.working_dir, self.preview_area_filename_template.format(position="*")
        )
        for file in glob.glob(preview_area_wildcard):
            return file
        return None

    def delete_input_files(self, input_type):
        """Delete input files from the working directory.

        This method removes all files in the working directory that match the specified
        input type.
        """
        log.debug(
            f"Delete input files of type {input_type}", extra={"tag": "job_submission"}
        )
        for file_name in os.listdir(self.working_dir):
            if file_name.startswith(input_type):
                self.delete_item(file_name)

    def prepare_input_files(self):
        """Prepare input files for the job.

        This method parses all input files once more but cut them to the area of the
        model.
        """
        log.debug("Prepare input files", extra={"tag": "job_submission"})
        crns_upload = {}
        predictors_upload = {}
        for file_name in os.listdir(self.working_dir):
            log.debug(f"File {file_name}", extra={"tag": "job_submission"})
            if file_name.startswith(f"{self.original_file_prefix}_crn_"):
                log.debug(f"Parse file {file_name}", extra={"tag": "job_submission"})
                file_path = os.path.join(self.working_dir, file_name)
                with open(file_path, "r") as file:
                    file_name, file_info = self.safe_input_file(
                        file_name, file, "crn", upload=False
                    )
                crns_upload[file_name] = file_info
            elif file_name.startswith(f"{self.original_file_prefix}_pred_"):
                log.debug(f"Parse file {file_name}", extra={"tag": "job_submission"})
                file_path = os.path.join(self.working_dir, file_name)
                with open(file_path, "r") as file:
                    file_name, file_info = self.safe_input_file(
                        file_name, file, "pred", upload=False
                    )
                predictors_upload[file_name] = file_info

        if any((self.model.train_data, self.model.rover_data, self.model.station_data)):
            log.debug(
                "Prepare CRNS data from database", extra={"tag": "job_submission"}
            )
            crns_info = self._write_crns()
            crns_upload["crns_data.csv"] = {
                "file_path": "crns_data.csv",
                "time_steps": crns_info["time_steps"],
                "num_data_points": crns_info["num_data_points"],
            }
            self.model.soil_moisture_data = "crns_data.csv"
        else:
            log.debug(crns_upload)
            self.model.crns_upload = crns_upload

        self.prepared_input = True
        self.model.predictor_upload = predictors_upload
        self.dump_parameters()
        self.save()

    def _write_crns(self):
        """Write CRNS data to CSV file."""
        log.debug("Write CRNS data to CSV file", extra={"tag": "job_submission"})
        # Bbox for PostGIS query
        transformer_to_wgs = Transformer.from_crs(
            self.model.projection, "EPSG:4326", always_xy=True
        )

        x1, y1, x2, y2 = (
            self.model.area_x1,
            self.model.area_y1,
            self.model.area_x2,
            self.model.area_y2,
        )

        lon1, lat1 = transformer_to_wgs.transform(x1, y1)
        lon2, lat2 = transformer_to_wgs.transform(x2, y2)
        min_lon, max_lon = min(lon1, lon2), max(lon1, lon2)
        min_lat, max_lat = min(lat1, lat2), max(lat1, lat2)
        bbox = (min_lon, min_lat, max_lon, max_lat)

        # Types of data to query
        types = []
        if self.model.train_data:
            types.append("train")
        if self.model.rover_data:
            types.append("rover")
        if self.model.station_data:
            types.append("station")

        start_date, end_date = self.model.date_range

        df = PostgresManager.get_measurement_points(
            bbox, types, start_date, end_date, representative=False
        )
        if df.empty:
            raise NoMeasurementPointsError

        # Transform coordinates to model projection
        transformer_to_proj = Transformer.from_crs(
            "EPSG:4326", self.model.projection, always_xy=True
        )
        xs, ys = transformer_to_proj.transform(
            df["longitude"].values, df["latitude"].values
        )
        df["x"] = xs
        df["y"] = ys

        df["time_step"] = df["date_time"].dt.strftime("%Y-%m-%d")

        out_df = df[["x", "y", "time_step", "soil_moisture", "error_low", "error_high"]]

        csv_path = os.path.join(self.working_dir, "crns_data.csv")

        out_df.to_csv(csv_path, index=False, float_format="%.4f")
        return {
            "time_steps": list(out_df["time_step"].unique()),
            "num_data_points": len(out_df),
        }

    def safe_input_file(self, file_name, file_content, input_type, upload: bool = True):
        """Check the content of the files and override data with file name and hash."""
        log.info(f"Safe input file {file_name}", extra={"tag": "job_submission"})
        if upload:
            # Set the geometry to infinity to not restrict the area
            geometry = RectGeom(
                xi=-float("inf"),
                xf=float("inf"),
                yi=-float("inf"),
                yf=float("inf"),
                resolution=0,
                build_grid=False,
            )
        else:
            # Set the geometry to the area of the model
            geometry = RectGeom(
                xi=self.model.area_x1,
                xf=self.model.area_x2,
                yi=self.model.area_y1,
                yf=self.model.area_y2,
                resolution=self.model.area_resolution,
                build_grid=False,
            )

        if input_type == "crn":
            parser = SoilMoistureParser(geometry)
        elif input_type == "pred":
            parser = PredictorParser(geometry)
        else:
            raise ValueError(f"Invalid input type: {input_type}")

        base_file_name = secure_filename(file_name)
        prefixes = [
            "crn_",
            f"{self.original_file_prefix}_crn_",
            "pred_",
            f"{self.original_file_prefix}_pred_",
        ]
        for prefix in prefixes:
            if base_file_name.startswith(prefix):
                base_file_name = base_file_name[len(prefix) :]  # noqa
        base_file_name = f"{input_type}_{base_file_name}"

        if upload:
            new_filename = f"{self.original_file_prefix}_{base_file_name}"
        else:
            new_filename = base_file_name

        if upload:
            try:
                if "," not in file_content:
                    raise ValueError("Missing comma in data URL")
                base64_str = file_content.split(",")[1]
                decoded_bytes = base64.b64decode(base64_str)
                decoded_text = decoded_bytes.decode("utf-8")
                file_content = io.StringIO(decoded_text)
            except (ValueError, binascii.Error, UnicodeDecodeError) as e:
                raise FileValidationError(f"Invalid file content: {e}")

        input_file_path = os.path.join(self.working_dir, new_filename)

        # Parse file and write to input dir.
        try:
            with open(input_file_path, "w") as file:
                for row in parser.parse(file_content):
                    if row[0] == "#":
                        file.write(row + "\n")
                    else:
                        file.write(
                            ",".join([str(e) for e in row if e is not None]) + "\n"
                        )
        except FileValidationError:
            self.delete_item(new_filename)
            raise

        file_information = parser.get_file_information()
        if input_type == "pred":
            file_information["file_path"] = base_file_name
        self.save()
        return base_file_name, file_information

    def _get_column_data(self, name):
        if name == "logs":
            log_file = os.path.join(self.working_dir, LOG_FILE_NAME)
            try:
                with open(log_file, "r") as f_handle:
                    content = f_handle.read()
                    # PostgreSQL text fields cannot contain NUL (0x00) bytes
                    return content.replace("\x00", "")
            # Catch error log file can be deleted by other process (change input from
            # submission page)
            except FileNotFoundError:
                return ""

        if name == "input_data":
            return self.model.model_dump_json(
                indent=4,
                exclude_unset=False,
                exclude_none=True,
                exclude_defaults=False,
            )

        return getattr(self, name)

    def reload_logs(self):
        """Reload the logs from the log file."""
        self.logs = self._get_column_data("logs")

    def save_attributes(self, attribute_list):
        """Save specicif job information to the database.

        This method takes a list of attributes, collects the current information of
        these attributes. It then uses a PostgresManager instance to add the collected
        data as to the respective column in the database.
        If the job can not be found in data base safe all attributes.
        """
        log.debug(
            f"Save attributes {', '.join(attribute_list)} to job {self.job_id}",
            extra={"tag": "job_submission"},
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
        log.debug(f"Save job {self.job_id}", extra={"tag": "job_submission"})
        # Save files first. Can lead to race conditions between worker and web app.
        save_files(self.job_id)
        column_names = JobTable.__table__.columns.keys()
        data_to_insert = {name: self._get_column_data(name) for name in column_names}
        for key, value in data_to_insert.items():
            # Try to load json data into model -> assures that only vaild data is saved
            if key == "input_data":
                ModelWebsite(**json.loads(value))
        PostgresManager.add_entry(data_to_insert)

    def delete(self, delete_work_dir=True, delete_db=True):
        """
        Delete the job in the data base.

        This method uses a PostgresManager instance to delete the job entry from
        the database based on the job's unique identifier ('job_id').
        """
        log.debug(f"Delete job {self.job_id}", extra={"tag": "job_submission"})
        if delete_work_dir:
            shutil.rmtree(self.working_dir)
        if delete_db:
            PostgresManager.delete_job(self.job_id)
            delete_directory_from_storage(self.job_id)

    def _log_to_file(self, message):
        """Write message directly to job log file.

        Used for logging errors that occur before background worker starts.
        """
        log_file = os.path.join(self.working_dir, LOG_FILE_NAME)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, "a") as f:
            f.write(f"[{timestamp}] {message}\n")

    def submit(self):
        """Submit job to Celery queue for background processing."""
        log.info(f"Submit job {self.job_id}.", extra={"tag": "job_submission"})

        if PostgresManager.set_submitted(self.job_id):
            self.submitted = True
            try:
                celery_task_id, failed = background_job_manager.submit_computation_job(
                    self
                )

            except (
                Exception
            ) as e:  # catch-all: submission can fail for many reasons; must report all  # noqa
                if "Error -3 connecting to redis" in str(e):
                    message = "Redis server is not running"
                    email_body = f"""
                    Redis server is not running.\n\n
                    Error: {str(e)}\n\n
                    Traceback info: {traceback.format_exc()}\n\n
                    """
                else:
                    message = f"{repr(e)}\n\n{traceback.format_exc()}"
                    email_body = f"""
                    Error: {str(e)}\n\n
                    Traceback info: {traceback.format_exc()}\n\n
                    """

                log.error(
                    f"Job {self.job_id} failed to start.\n{message}",
                    extra={"tag": "job_submission"},
                )

                # Write generic error message to job log file
                self._log_to_file("ERROR: Cannot start job")

                email_subject = f"Failed to start job {self.job_id}"
                email_body = f"""
                Error: {str(e)}\n\n
                Traceback info: {traceback.format_exc()}\n\n
                """

                send_mail(MAINTAINER_EMAIL, email_subject, email_body)
                failed = True
                celery_task_id = None
        else:
            log.debug(
                f"Job {self.job_id} was already submitted.",
                extra={"tag": "job_submission"},
            )
            return

        if failed:
            self.celery_task_id = celery_task_id
        if failed:
            self.status = "FAILED"
        else:
            self.status = "RUNNING"

        self.save()

    def time_to_life(self):
        """Return the number of days after which this job will be deleted."""
        days_passed = (date.today() - self.start_date).days
        if self.submitted:
            return DAYS_DELETE_SUMBITTED - days_passed
        else:
            return DAYS_DELETE_NOT_SUMBITTED - days_passed

    def status_color(self):
        """Return the color of the job status."""
        if self.status == "PENDING":
            return "bg-info"
        elif self.status == "RUNNING":
            return "bg-secondary"
        elif self.status == "COMPLETED":
            return "bg-success"
        elif self.status == "FAILED":
            return "bg-danger"
        else:
            return "bg-secondary"

    def copy_input_files(self, parent_work_dir):
        """Copy input files of the parent job to the working directory of the job."""
        log.info(
            f"Copy input files from parent for job {self.job_id}.",
            extra={"tag": "job_submission"},
        )
        for file in os.listdir(parent_work_dir):
            if file.startswith(self.original_file_prefix):
                source_path = os.path.join(parent_work_dir, file)
                target_path = os.path.join(self.working_dir, file)
                shutil.copy(source_path, target_path)

    def spawn(self) -> Self:
        """Clone the job."""
        log.info(f"Spawn job {self.job_id}.", extra={"tag": "job_submission"})
        new_model = deepcopy(self.model)
        i = 1
        while True:
            new_model.job_id = f"{self.job_id}_child_{i}"
            if not PostgresManager.check_existence(new_model.job_id):
                break
            i += 1

        new_job = Job(model=new_model)
        new_job.copy_input_files(self.working_dir)
        new_job.save()
        return new_job

    def clean_work_dir(self):
        """Clean the working directory."""
        log.info(f"Clean work dir {self.working_dir}", extra={"tag": "job_submission"})

        for file in os.listdir(self.working_dir):
            if file.startswith(self.original_file_prefix):
                continue

            self.delete_item(file)

        self.preview_area()
        self.dump_parameters()

        self.save()

    def delete_logs(self):
        """Delete the logs."""
        log.info(f"Delete logs of job {self.job_id}", extra={"tag": "job_submission"})
        self.delete_item(LOG_FILE_NAME)
