#!/bin/bash
# This script should set up the backend server environment.

module load foss/2022b Python/3.11.2-bare PostgreSQL/15.2

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <dev|prod>"
    exit 1
fi

if [ "$1" == "dev" ]; then
    env_file=".env_dev_prod"
elif [ "$1" == "prod" ]; then
    env_file=".env_prod"
else
    echo "Usage: $0 <dev|prod>"
    echo "Invalid mode. Use 'dev' or 'prod'."
    exit 1
fi

# If the .env file does not exist, copy the appropriate .env file to the current
# directory.
overwrite=true
# If the .env file exists, ask the user if they want to overwrite it.
if [ -f .env ]; then
    while true; do
        read -p "The .env file already exists. Do you want to overwrite it (Y/n)? " yn
        if [[ "$yn" =~ Y|y|^$ ]]; then
            break
        fi
        if [[ "$yn" =~ N|n ]]; then
            overwrite=false
            break
        fi
        echo "Answer Y/n."
    done
fi
if [ "$overwrite" == true ]; then
    cp "$env_file" .env
    # Ask the user to add passwords to the .env file.
    echo "Please add passwords to the .env file"
    while true; do
        read -p "Should ${EDITOR:-vi} be used to open the file (Y/n)? " yn
        if [[ "$yn" =~ Y|y|^$ ]]; then
            "${EDITOR:-vi}" ".env"
            break
        fi
        if [[ "$yn" =~ N|n ]]; then break; fi
        echo "Answer Y/n."
    done
fi

source .env

mkdir -p "$CLUSTER_WORK_DIR"

# If the virtual environment does not exist, create it.
overwrite=true
# If the python environment exists, ask the user if they want to overwrite it.
if [ -d "$CLUSTER_PYTHON_ENV_PATH" ]; then
    while true; do
        read -p "A python environment already exists. Do you want to overwrite it (Y/n)? " yn
        if [[ "$yn" =~ Y|y|^$ ]]; then
            break
        fi
        if [[ "$yn" =~ N|n ]]; then
            overwrite=false
            break
        fi
        echo "Answer Y/n."
    done
fi
if [ "$overwrite" == true ]; then
    python -m venv "$CLUSTER_PYTHON_ENV_PATH"
    
    source "$CLUSTER_PYTHON_ENV_PATH/bin/activate"
    pip install poetry
    poetry install --no-interaction --no-ansi
fi

# Create clean up cron job
lmod_env="BASH_ENV=/software/lmod/lmod/init/profile"
logs="$HOME/clean_up_$1.log"
cron_expression="00 3 * * *"
if [ ! -f ./cosmopolitan_app/backend_util/cron_cleanup_call.sh ]; then
    echo "Cann not find cron_cleanup_call.sh. Exiting."
    exit 1
fi
cron_call=$(cat ./cosmopolitan_app/backend_util/cron_cleanup_call.sh)

cron_entry="$lmod_env\n$cron_expression bash $CLUSTER_COSMOPOLITAN_REPO/auxilary_scripts/cleanup_backend.sh $CLUSTER_COSMOPOLITAN_REPO/.env >> $logs 2>&1"
# If no cron job exists, create one.
overwrite=true
# If the cron job exists, ask the user if they want to overwrite it.
current_cron=$(crontab -l)
if [[ $current_cron != "" ]]; then
    echo "Cron job already exists."
    echo "$current_cron"
    while true; do
        read -p "Do you want to overwrite it (Y/n)? " yn
        if [[ "$yn" =~ Y|y|^$ ]]; then
            break
        fi
        if [[ "$yn" =~ N|n ]]; then
            overwrite=false
            break
        fi
        echo "Answer Y/n."
    done
fi
if [ "$overwrite" == true ]; then
    (crontab -l ; echo -e "$cron_entry") | crontab -
else
    echo "If you want to edit the cron job, run:"
    echo "crontab -e"
    echo "This would have been the cron job:"
    echo -e "$cron_entry"
fi
