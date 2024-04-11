#!/bin/bash

module load foss/2022b Python/3.11.2-bare PostgreSQL/15.2

if [ ! -f "$1" ]; then
    echo "Can not find enviroment file: $1"
    exit 1
fi

source "$1"

PYTHONPATH="$CLUSTER_COSMOPOLITAN_REPO"

source "$CLUSTER_PYTHON_ENV_PATH/bin/activate"

python3 "$CLUSTER_COSMOPOLITAN_REPO/cosmopolitan_app/backend_util/cleanup_work_dir.py"
