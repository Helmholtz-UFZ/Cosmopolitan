"""Test if the back up setup is working correctly.

Not indendt to be used with pytest, but rather as a script to test the setup of the
backend.
"""

import os
import subprocess

with open("cosmopolitan_app/backend_util/cron_cleanup_call.sh", "r") as file:
    call = file.read().replace("$CLUSTER_COSMOPOLITAN_REPO", os.getcwd())

try:
    output = subprocess.check_output(call.split(), universal_newlines=True)
except subprocess.CalledProcessError as e:
    print(f"Command failed with return code: {e.returncode}")
    print(e.output)
