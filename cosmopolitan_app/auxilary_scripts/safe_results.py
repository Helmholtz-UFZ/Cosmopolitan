"""This script should be executed before and after the job on the cluster."""

import logging
import sys
import time

import requests
from flask import Flask

from cosmopolitan_app.config import CLUSTER_WORK_DIR, WEB_OUTSIDE_URL
from cosmopolitan_app.cosmopolitan_job import CosmopolitanJob

logging.basicConfig(level=logging.DEBUG)


def main(job_id, mode):
    """Will load, save the job and notify after save the frontend."""
    # Create a minimal Flask app for the context of CosmopolitanJobForm
    app = Flask(__name__)
    with app.app_context():
        cosmopolitan_job = CosmopolitanJob(
            job_id=job_id, base_work_dir=CLUSTER_WORK_DIR
        )
        if mode == "save":
            cosmopolitan_job.save()
            url = f"{WEB_OUTSIDE_URL}/submission/{job_id}"
            for attempt in range(3):
                response = requests.get(url)
                try:
                    response.raise_for_status()
                except requests.exceptions.ConnectionError:
                    logging.info(
                        "Could not reach the frontend.\n"
                        f"Status code: {response.status_code}"
                    )
                    logging.info(url)
                    time.sleep(10)
                except requests.exceptions.HTTPError:
                    logging.info(f"HTTP error: {response.status_code}")
                    logging.info(url)
                    break
                logging.info("Informed frontend")
                break


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
