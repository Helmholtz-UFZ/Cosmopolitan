"""Module for interaction between webservice and data base."""

import logging
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict

from geoalchemy2 import Geometry
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
)
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from cosmopolitan_app.config import (
    POSTGRES_DB,
    POSTGRES_HOST_NAME,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)

# Number of retries for database operations
max_retries = 3


class Base(DeclarativeBase):
    """Base class for declarative base."""

    pass


class JobNotFound(Exception):
    """Custom exception for when a job is not found."""

    def __init__(self, job_id):
        """Add job id as attribute and format error message."""
        self.job_id = job_id
        super().__init__(f"Job with ID '{job_id}' not found")


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
    @contextmanager
    def session_scope(cls, max_retries=None, retry_delay=None):
        """Context manager for database sessions with retry logic.

        Provides a transactional scope around a series of operations.
        Automatically handles commits, rollbacks, and session closing.
        Includes retry logic for transient database errors.

        Parameters:
        -----------
        max_retries : int, optional
            Maximum number of retry attempts for transient errors
        retry_delay : int, optional
            Delay in seconds between retry attempts

        Yields:
        -------
        session : Session
            SQLAlchemy session object
        """
        # Use default values if not specified
        max_retries = (
            max_retries if max_retries is not None else cls.DEFAULT_MAX_RETRIES
        )
        retry_delay = (
            retry_delay if retry_delay is not None else cls.DEFAULT_RETRY_DELAY
        )

        attempt = 0

        while True:
            session = cls.Session()
            try:
                yield session
                session.commit()
                # Success - exit the retry loop
                return
            except OperationalError as e:
                # Handle transient database errors (connection issues, deadlocks, etc.)
                session.rollback()
                attempt += 1
                if attempt <= max_retries:
                    logging.warning(f"Database OperationalError: {e}")
                    logging.warning(
                        f"Retrying operation (attempt {attempt}/{max_retries})"
                    )
                    time.sleep(retry_delay)
                else:
                    logging.error(f"Max retries ({max_retries}) exceeded")
                    raise
            except SQLAlchemyError as e:
                # Handle other SQLAlchemy errors (integrity errors, etc.)
                logging.error(f"Database error: {e}")
                session.rollback()
                raise
            except Exception as e:  # noqa: B902
                # Handle unexpected errors
                logging.error(f"Unexpected error during database operation: {e}")
                session.rollback()
                raise
            finally:
                session.close()

    @classmethod
    def query_logs(cls, date, sh, sm, eh, em, levels, pid=None):
        """Query logs from the database with specified filters.

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

        Returns:
        --------
        list
            List of dictionaries containing log records
        """
        # logging.debug(f"Querying logs from {date} {sh}:{sm} to {date} {eh}:{em}")

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

            # Order results by timestamp
            query = query.order_by(LogTable.timestamp)

            # Execute query and convert results to dictionaries
            logs = [log.to_dict() for log in query.all()]

        return logs

    @classmethod
    def delete_logs_older_than(cls, cutoff_datetime):
        """Delete all log records older than the given datetime."""
        logging.info(f"Deleting logs older than {cutoff_datetime}")
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
        logging.debug(f"Check existence of job: {job_id}")
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
        logging.debug(f"Add entry to database: {data_to_insert['job_id']}")
        with cls.session_scope() as session:
            # Check existence within this session
            job_row = (
                session.query(JobTable.job_id)
                .filter_by(job_id=data_to_insert["job_id"])
                .first()
            )

            if job_row is not None:
                # Update existing entry
                logging.debug("Update entry.")
                job = (
                    session.query(JobTable)
                    .filter_by(job_id=data_to_insert["job_id"])
                    .first()
                )
                for column_name, column_value in data_to_insert.items():
                    setattr(job, column_name, column_value)
            else:
                # Create new entry
                logging.debug("New entry.")
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
        logging.debug(f"Update columns for job: {job_id}")

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
        logging.debug(f"Set submitted for job: {job_id}")

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
        logging.debug(f"Get columns for job: {job_id}")

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
        logging.debug(f"Delete job: {job_id}")
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
        logging.debug("List all jobs.")

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
    def get_lock(cls, task_type):
        """Get a lock for a specific background task type.

        This method queries the TaskLockTable in the database to retrieve
        the lock for a specific background task type. If the lock does not exist,
        it will be created. The lock is used to prevent multiple instances of the
        same background task type from running concurrently. The lock is released
        with the method 'release_lock'.

        Parameters:
        task_type (str): The type of background task.

        Returns:
        bool: True if the lock was acquired, False if it was already locked.
        """
        logging.debug(f"Get lock for task type: {task_type}")

        with cls.session_scope() as session:
            task_lock = (
                session.query(TaskLockTable)
                .filter_by(task_type=task_type)
                .with_for_update()
                .first()
            )
            if task_lock is None:
                task_lock = TaskLockTable(task_type=task_type, is_locked=True)
                session.add(task_lock)
                return True
            elif task_lock.is_locked:
                return False
            else:
                task_lock.is_locked = True
                return True

    @classmethod
    def release_lock(cls, task_type):
        """Release the lock for a specific background task type.

        This method releases the lock for a specific background task type in the
        TaskLockTable in the database. The lock is used to prevent multiple instances
        of the same background task type from running concurrently.

        Parameters:
        task_type (str): The type of background task.
        """
        logging.debug(f"Release lock for task type: {task_type}")

        with cls.session_scope() as session:
            task_lock = (
                session.query(TaskLockTable).filter_by(task_type=task_type).first()
            )

            if task_lock:
                task_lock.is_locked = False

    @classmethod
    def last_update_crns(cls):
        """Get the last update time for CRNS measurements.

        This method retrieves the last update time for CRNS measurements
        from the 'update_times_crns' table in the database.

        Returns:
        datetime: The last update time for CRNS measurements.
        """
        logging.debug("Get last update time for CRNS measurements")

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
    def add_update_crns(cls, successful):
        """Add a new update time for CRNS measurements.

        This method adds a new update time for CRNS measurements to the
        'update_times_crns' table in the database.

        Parameters:
        successful (bool): Indicates whether the update was successful.
        """
        logging.debug("Add new update time for CRNS measurements")

        with cls.session_scope() as session:
            new_update = UpdateTimesCRNS(
                update=datetime.utcnow(), successful=successful
            )
            session.add(new_update)


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

    def to_dict(self) -> Dict[str, Any]:
        """Convert log record to dictionary format."""
        return {
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "pid": self.pid,
            "level": self.level,
            "message": self.message,
            "module": self.module,
        }


class UpdateTimesCRNS(Base):
    """Represents the 'update_times_crns' table in the database."""

    __tablename__ = "update_times_crns"

    update = Column(DateTime, primary_key=True, nullable=False)
    successful = Column(Boolean, nullable=False)


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
        """Create a Shapely Point for PostGIS geometry column."""
        return Point(longitude, latitude)
