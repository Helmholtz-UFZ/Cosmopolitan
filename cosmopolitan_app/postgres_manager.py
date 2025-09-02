"""Module for interaction between webservice and data base."""

import logging
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from geoalchemy2 import Geometry
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.sql import func

from cosmopolitan_app.config import (
    POSTGRES_DB,
    POSTGRES_HOST_NAME,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)


class Base(DeclarativeBase):
    """Base class for declarative base."""

    pass


class JobNotFound(Exception):
    """Custom exception for when a job is not found."""

    def __init__(self, job_id):
        """Add job id as attribute and format error message."""
        self.job_id = job_id
        super().__init__(f"Job with ID '{job_id}' not found")


class SessionScope:
    """Context manager for managing database sessions with retry logic."""

    def __init__(self, session_factory):
        """Initialize the session scope with a session factory."""
        self.session_factory = session_factory
        self.max_retries = 3
        self.retry_delay = 1
        self.session = None

    def __enter__(self):
        """Create a new session and handle retries for database operations."""
        for attempt in range(self.max_retries + 1):
            try:
                self.session = self.session_factory()
                return self.session  # success
            except OperationalError as e:
                if attempt < self.max_retries:
                    logging.warning(
                        f"Database OperationalError: {e}", extra={"tag": "database"}
                    )
                    logging.warning(
                        f"Retrying operation (attempt {attempt + 1}/{self.max_retries + 1})",  # noqa
                        extra={"tag": "database"},
                    )
                    time.sleep(self.retry_delay)
                else:
                    logging.error(
                        f"Max retries ({self.max_retries}) exceeded",
                        extra={"tag": "database"},
                    )
                    raise
            except SQLAlchemyError as e:
                logging.error(f"Database error: {e}", extra={"tag": "database"})
                raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Commit or rollback the session based on exception type."""
        try:
            if exc_type is None:
                self.session.commit()
            else:
                self.session.rollback()
        finally:
            self.session.close()

        # False means exceptions are re-raised outside the `with`
        return False


class PostgresManager:
    """Class for interacting with the posgres database."""

    database_url = (
        f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
        f"{POSTGRES_HOST_NAME}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
    )
    Session = sessionmaker(bind=engine)

    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1

    @classmethod
    def session_scope(cls, max_retries=None, retry_delay=None):
        """Provide a transactional scope around a series of operations."""
        return SessionScope(session_factory=cls.Session)

    @classmethod
    def query_logs(
        cls,
        date: str,
        sh: int,
        sm: int,
        eh: int,
        em: int,
        levels: List[str],
        pid: Optional[int] = None,
        tag: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Query logs from the database with specified filters.

        This method supports filtering by the tag-based logging system that categorizes
        logs by functional area (e.g., 'database', 'time_io', 'job_submission').

        Parameters:
        -----------
        date : str
            Date in the format 'YYYY-MM-DD'
        sh : int
            Start hour (0-23)
        sm : int
            Start minute (0-59)
        eh : int
            End hour (0-23)
        em : int
            End minute (0-59)
        levels : list
            List of log levels to include (e.g., ['INFO', 'ERROR'])
        pid : int, optional
            Process ID to filter logs by
        tag : list, optional
            List of tags to filter logs by using the tag-based logging system.
            Use None to get logs from all tags.

        Returns:
        --------
        list
            List of dictionaries containing log records
        """
        logging.debug(
            f"Querying logs from {date} {sh}:{sm} to {date} {eh}:{em}",
            extra={"tag": "database"},
        )

        start_datetime = datetime.strptime(
            f"{date} {sh:02d}:{sm:02d}:00", "%Y-%m-%d %H:%M:%S"
        )
        end_datetime = datetime.strptime(
            f"{date} {eh:02d}:{em:02d}:59", "%Y-%m-%d %H:%M:%S"
        )

        with cls.session_scope() as session:
            query = session.query(LogTable).filter(
                LogTable.timestamp >= start_datetime,
                LogTable.timestamp <= end_datetime,
                LogTable.level.in_(levels),
            )

            if pid is not None:
                query = query.filter(LogTable.pid == pid)

            if tag is not None:
                query = query.filter(LogTable.tag.in_(tag))

            # Order results by timestamp
            query = query.order_by(LogTable.timestamp)

            # Execute query and convert results to dictionaries
            logs = [log.to_dict() for log in query.all()]

        return logs

    @classmethod
    def delete_logs_older_than(cls, cutoff_datetime):
        """Delete all log records older than the given datetime."""
        logging.info(
            f"Deleting logs older than {cutoff_datetime}", extra={"tag": "database"}
        )
        with cls.session_scope() as session:
            session.query(LogTable).filter(LogTable.timestamp < cutoff_datetime).delete(
                synchronize_session=False
            )

    @classmethod
    def check_existence(cls, job_id):
        """Check if a job with the given job ID exists in the database.

        This method queries the 'jobs' table in the database to determine
        whether a job with the provided job ID exists.

        Parameters:
        job_id (str): The unique identifier for the job.

        Returns:
        bool: True if a job with the given job ID exists, False otherwise.
        """
        logging.debug(f"Check existence of job: {job_id}", extra={"tag": "database"})
        with cls.session_scope() as session:
            job_row = session.query(JobTable.job_id).filter_by(job_id=job_id).first()
        return job_row is not None

    @classmethod
    def add_entry(cls, data_to_insert):
        """Add or update a job entry in the database.

        This method takes a dictionary containing job information and

        Parameters:
        data_to_insert (dict): A dictionary containing job information with keys
        equivalent to the columns in JobTable.
        """
        logging.debug(
            f"Add entry to database: {data_to_insert['job_id']}",
            extra={"tag": "database"},
        )
        with cls.session_scope() as session:
            # Check existence within this session
            job_row = (
                session.query(JobTable.job_id)
                .filter_by(job_id=data_to_insert["job_id"])
                .first()
            )

            if job_row is not None:
                # Update existing entry
                logging.debug("Update entry.", extra={"tag": "database"})
                job = (
                    session.query(JobTable)
                    .filter_by(job_id=data_to_insert["job_id"])
                    .first()
                )
                for column_name, column_value in data_to_insert.items():
                    setattr(job, column_name, column_value)
            else:
                # Create new entry
                logging.debug("New entry.", extra={"tag": "database"})
                job_row = JobTable(**data_to_insert)
                session.add(job_row)

    @classmethod
    def update_column(cls, job_id, column_dic):
        """Update specific columns in the 'JobTable' for a given job ID.

        Parameters:
        job_id (str): The unique identifier for the job.
        column_dic (dict): Dictionary of column names and values to update.

        Raises:
        JobNotFound: If the job with the provided job ID does not exist.
        """
        logging.debug(f"Update columns for job: {job_id}", extra={"tag": "database"})

        with cls.session_scope() as session:
            job = session.query(JobTable).filter_by(job_id=job_id).first()
            if job is None:
                raise JobNotFound(job_id)

            for column_name, column_value in column_dic.items():
                setattr(job, column_name, column_value)

    @classmethod
    def set_submitted(cls, job_id):
        """Update the 'submitted' column in the 'JobTable' for a given job ID.

        The method works as well as a lock so that the job is not submitted twice.

        Parameters:
        job_id (str): The unique identifier for the job.

        Returns:
        bool: True if the job was successfully marked as submitted, False if it was
        already submitted.

        Raises:
        JobNotFound: If the job with the provided job ID does not exist.
        """
        logging.debug(f"Set submitted for job: {job_id}", extra={"tag": "database"})

        with cls.session_scope() as session:
            job = (
                session.query(JobTable)
                .filter_by(job_id=job_id)
                .with_for_update()
                .first()
            )
            if job is None:
                raise JobNotFound(job_id)

            if job.submitted and job.status in ["RUNNING", "COMPLETED"]:
                return False
            else:
                job.submitted = True
                return True

    @classmethod
    def get_job_columns(cls, job_id):
        """Retrieve all columns of a specific job entry based on its job ID.

        This method queries the 'jobs' table in the database to retrieve all
        columns of the job entry associated with the provided job ID.

        Parameters:
        job_id (str): The unique identifier for the job.

        Returns:
        dict: A dictionary containing all columns and their values for the
        specified job.

        Raises:
        JobNotFound: If the job with the provided job ID does not exist.
        """
        logging.debug(f"Get columns for job: {job_id}", extra={"tag": "database"})

        with cls.session_scope() as session:
            job_row = session.query(JobTable).filter_by(job_id=job_id).first()

            if job_row is None:
                raise JobNotFound(job_id)

            # Convert all columns to a dictionary
            job_columns = {
                column.name: getattr(job_row, column.name)
                for column in JobTable.__table__.columns
            }

        return job_columns

    @classmethod
    def delete_job(cls, job_id):
        """Delete a job entry from the database based on its job ID.

        This method deletes a job entry from the 'jobs' table in the database
        based on the provided job ID.

        Parameters:
        job_id (str): The unique identifier for the job to be deleted.

        Raises:
        JobNotFound: If the job with the provided job ID does not exist.
        """
        logging.debug(f"Delete job: {job_id}", extra={"tag": "database"})
        with cls.session_scope() as session:
            job = session.query(JobTable).filter_by(job_id=job_id).first()

            if job is None:
                raise JobNotFound(job_id)

            session.delete(job)

    @classmethod
    def list_jobs(cls):
        """List all jobs in the database with their submission date and status.

        This method retrieves all job entries from the 'jobs' table in the
        database and returns a dictionary where the keys are 'job_id', and the
        values are dictionaries containing all columns of the job entry.

        Returns:
        dict: A dictionary where keys are 'job_id' and values are dictionaries of
        all columns of the job entry.

        Example:
        {
        'job1': ('2023-09-01', True),
        'job2': ('2023-09-02', False),
        # ...
        }

        """
        logging.debug("List all jobs.", extra={"tag": "database"})

        with cls.session_scope() as session:
            job_rows = session.query(JobTable).all()

            job_info = {}
            for job_row in job_rows:
                job_info[job_row.job_id] = {
                    "start_date": job_row.start_date,
                    "input_data": job_row.input_data,
                    "status": job_row.status,
                    "submitted": job_row.submitted,
                    "notified_end": job_row.notified_end,
                    "logs": job_row.logs,
                    "version": job_row.version,
                }
        return job_info

    @classmethod
    def _extract_date(cls, date_input: Union[date, datetime]) -> date:
        """Extract date from datetime or date object."""
        if isinstance(date_input, datetime):
            return date_input.date()
        return date_input

    @classmethod
    def last_update_crns(cls):
        """Get the last update date for CRNS measurements.

        This method retrieves the last update date for CRNS measurements
        from the 'update_times_crns' table in the database.

        Returns:
        date: The last update date for CRNS measurements.
        """
        logging.debug(
            "Get last update date for CRNS measurements", extra={"tag": "database"}
        )

        with cls.session_scope() as session:
            update = session.query(UpdateTimesCRNS).order_by(
                UpdateTimesCRNS.update.desc()
            )
            for last_update in update:
                if last_update.successful:
                    break
            else:
                return None

            if last_update:
                return last_update.update
            else:
                return None

    @classmethod
    def get_earliest_missing_or_failed_date(cls, start_date: Union[date, datetime]):
        """Get the earliest missing or failed date for CRNS measurements.

        This method analyzes CRNS measurement update times and returns:
        - Start date if the table is empty
        - The earliest unsuccessful date if any exist
        - The earliest missing date if there are gaps in the sequence
        - The next expected date if all dates from start are successful
        - The start_date if the first entry is after start_date

        Args:
            start_date (date or datetime): The starting date for analysis

        Returns:
            date or None: The appropriate date based on the analysis logic
        """
        logging.debug(
            "Get earliest missing or failed date for CRNS measurements",
            extra={"tag": "database"},
        )

        # Convert to date if datetime
        start_date = cls._extract_date(start_date)

        with cls.session_scope() as session:
            # Check if table is empty
            total_count = session.query(UpdateTimesCRNS).count()
            if total_count == 0:
                return start_date

            # Get the earliest date in the database
            earliest_entry = (
                session.query(UpdateTimesCRNS)
                .order_by(UpdateTimesCRNS.update.asc())
                .first()
            )

            # If first entry is after start_date, return start_date
            if earliest_entry.update > start_date:
                return start_date

            # Get all entries from start_date onwards, ordered by date
            all_updates = (
                session.query(UpdateTimesCRNS)
                .filter(UpdateTimesCRNS.update >= start_date)
                .order_by(UpdateTimesCRNS.update.asc())
                .all()
            )

            if not all_updates:
                return start_date

            # Find the earliest unsuccessful date
            earliest_unsuccessful = None
            for update in all_updates:
                if not update.successful:
                    earliest_unsuccessful = update.update
                    break

            # Find the earliest gap (missing date)
            current_date = start_date
            update_dates = {update.update for update in all_updates}
            earliest_gap = None

            while current_date <= max(update_dates):
                if current_date not in update_dates:
                    earliest_gap = current_date
                    break
                current_date += timedelta(days=1)

            # If no gap found within existing range, the gap is the next day after the
            # last entry
            if earliest_gap is None:
                last_date = max(update_dates)
                earliest_gap = last_date + timedelta(days=1)

            # Return whichever is earlier: gap or unsuccessful date
            if earliest_unsuccessful is None:
                return earliest_gap
            elif earliest_gap is None:
                return earliest_unsuccessful
            else:
                return min(earliest_gap, earliest_unsuccessful)

    @classmethod
    def add_update_crns(cls, day: Union[date, datetime], successful: bool = True):
        """Add or update a new update date for CRNS measurements.

        Args:
            day: The date (as date or datetime object) to add/update
            successful: Whether the update was successful
        """
        # Convert to date if datetime
        update_date = cls._extract_date(day)

        logging.debug(
            f"Add new update date for CRNS measurements: {update_date}",
            extra={"tag": "database"},
        )

        with cls.session_scope() as session:
            existing = (
                session.query(UpdateTimesCRNS).filter_by(update=update_date).first()
            )
            if existing:
                existing.successful = successful
            else:
                new_update = UpdateTimesCRNS(update=update_date, successful=successful)
                session.add(new_update)

    @classmethod
    def was_update_successful(cls, day: Union[date, datetime]) -> bool:
        """Check if the update for CRNS measurements was successful.

        This method checks if the update for CRNS measurements on a specific
        date was successful by querying the 'update_times_crns' table in the
        database.

        Parameters:
        day (date or datetime): The date of the update.

        Returns:
        bool: True if the update was successful, False otherwise.
        """
        # Convert to date if datetime
        check_date = cls._extract_date(day)

        logging.debug(
            f"Check if update on {check_date} was successful", extra={"tag": "database"}
        )

        with cls.session_scope() as session:
            update = session.query(UpdateTimesCRNS).filter_by(update=check_date).first()
            return update.successful if update else False

    @classmethod
    def reset_update_crns(cls):
        """Reset all update dates for CRNS measurements."""
        logging.info(
            "Reset all update dates for CRNS measurements", extra={"tag": "database"}
        )

        with cls.session_scope() as session:
            session.query(UpdateTimesCRNS).delete(synchronize_session=False)
            logging.info(
                "All CRNS update dates have been reset", extra={"tag": "database"}
            )

    @classmethod
    def insert_crns_measurements_from_df(cls, df):
        """Insert or update CRNS measurements from a DataFrame into the database.

        Args:
            df: DataFrame with all CRNSMeasurement columns except 'geom'.
                latitude and longitude cannot be None/null.

        Raises:
            ValueError: If required columns are missing or lat/lon contain null values.
        """
        logging.debug(
            "Insert or update CRNS measurements from DataFrame",
            extra={"tag": "database"},
        )

        # Get all table columns except geom
        table = CRNSMeasurement.__table__
        required_columns = {c.name for c in table.columns if c.name != "geom"}
        df_columns = set(df.columns)

        # Check for missing columns
        missing_columns = required_columns - df_columns
        if missing_columns:
            raise ValueError(
                f"DataFrame is missing required columns: {missing_columns}"
            )

        # Check for extra columns (optional validation)
        extra_columns = df_columns - required_columns
        if extra_columns:
            logging.warning(
                f"DataFrame contains extra columns that will be ignored: {extra_columns}",  # noqa: E501
                extra={"tag": "database"},
            )
            # Keep only required columns
            df = df[list(required_columns)]

        df = df.dropna()

        if df.empty:
            logging.warning(
                "DataFrame is empty after dropping null values.",
                extra={"tag": "database"},
            )
            return

        # Create geometry column from lat/lon
        df = df.copy()  # Avoid modifying the original DataFrame
        df["geom"] = df.apply(
            lambda row: f"POINT({row['longitude']} {row['latitude']})", axis=1
        )

        # Insert/update records
        records = df.to_dict(orient="records")
        stmt = insert(table).values(records)
        update_cols = {
            c.name: getattr(stmt.excluded, c.name)
            for c in table.columns
            if c.name not in ("date_time", "sensor_id")
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["date_time", "sensor_id"], set_=update_cols
        )

        with cls.session_scope() as session:
            session.execute(stmt)
            logging.debug(
                f"Successfully inserted/updated {len(records)} CRNS measurements",
                extra={"tag": "database"},
            )

    @classmethod
    def get_measurement_points(cls, bbox, types, start_date, end_date, representative):
        """Retrieve measurement points."""
        logging.debug(
            f"Get measurement points for types: {types} in bbox: {bbox} and date range: {start_date} to {end_date}",  # noqa: E501
            extra={"tag": "database"},
        )
        # Get type mapping from database
        type_id_dict = cls.get_timeio_type_mapping()
        sensor_ids = [id for id, t in type_id_dict.items() if t in types]
        min_lon, min_lat, max_lon, max_lat = bbox
        with cls.session_scope() as session:
            columns = [
                CRNSMeasurement.date_time,
                CRNSMeasurement.sensor_id,
                CRNSMeasurement.soil_moisture,
                CRNSMeasurement.error_high,
                CRNSMeasurement.error_low,
                CRNSMeasurement.latitude,
                CRNSMeasurement.longitude,
                CRNSMeasurement.sensor_name,
                CRNSMeasurement.representative,
            ]
            query = session.query(*columns).filter(
                CRNSMeasurement.sensor_id.in_(sensor_ids),
                CRNSMeasurement.date_time >= start_date,
                CRNSMeasurement.date_time <= end_date,
                func.ST_Within(
                    CRNSMeasurement.geom,
                    func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326),
                ),
            )

            if representative:
                query = query.filter(CRNSMeasurement.representative)

            col_names = [col.key for col in columns]
            data = [dict(zip(col_names, row)) for row in query.all()]

        logging.debug(
            f"Retrieved {len(data)} measurement points", extra={"tag": "database"}
        )
        df = pd.DataFrame(data).dropna()
        logging.debug(
            f"Returning {len(df)} measurement points after dropping NaNs",
            extra={"tag": "database"},
        )
        return df

    @classmethod
    def rebuild_geo_index(cls):
        """Rebuild the spatial index on the geometry column.

        This method drops and recreates the spatial index on the geom column
        to optimize geo queries and resolve any index corruption issues.

        Raises:
            Exception: If there's an error during index operations.
        """
        logging.info(
            "Rebuilding spatial index on crns_measurements.geom",
            extra={"tag": "database"},
        )

        with cls.session_scope() as session:
            # Drop the existing spatial index if it exists
            drop_index_sql = """
                DROP INDEX IF EXISTS idx_crns_measurements_geom;
            """

            # Recreate the spatial index
            create_index_sql = """
                CREATE INDEX idx_crns_measurements_geom
                ON crns_measurements
                USING GIST (geom);
            """

            # Execute the SQL commands
            session.execute(text(drop_index_sql))
            logging.debug("Dropped existing spatial index", extra={"tag": "database"})

            session.execute(text(create_index_sql))
            logging.debug("Created new spatial index", extra={"tag": "database"})

            # Commit the transaction
            session.commit()

            logging.info(
                "Successfully rebuilt spatial index on crns_measurements.geom",
                extra={"tag": "database"},
            )

    @classmethod
    def purge_measurement_points(cls, sensor_ids=None):
        """Purge measurement points from the database.

        If sensor_ids is provided, only those sensors will be purged.
        Otherwise, all measurement points will be deleted.

        Parameters:
        sensor_ids (list): List of sensor IDs to purge. If None, all sensors are purged.
        """
        logging.info(
            f"Purging measurement points for sensors: {sensor_ids}",
            extra={"tag": "database"},
        )

        with cls.session_scope() as session:
            if sensor_ids is not None:
                session.query(CRNSMeasurement).filter(
                    CRNSMeasurement.sensor_id.in_(sensor_ids)
                ).delete(synchronize_session=False)
            else:
                session.query(CRNSMeasurement).delete(synchronize_session=False)

            logging.info(
                "Measurement points purged successfully", extra={"tag": "database"}
            )

    @classmethod
    def get_timeio_type_mapping(cls) -> Dict[int, str]:
        """Get sensor_id to sensor_type mapping for active sensors.

        Returns:
            dict: {sensor_id: sensor_type} for active sensors
        """
        logging.debug(
            "Getting TimeIO type mapping from database", extra={"tag": "database"}
        )

        with cls.session_scope() as session:
            sensors = (
                session.query(TimeIOInfo.sensor_id, TimeIOInfo.sensor_type)
                .filter(~TimeIOInfo.ignored)
                .all()
            )

            return {sensor.sensor_id: sensor.sensor_type for sensor in sensors}

    @classmethod
    def get_timeio_datastream_mapping(cls) -> Dict[int, Dict[str, str]]:
        """Get sensor_id to datastream mapping for active sensors.

        Returns:
            dict: {sensor_id: {datastream_id: datastream_name}} for active sensors
        """
        logging.debug(
            "Getting TimeIO datastream mapping from database", extra={"tag": "database"}
        )

        with cls.session_scope() as session:
            sensors = (
                session.query(TimeIOInfo.sensor_id, TimeIOInfo.datastreams)
                .filter(~TimeIOInfo.ignored)
                .all()
            )

            result = {}
            for sensor in sensors:
                # Convert string keys to integers for datastream_ids
                datastreams = {}
                for ds_id, ds_name in sensor.datastreams.items():
                    datastreams[int(ds_id)] = ds_name
                result[sensor.sensor_id] = datastreams

            return result

    @classmethod
    def get_timeio_name_mapping(cls) -> Dict[int, str]:
        """Get sensor_id to sensor_name mapping for active sensors.

        Returns:
            dict: {sensor_id: sensor_name} for active sensors
        """
        logging.debug(
            "Getting TimeIO name mapping from database", extra={"tag": "database"}
        )

        with cls.session_scope() as session:
            sensors = (
                session.query(TimeIOInfo.sensor_id, TimeIOInfo.sensor_name)
                .filter(~TimeIOInfo.ignored)
                .all()
            )

            return {sensor.sensor_id: sensor.sensor_name for sensor in sensors}

    @classmethod
    def get_ignored_sensor_ids(cls) -> list[int]:
        """Get list of ignored sensor IDs (replaces ignore_things).

        Returns:
            list: List of sensor_ids where ignored=True
        """
        logging.debug(
            "Getting ignored sensor IDs from database", extra={"tag": "database"}
        )

        with cls.session_scope() as session:
            sensors = (
                session.query(TimeIOInfo.sensor_id).filter(TimeIOInfo.ignored).all()
            )

            return [sensor.sensor_id for sensor in sensors]

    @classmethod
    def get_timeio_sensor_info(cls, sensor_id: int) -> Dict[str, Any]:
        """Get complete information for a specific sensor.

        Args:
            sensor_id: The sensor ID to retrieve

        Returns:
            dict: Complete sensor information or None if not found
        """
        logging.debug(
            f"Getting TimeIO sensor info for sensor_id: {sensor_id}",
            extra={"tag": "database"},
        )

        with cls.session_scope() as session:
            sensor = (
                session.query(TimeIOInfo)
                .filter(TimeIOInfo.sensor_id == sensor_id)
                .first()
            )

            if not sensor:
                return None

            return {
                "sensor_id": sensor.sensor_id,
                "sensor_name": sensor.sensor_name,
                "sensor_type": sensor.sensor_type,
                "ignored": sensor.ignored,
                "datastreams": sensor.datastreams,
                "stationary": sensor.stationary,
            }

    @classmethod
    def get_all_timeio_sensors(
        cls, not_ignored_only: bool = True
    ) -> list[Dict[str, Any]]:
        """Get all sensor information.

        Args:
            not_ignored_only: If True, only return non-ignored sensors

        Returns:
            list: List of sensor information dictionaries
        """
        logging.debug(
            f"Getting all TimeIO sensors (not_ignored_only={not_ignored_only})",
            extra={"tag": "database"},
        )

        with cls.session_scope() as session:
            query = session.query(TimeIOInfo)
            if not_ignored_only:
                query = query.filter(~TimeIOInfo.ignored)

            sensors = query.order_by(TimeIOInfo.sensor_id).all()

            return [
                {
                    "sensor_id": sensor.sensor_id,
                    "sensor_name": sensor.sensor_name,
                    "sensor_type": sensor.sensor_type,
                    "ignored": sensor.ignored,
                    "datastreams": sensor.datastreams,
                    "stationary": sensor.stationary,
                }
                for sensor in sensors
            ]

    @classmethod
    def add_timeio_sensor(cls, sensor_data: Dict[str, Any]) -> None:
        """Add or update a TimeIO sensor in the database.

        Args:
            sensor_data: Dictionary containing sensor information

        Returns:
            bool: True if sensor was added/updated successfully, False otherwise
        """
        sensor_id = sensor_data["sensor_id"]
        logging.debug(
            f"Adding/updating TimeIO sensor: {sensor_id}", extra={"tag": "database"}
        )

        with cls.session_scope() as session:
            # Check if sensor already exists
            existing_sensor = (
                session.query(TimeIOInfo)
                .filter(TimeIOInfo.sensor_id == sensor_id)
                .first()
            )

            if existing_sensor:
                # Update existing sensor
                logging.debug(
                    f"Updating existing sensor {sensor_id}", extra={"tag": "database"}
                )
                for key, value in sensor_data.items():
                    if key != "stationary":  # Skip computed column
                        setattr(existing_sensor, key, value)
            else:
                # Add new sensor
                logging.debug(
                    f"Adding new sensor {sensor_id}", extra={"tag": "database"}
                )
                new_sensor = TimeIOInfo(**sensor_data)
                session.add(new_sensor)


class TaskLockTable(Base):
    """Represents the 'task_lock' table in the database."""

    __tablename__ = "task_lock"

    task_type = Column(String, primary_key=True)
    is_locked = Column("is_locked", Boolean)


class JobTable(Base):
    """Represents the 'jobs' table in the database."""

    __tablename__ = "jobs"

    job_id = Column(String, primary_key=True)
    start_date = Column("start_date", Date)
    input_data = Column("input_data", JSON)
    submitted = Column("submitted", Boolean)
    notified_end = Column("notified_end", Boolean)
    logs = Column("logs", String)
    status = Column("status", String)
    version = Column("version", String)


class LogTable(Base):
    """SQLAlchemy model for the logs table."""

    __tablename__ = "logs"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=False), nullable=False)
    pid = Column(Integer, nullable=False)
    level = Column(String(10), nullable=False)
    module = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    tag = Column(String(20), nullable=False, default="unknown")

    def to_dict(self) -> Dict[str, Any]:
        """Convert log record to dictionary format."""
        return {
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "pid": self.pid,
            "level": self.level,
            "message": self.message,
            "module": self.module,
            "tag": self.tag,
        }


class UpdateTimesCRNS(Base):
    """Represents the 'update_times_crns' table in the database."""

    __tablename__ = "update_times_crns"

    update = Column(Date, primary_key=True, nullable=False)
    successful = Column(Boolean, nullable=False)


class TimeIOInfo(Base):
    """Represents the 'timeio_info' table in the database."""

    __tablename__ = "timeio_info"

    sensor_id = Column(Integer, primary_key=True)
    sensor_name = Column(String(255), nullable=False)
    sensor_type = Column(String(50), nullable=False)
    ignored = Column(Boolean, default=False)
    datastreams = Column(JSON, nullable=False)
    stationary = Column(
        Boolean, server_default=text("NULL"), insert_default=None
    )  # Database computed column


class CRNSMeasurement(Base):
    """Represents the 'crns_measurements' table in the database."""

    __tablename__ = "crns_measurements"
    date_time = Column(DateTime, primary_key=True)
    sensor_id = Column(Integer, primary_key=True)
    soil_moisture = Column(Float)
    error_high = Column(Float)
    error_low = Column(Float)
    latitude = Column(Float)
    longitude = Column(Float)
    geom = Column(Geometry("POINT", srid=4326))
    sensor_name = Column(String(255))
    representative = Column(Boolean)

    @classmethod
    def create_point(cls, longitude, latitude):
        """Create a WKT string for PostGIS geometry column."""
        return from_shape(Point(longitude, latitude))


if __name__ == "__main__":
    PostgresManager.check_existence("test_job")
