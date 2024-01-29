#!/bin/bash

echo "Not working required python version (3.11) is not available on system"
echo "See ticket 42043141"
exit 1

module load foss/2022b Python/3.10.8 PostgreSQL/15.2

# This script should take a variable mode (dev, prod) and setup the cluster

# Check if .env file exists
source .env
if [ ! -f .env ]; then
    echo "No .env file found"
    exit 1
fi

mkdir -p "$WEB_WORK_DIR"

if [ -d "$CLUSTER_PYTHON_ENV_PATH" ]; then
    rm -r "$CLUSTER_PYTHON_ENV_PATH"
fi

python -m venv "$CLUSTER_PYTHON_ENV_PATH"

source "$CLUSTER_PYTHON_ENV_PATH/bin/activate"
# TODO Poetry
# Quickfix
pip install -r ./requirements.txt
# pip install poetry
# poetry install --no-interaction --no-ansi

lmod_env="BASH_ENV=/software/lmod/lmod/init/profile"
logs="$HOME/clean_up.log"
cron_expression="59 13 * * *"
cron_entry="$lmod_env\n$cron_expression bash $CLUSTER_COSMOPOLITAN_REPO/auxilary_scripts/start_cleanup_backend.sh $CLUSTER_COSMOPOLITAN_REPO >> $logs 2>&1"

# echo -e "$cron_entry" | crontab -
echo -e "$cron_entry"
# lmod_env="BASH_ENV=/software/lmod/8.7.30/init/profile"
# Add the cron entry
# (crontab -l ; echo "$cron_entry") | crontab -

# cron_entry="$lmod_env\n$cron_expression module load foss/2022b Python/3.10.8 >> $logs 2>&1"
# cron_entry="$lmod_env\n$cron_expression (source /software/lmod/8.7.30/init/profile && module load foss/2022b Python/3.10.8 && source $py_venv && python $clean_up_script) >> $logs 2>&1"
