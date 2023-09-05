#!/bin/bash

set -e

load_param() {
    python3 -c "import config; print(config.$1)"
}

user=$(load_param "USER_CLUSTER")
machine=$(load_param "MACHINE_CLUSTER")
work_dir=$(load_param "WORK_DIR_CLUSTER")

job_ids=$@

ssh -qT "$user"@"$machine" "cd $work_dir && rm -r $job_ids"
