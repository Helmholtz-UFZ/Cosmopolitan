"""This script is used to clean up the work directory of the cluster.

It will remove all the logs and work directories that are not associated with any job in
the database.
"""

import os
import shutil

from cosmopolitan_app.config import CLUSTER_LOG_DIR, CLUSTER_WORK_DIR
from cosmopolitan_app.db_manager import DataBaseManager

existing_jobs = list(DataBaseManager().list_jobs().keys())
for logs in os.listdir(os.path.join(CLUSTER_WORK_DIR, CLUSTER_LOG_DIR)):
    print(logs)
    if any((job_id in logs for job_id in existing_jobs)):
        print("Will not be deleted")
        continue
    print("Will be deleted")
    os.remove(os.path.join(CLUSTER_WORK_DIR, CLUSTER_LOG_DIR, logs))

existing_jobs.append(CLUSTER_LOG_DIR)

for job_work_dir in os.listdir(CLUSTER_WORK_DIR):
    print(job_work_dir)
    if job_work_dir in existing_jobs:
        print("Will not be deleted")
        continue
    print("Will be deleted")
    shutil.rmtree(os.path.join(CLUSTER_WORK_DIR, job_work_dir))
