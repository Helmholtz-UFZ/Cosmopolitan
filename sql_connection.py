"""Module that handles the interaction with the data base."""

import json

from sqlalchemy import create_engine, Column, Date, String, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

with open("./parameters_flask_local.json", "r", encoding="UTF-8") as f_handle:
    PARAMETERS = json.load(f_handle)

DATABASE_URL = (
    f'postgresql+psycopg2://{PARAMETERS["db_user"]}:{PARAMETERS["db_pw"]}@'
    f'{PARAMETERS["db_host_name"]}:{PARAMETERS["db_port"]}/{PARAMETERS["db"]}'
)

Base = declarative_base()


class JobManager:
    """Class for the interaction with job table."""

    def __init__(self, db_url):
        """Init."""
        self.engine = create_engine(DATABASE_URL)
        self.Session = sessionmaker(bind=self.engine)

    def check_existence(self, job_id):
        """Check if job id already exist in DB."""
        with self.engine.begin() as conn:
            session = self.Session(bind=conn)
            job = session.query(Job).filter_by(job_id=job_id).first()
        return job is not None


class Job(Base):
    """Class Represents table job."""

    __tablename__ = "jobs"

    job_id = Column(String, primary_key=True)
    submission_date = (Column("submission_date", Date),)
    form = (Column("form", JSON),)


if __name__ == "__main__":
    job_manager = JobManager()
    job_id = "job123"
    if JobManager.check_job_id_existence(job_id):
        print(f"Job ID '{job_id}' exists in the table.")
    else:
        print(f"Job ID '{job_id}' does not exist in the table.")
