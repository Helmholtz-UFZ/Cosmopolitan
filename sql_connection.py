"""Module that handles the interaction with the data base."""

import json
import datetime
from sqlalchemy import create_engine, Column, Date, String, JSON
from sqlalchemy.orm import sessionmaker, declarative_base

with open("./parameters_flask_local.json", "r", encoding="UTF-8") as f_handle:
    PARAMETERS = json.load(f_handle)

DATABASE_URL = (
    f'postgresql+psycopg2://{PARAMETERS["db_user"]}:{PARAMETERS["db_pw"]}@'
    f'{PARAMETERS["db_host_name"]}:{PARAMETERS["db_port"]}/{PARAMETERS["db"]}'
)

Base = declarative_base()


class JobManager():
    """Class for the interaction with job table."""

    def __init__(self):
        """Init."""
        self.engine = create_engine(DATABASE_URL)
        self.Session = sessionmaker(bind=self.engine)

    def check_existence(self, job_id):
        """Check if job id already exist in DB."""
        with self.engine.begin() as conn:
            session = self.Session(bind=conn)
            job = session.query(Job).filter_by(job_id=job_id).first()
        return job is not None

    def add_entry(self, data_to_insert):
        with self.engine.begin() as conn:
            session = self.Session(bind=conn)
            job = Job(**data_to_insert)  # Create a new Job object with the provided data
            session.add(job)  # Add the new Job object to the session
            session.commit()  # Commit the session to persist the changes



class Job(Base):
    """Class Represents table job."""

    __tablename__ = "jobs"

    job_id = Column(String, primary_key=True)
    submission_date = (Column("submission_date", Date))
    form = (Column("form", JSON))


if __name__ == "__main__":
    job_manager = JobManager()
    job_id = "job123"

    json_data_to_insert = {
        'key1': 'value1',
        'key2': 42,
        'key3': ['item1', 'item2', 'item3']
    }

    data_to_insert = {
        'job_id': job_id,
        'submission_date': datetime.date(1990, 7, 15),
        'form': json_data_to_insert
    }

    job_manager.add_entry(data_to_insert)

    if job_manager.check_existence(job_id):
        print(f"Job ID '{job_id}' exists in the table.")
    else:
        print(f"Job ID '{job_id}' does not exist in the table.")
