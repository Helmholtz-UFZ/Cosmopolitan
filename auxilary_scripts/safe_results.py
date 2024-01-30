"""This script should be executed after the sm-prediction job on the cluster."""

import sys
import logging
from flask import Flask

from cosmopolitan_app.cosmopolitan_job import CosmopolitanJob
from cosmopolitan_app.config import CLUSTER_WORK_DIR

logging.basicConfig(level=logging.DEBUG)

# Create a minimal Flask app for the context of CosmopolitanJobForm
app = Flask(__name__)
with app.app_context():
    cosmopolitan_job = CosmopolitanJob(
        job_id=sys.argv[1], base_work_dir=CLUSTER_WORK_DIR
    )
    if sys.argv[2] == "save":
        cosmopolitan_job.save()
