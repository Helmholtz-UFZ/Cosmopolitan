#!/bin/bash

set -e

load_param() {
    python3 -c "import config; print(config.$1)"
}

user=$(load_param "USER_CLUSTER")
machine=$(load_param "MACHINE_CLUSTER")
repo_dir=$(load_param "REPO_DIR_CLUSTER")
python_env_path=$(load_param "PYTHON_ENV_PATH_CLUSTER")
work_dir=$(load_param "WORK_DIR_CLUSTER")
input_dir=$(load_param "INPUT_DIR")

job_id=$1

scp -r "$input_dir/$job_id" "$user@$machine:$work_dir"

ssh "$user"@"$machine" "sstart_job_cluster.sh $job_id $work_dir $python_env_path $repo_dir"
