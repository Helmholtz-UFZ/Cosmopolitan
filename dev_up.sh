#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <mock|prod>"
    exit 1
fi

if [ "$1" == "mock" ]; then
    env_file="env_dev_mock"
elif [ "$1" == "prod" ]; then
    env_file="env_dev_prod_priv"
else
    echo "Usage: $0 <mock|prod>"
    echo "Invalid mode. Use 'mock' or 'prod'."
    exit 1
fi

if [ ! -e "$env_file" ]; then
    echo "File $env_file not found."
    exit 1
fi

cp "$env_file" .env

docker compose down
docker rm postgres

if [ "$1" == "prod" ]; then
    docker compose up --no-log-prefix --no-deps webserver
else
    docker compose up --no-log-prefix --attach webserver
fi
