#!/bin/bash

# Parse command line arguments
DEBUG_MODE=false
MODE=""

while [[ $# -gt 0 ]]; do
    case $1 in
    -d | --debug)
        DEBUG_MODE=true
        shift
        ;;
    mock | prod | stage)
        MODE="$1"
        shift
        ;;
    *)
        echo "Unknown option: $1"
        echo "Usage: $0 [-d|--debug] <mock|prod|stage>"
        echo "  -d, --debug: Enable debug mode (DEBUG=1)"
        echo "  mock: Use mock environment (env_dev_mock)"
        echo "  prod: Use production environment (env_dev_prod_priv)"
        echo "  stage: Use staging environment (env_dev_stage_priv)"
        exit 1
        ;;
    esac
done

if [ -z "$MODE" ]; then
    echo "Usage: $0 [-d|--debug] <mock|prod|stage>"
    echo "  -d, --debug: Enable debug mode (DEBUG=1)"
    echo "  mock: Use mock environment (env_dev_mock)"
    echo "  prod: Use production environment (env_dev_prod_priv)"
    echo "  stage: Use staging environment (env_dev_stage_priv)"
    exit 1
fi

if [ "$MODE" == "mock" ]; then
    env_file="env_dev_mock"
elif [ "$MODE" == "prod" ]; then
    env_file="env_dev_prod_priv"
elif [ "$MODE" == "stage" ]; then
    env_file="env_dev_stage_priv"
else
    echo "Invalid mode. Use 'mock', 'prod' or 'stage'."
    exit 1
fi

if [ ! -e "$env_file" ]; then
    echo "File $env_file not found."
    exit 1
fi

# Copy env file and optionally override FLASK_DEBUG variable
cp "$env_file" .env

if [ "$DEBUG_MODE" = true ]; then
    sed -i 's/^FLASK_DEBUG=.*/FLASK_DEBUG=1/' .env
else
    sed -i 's/^FLASK_DEBUG=.*/FLASK_DEBUG=0/' .env
fi

docker compose down
docker rm postgres

if [ "$MODE" == "prod" ] || [ "$MODE" == "stage" ]; then
    docker compose up --no-log-prefix --no-deps webserver
else
    docker compose up --no-log-prefix --attach webserver
fi
