#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <mock|prod>"
    exit 1
fi

mode=$1

if [ "$mode" != "mock" ]; then
    env_file=".env_dev_mock"
elif [ "$mode" != "prod" ]; then
    env_file=".env_dev_prod_priv"
else
    echo "Invalid mode. Use 'mock' or 'prod'."
    exit 1
fi

if [ ! -e "$env_file" ]; then
    echo "File $env_file not found."
    exit 1
fi

cp "$env_file" .env

if [ "$mode" == "prod" ]; then
    docker-compose up cosmopolitan-local
else
    docker-compose up --attach cosmopolitan-local
fi
