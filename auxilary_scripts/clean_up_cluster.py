import os
import shutil

from cosmopolitan_app.db_manager import DataBaseManager
from cosmopolitan_app.config import WEB_WORK_DIR, LOG_CLUSTER_DIR_NAME

existing_jobs = list(DataBaseManager().list_jobs().keys())

for logs in os.listdir(os.path.join(WEB_WORK_DIR, LOG_CLUSTER_DIR_NAME)):
    print(logs)
    if any((job_id in logs for job_id in existing_jobs)):
        print("Will not be deleted")
        continue
    print("Will be deleted")
    os.remove(os.path.join(WEB_WORK_DIR, LOG_CLUSTER_DIR_NAME, logs))

existing_jobs.append(LOG_CLUSTER_DIR_NAME)

for job_work_dir in os.listdir(WEB_WORK_DIR):
    print(job_work_dir)
    if job_work_dir in existing_jobs:
        print("Will not be deleted")
        continue
    print("Will be deleted")
    shutil.rmtree(os.path.join(WEB_WORK_DIR, job_work_dir))
