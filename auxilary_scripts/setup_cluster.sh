#!/bin/bash

source .env

if [ ! -d "WEB_WORK_DIR" ]; then
    mkdir "WEB_WORK_DIR"
fi

lmod_env="BASH_ENV=/software/lmod/lmod/init/profile"
py_venv="$CLUSTER_PYTHON_ENV_PATH/bin/activate"
clean_up_script="$CLUSTER_COSMOPOLITAN_REPO/auxilary_scripts/clean_up_cluster.py"
logs="$HOME/clean_up.log"
cron_expression="0 1 * * *"

cron_entry="$lmod_env\n$cron_expression module load foss/2022b Python/3.10.8 && source $py_venv && python $clean_up_script >> $logs 2>&1"

# Add the cron entry
# (crontab -l ; echo "$cron_entry") | crontab -
echo -e "$cron_entry"
