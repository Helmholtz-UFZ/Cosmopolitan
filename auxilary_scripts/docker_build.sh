#!/bin/bash

set -e

. .env

container_name="$(docker ps -all | grep cosmopolitan-test | awk '{print $1}')"
if [ -n "$container_name" ]; then
    docker rm "$container_name"
fi

    # --no-cache \
docker build --build-arg GIT_PAT_SM="$GIT_PAT_SM" \
    --build-arg GUNICORN="$GUNICORN" \
    --build-arg PORT=$PORT \
    --progress plain \
    -t cosmopolitan-test \
    . 

docker run --name cosmopolitan-test \
    -v "$(pwd)/cosmopolitan_app:/python_docker/cosmopolitan/cosmopolitan_app" \
    -e EMAIL_PASSWORD="$EMAIL_PASSWORD" \
    -e DB_PW="$DB_PW" \
    -e CLUSTER_TOKEN="$CLUSTER_TOKEN" \
    -e FLASK_DEBUG="$FLASK_DEBUG" \
    -p $PORT:$PORT \
    cosmopolitan-test
