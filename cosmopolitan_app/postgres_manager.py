"""Module for interaction between webservice and data base."""

import logging
import time

from sqlalchemy import JSON, Boolean, Column, Date, String, create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from cosmopolitan_app.config import (
    POSTGRES_HOST_NAME,
    POSTGRES_NAME,
    POSTGRES_PORT,
    POSTGRES_PW,
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
        f"postgresql+psycopg2://{ POSTGRES_USER }:{ POSTGRES_PW }@"
        f"{ POSTGRES_HOST_NAME }:{ POSTGRES_PORT }/{ POSTGRES_NAME }"
    )
    print(POSTGRES_HOST_NAME)
    print(POSTGRES_PORT)
    print(POSTGRES_NAME)
    engine = create_engine(database_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)

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
        with cls.Session() as session:
            job_row = session.query(JobTable.job_id).filter_by(job_id=job_id).first()
        return job_row is not None

    @classmethod
    def add_entry(cls, data_to_insert):
        """Add or update a job entry in the database.

        This method takes a dictionary containing job information and

        Parameters:
        data_to_insert (dict): A dictionary containing job information with keys
        equivalent to the cloumns ins JobTable.
        """
        logging.debug(f"Add entry to database: {data_to_insert['job_id']}")
        if cls.check_existence(data_to_insert["job_id"]):
            logging.debug("Update entry.")
            cls.update_column(data_to_insert["job_id"], data_to_insert)
            return

        with cls.Session() as session:
            logging.debug("New entry.")
            job_row = JobTable(**data_to_insert)
            session.merge(job_row)
            session.commit()

        logging.debug("Entry added.")

    @classmethod
    def update_column(cls, job_id, column_dic):
        """Update a specific column in the 'JobTable' for a given job ID."""
        retries = 0
        while retries < max_retries:
            with cls.Session() as session:
                try:
                    job = session.query(JobTable).filter_by(job_id=job_id).first()
                    if job is None:
                        raise JobNotFound(job_id)
                    for column_name, column_value in column_dic.items():
                        setattr(job, column_name, column_value)
                    session.commit()
                    break
                except OperationalError as e:
                    session.rollback()
                    retries += 1
                    if retries == max_retries:
                        raise
                    logging.warning(f"OperationalError: {e}")
                    logging.warning("Retry operation.")
                    time.sleep(1)
                except:  # noqa: E722
                    session.rollback()
                    raise

    @classmethod
    def set_submitted(cls, job_id):
        """Update the 'submitted' column in the 'JobTable' for a given job ID.

        The method works as well as a lock so that the job is not submitted twice.

        Raises:
        JobNotFound: If the job with the provided job ID does not exist.
        """
        with cls.Session() as session:
            job = (
                session.query(JobTable)
                .filter_by(job_id=job_id)
                .with_for_update()
                .first()
            )
            if job is None:
                session.commit()
                raise JobNotFound(job_id)

            if job.submitted:
                session.commit()
                return False
            else:
                job.submitted = True
                session.commit()
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
        retries = 0
        while retries < max_retries:
            with cls.Session() as session:
                try:
                    job_row = session.query(JobTable).filter_by(job_id=job_id).first()
                    break
                except OperationalError as e:
                    session.rollback()
                    retries += 1
                    if retries == max_retries:
                        raise
                    logging.warning(f"OperationalError: {e}")
                    logging.warning("Retry operation.")
                    time.sleep(1)
                except:  # noqa: E722
                    session.rollback()
                    raise

        if job_row:
            job_columns = {
                column.name: getattr(job_row, column.name)
                for column in JobTable.__table__.columns
            }
            return job_columns
        else:
            raise JobNotFound(job_id)

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
        with cls.Session() as session:
            job = (
                session.query(JobTable)
                .filter_by(job_id=job_id)
                .with_for_update()
                .first()
            )
            if job:
                session.delete(job)
                session.commit()
            else:
                raise JobNotFound(job_id)

    @classmethod
    def list_jobs(cls):
        """List all jobs in the database with their submission date and status.

        This method retrieves all job entries from the 'jobs' table in the
        database and returns a dictionary where the keys are 'job_id', and the
        values are a tuple containing 'start_date' and 'submitted' status
        for each job.

        Returns:
        dict: A dictionary where keys are 'job_id' and values are tuples
        containing 'start_date' and 'submitted' status.

        Example:
        {
        'job1': ('2023-09-01', True),
        'job2': ('2023-09-02', False),
        # ...
        }

        """
        with cls.Session() as session:
            job_rows = session.query(JobTable).all()

            job_info = {}
            for job_row in job_rows:
                job_info[job_row.job_id] = (job_row.start_date, job_row.submitted)
            return job_info

    @classmethod
    def get_lock(cls, task_type):
        """Get a lock for a specific backgroung task type.

        This method queries the TaskLockTable in the database to retrieve
        the lock for a specific background task type. If the lock does not exist,
        it will be created. The lock is used to prevent multiple instances of the
        same background task type from running concurrently. The lock is released
        with the method 'release_lock'.
        """
        logging.debug(f"Get lock for task type: {task_type}")
        with cls.Session() as session:
            task_lock = (
                session.query(TaskLockTable)
                .filter_by(task_type=task_type)
                .with_for_update()
                .first()
            )
            if task_lock is None:
                task_lock = TaskLockTable(task_type=task_type, is_locked=True)
                session.add(task_lock)
            elif task_lock.is_locked:
                return False
            else:
                task_lock.is_locked = True
            session.commit()
        return True

    @classmethod
    def release_lock(cls, task_type):
        """Release the lock for a specific background task type.

        This method releases the lock for a specific background task type in the
        TaskLockTable in the database. The lock is used to prevent multiple instances
        of the same background task type from running concurrently.
        """
        logging.debug(f"Release lock for task type: {task_type}")
        with cls.Session() as session:
            task_lock = (
                session.query(TaskLockTable).filter_by(task_type=task_type).first()
            )
            if task_lock:
                task_lock.is_locked = False
                session.commit()


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
    email = Column("email", String)
    notified_end = Column("notified_end", Boolean)
    logs = Column("logs", String)
    status = Column("status", String)
    version = Column("version", String)
