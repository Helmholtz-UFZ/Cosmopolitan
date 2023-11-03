"""This script should be executed after the sm-prediction job on the cluster."""

import sys

from cosmopolitan_app.cosmopolitan_job import CosmopolitanJob

cosmopolitan_job = CosmopolitanJob(job_id=sys.argv[1])
cosmopolitan_job.get_results()
