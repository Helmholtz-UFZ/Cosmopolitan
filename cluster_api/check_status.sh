#!/bin/bash

set -e

load_param() {
    python3 -c "import config; print(config.$1)"
}

user=$(load_param "USER_CLUSTER")
machine=$(load_param "MACHINE_CLUSTER")
work_dir=$(load_param "WORK_DIR_CLUSTER")

job_id=$1
cluster_job_id=$2

status=$(ssh -qT "$user"@"$machine" "sacct -j $cluster_job_id --format=State,JobID --noheader | grep -v '\.batch' | awk '{print \$1}'")
echo "$status"
if [ "$status" == "PENDING" ]; then
    exit 0
fi

ssh -qT "$user"@"$machine" "cat $work_dir/$job_id/logs"
