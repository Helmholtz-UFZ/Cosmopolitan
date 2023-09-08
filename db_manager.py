"""Module for interaction between webservice and data base.

This module defines the DataBaseManager class for interacting with job entries
in a database. The DataBaseManager class provides methods to check for the
existence of a job, add or update job entries, and retrieve all columns of a
specific job entry.

Classes:
- DataBaseManager: A class for managing job entries in the database.
- JobTable: Represents the 'jobs' table in the database.
"""

import datetime
from sqlalchemy import create_engine, Column, Date, String, JSON, Boolean, Float
from sqlalchemy.orm import sessionmaker, declarative_base

from config import DB_NAME, DB_HOST_NAME, DB_PORT, DB_USER, DB_PW

Base = declarative_base()


class JobNotFound(Exception):
    """Custom exception for when a job is not found."""

    pass


class DataBaseManager:
    """Class for interacting with the 'jobs' table in the database.

    This class encapsulates methods to manage job entries in the 'jobs' table
    of the database. It provides functionalities to check for the existence of
    a job by its ID and to add or update job entries.

    Attributes:
    database_url (str): The URL for connecting to the PostgreSQL database.
    engine (sqlalchemy.engine.base.Engine): The database connection engine.
    Session (sqlalchemy.orm.session.sessionmaker): A session factory for
    creating sessions to interact with the database.

    Methods:
    check_existence(job_id): Check if a job with the given job ID exists in the
    database.
    add_entry(data_to_insert): Add or update a job entry in the database.
    get_job_columns(job_id): Retrieve all columns of a specific job entry based
    on its job ID.
    """

    database_url = (
        f"postgresql+psycopg2://{ DB_USER }:{ DB_PW }@"
        f"{ DB_HOST_NAME }:{ DB_PORT }/{ DB_NAME }"
    )

    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)

    def check_existence(self, job_id):
        """Check if a job with the given job ID exists in the database.

        This method queries the 'jobs' table in the database to determine
        whether a job with the provided job ID exists.

        Parameters:
        job_id (str): The unique identifier for the job.

        Returns:
        bool: True if a job with the given job ID exists, False otherwise.
        """
        with self.engine.begin() as conn:
            session = self.Session(bind=conn)
            job_row = session.query(JobTable).filter_by(job_id=job_id).first()
        return job_row is not None

    def add_entry(self, data_to_insert):
        """Add or update a job entry in the database.

        This method takes a dictionary containing job information and
        either adds a new entry to the 'jobs' table or updates an existing
        entry based on the provided 'job_id'.

        Parameters:
        data_to_insert (dict): A dictionary containing job information with keys
        equivalent to the cloumns ins JobTable.

        Returns:
        None
        """
        with self.engine.begin() as conn:
            session = self.Session(bind=conn)
            job_row = JobTable(**data_to_insert)
            session.merge(job_row)
            session.commit()

    def get_job_columns(self, job_id):
        """Retrieve all columns of a specific job entry based on its job ID.

        This method queries the 'jobs' table in the database to retrieve all
        columns of the job entry associated with the provided job ID.

        Parameters:
        job_id (str): The unique identifier for the job.

        Returns:
        dict: A dictionary containing all columns and their values for the
        specified job.

        Raises:
        ValueError: If the job with the provided job ID does not exist.
        """
        with self.engine.begin() as conn:
            session = self.Session(bind=conn)
            job_row = session.query(JobTable).filter_by(job_id=job_id).first()
            if job_row:
                job_columns = {
                    column.name: getattr(job_row, column.name)
                    for column in JobTable.__table__.columns
                }
                return job_columns
            else:
                raise JobNotFound(f"Job with ID '{job_id}' not found")

    def delete_job(self, job_id):
        """Delete a job entry from the database based on its job ID.

        This method deletes a job entry from the 'jobs' table in the database
        based on the provided job ID.

        Parameters:
        job_id (str): The unique identifier for the job to be deleted.

        Raises:
        JobNotFound: If the job with the provided job ID does not exist.
        """
        with self.engine.begin() as conn:
            session = self.Session(bind=conn)
            job = session.query(JobTable).filter_by(job_id=job_id).first()
            if job:
                session.delete(job)
                session.commit()
            else:
                raise JobNotFound(f"Job with ID '{job_id}' not found")

    def list_jobs(self):
        """List all jobs in the database with their submission date and submission status.

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
        with self.engine.begin() as conn:
            session = self.Session(bind=conn)
            job_rows = session.query(JobTable).all()

            job_info = {}
            for job_row in job_rows:
                job_info[job_row.job_id] = (job_row.start_date, job_row.submitted)
            return job_info


class JobTable(Base):
    """Represents the 'jobs' table in the database.

    This class defines the mapping between the 'jobs' table in the database and
    the Python object model. It includes the necessary columns for job entries.
    """

    __tablename__ = "jobs"

    job_id = Column(String, primary_key=True)
    start_date = Column("start_date", Date)
    input_data = Column("input_data", JSON)
    submitted = Column("submitted", Boolean)
    cluster_job_id = Column("cluster_job_id", String)
    email = Column("email", String)
    notified_end = Column("notified_end", Boolean)
    logs = Column("logs", String)
    status = Column("status", String)
    version = Column("version", Float)


def test():
    """Test basic connectivity."""
    db_manager = DataBaseManager()
    job_id = "job123"

    json_data_to_insert = {
        "key1": "value1",
        "key2": 42,
        "key3": ["item1", "item2", "item3"],
    }

    data_to_insert = {
        "job_id": job_id,
        "start_date": datetime.date(1990, 7, 15),
        "input_data": json_data_to_insert,
        "submitted": True,
        "email": "wtf@where.some",
        "email_status": "send",
        "err_msg": "None",
        "finished": False,
        "version": 0.01,
    }

    db_manager.add_entry(data_to_insert)

    if db_manager.check_existence(job_id):
        print(f"Job ID '{job_id}' exists in the table.")
    else:
        print(f"Job ID '{job_id}' does not exist in the table.")


if __name__ == "__main__":
    test()
