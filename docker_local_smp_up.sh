#!/bin/bash

# To set other smp path use: export SOIL_MOISTURE_PREDICTION_PATH="/foo/bar"

if [ -f .env ]; then
    mv .env .env.bak
fi

cp env_test .env

docker compose -f docker-compose.yml -f docker-compose.local_smp.yml up
