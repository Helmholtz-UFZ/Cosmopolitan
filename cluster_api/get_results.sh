#!/bin/bash

set -e

load_param() {
    python3 -c "import config; print(config.$1)"
}

user=$(load_param "USER_CLUSTER")
machine=$(load_param "MACHINE_CLUSTER")
work_dir=$(load_param "WORK_DIR_CLUSTER")
output_dir=$(load_param "OUTPUT_DIR")

job_id=$1

scp -qr "$user@$machine:$work_dir/$job_id/"*.svg "$output_dir/$job_id/" 
