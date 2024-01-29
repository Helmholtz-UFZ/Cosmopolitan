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

cp "$env_file" .env

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

source .env

mkdir -p "$CLUSTER_WORK_DIR"

if [ ! -d "$CLUSTER_PYTHON_ENV_PATH" ]; then
    python -m venv "$CLUSTER_PYTHON_ENV_PATH"
    
    source "$CLUSTER_PYTHON_ENV_PATH/bin/activate"
    pip install poetry
    poetry install --no-interaction --no-ansi
fi

lmod_env="BASH_ENV=/software/lmod/lmod/init/profile"
logs="$HOME/clean_up_$1.log"
cron_expression="00 3 * * *"
cron_entry="$lmod_env\n$cron_expression bash $CLUSTER_COSMOPOLITAN_REPO/auxilary_scripts/cleanup_backend.sh $CLUSTER_COSMOPOLITAN_REPO/.env >> $logs 2>&1"

# echo -e "$cron_entry" | crontab -
# echo -e "$cron_entry"

(crontab -l ; echo -e "$cron_entry") | crontab -
