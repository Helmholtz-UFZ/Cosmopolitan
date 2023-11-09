import os
import shutil

from cosmopolitan_app.db_manager import DataBaseManager
from cosmopolitan_app.config import WEB_WORK_DIR, LOG_DIR

existing_jobs = list(DataBaseManager().list_jobs().keys())

for job_work_dir in os.listdir(WEB_WORK_DIR):
    print(job_work_dir)
    if job_work_dir in existing_jobs:
        continue
    print("Should be deleted")
