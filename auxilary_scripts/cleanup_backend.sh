#!/bin/bash

repo_path="$1"

module load foss/2022b Python/3.10.8 PostgreSQL/15.2

source "$repo_path/.env"

PYTHONPATH="$repo_path"

source "$CLUSTER_PYTHON_ENV_PATH/bin/activate"

python3 "$repo_path/auxilary_scripts/clean_up_cluster.py"
