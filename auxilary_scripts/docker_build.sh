#!/bin/bash

set -e

. .env

docker rm "$(docker ps -all | tail -n 1 | awk '{print $1}')"

docker build --progress plain --no-cache -t cosmopolitan-test . 

docker run --name cosmopolitan-test \
    -e EMAIL_PASSWORD="$EMAIL_PASSWORD" \
    -e DB_PW="$DB_PW" \
    -e CLUSTER_TOKEN="$CLUSTER_TOKEN" \
    cosmopolitan-test
