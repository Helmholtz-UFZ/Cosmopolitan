#!/bin/bash

set -e

. .env

show_usage() {
    echo "Usage: $0 [-r|--run_only]"
    echo "  -r, --run_only    Do not build only start container"
    exit 1
}

run_only=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        -r|--run_only)
            run_only=1
            shift
            ;;
        *)
            show_usage
            ;;
    esac
done

# Test if variables are set
variable_list=("PORT" "CLUSTER_TOKEN" "EMAIL_PASSWORD" "DB_PW" "FLASK_DEBUG" "GIT_PAT_SM" "GUNICORN")
for var_name in "${variable_list[@]}"; do
    if [ -z "${!var_name}" ]; then
        echo "Error: $var_name is not set in the environment."
        exit 1
    fi
done

if [ ! -d ".git" ]; then
    echo "Error: This script must be run at the base of the git repository."
    exit 1
fi

repo_name=$(git rev-parse --show-toplevel | xargs basename)
if [ "$repo_name" != "SOM-Web" ]; then
    echo "Error: This script must be run at the base of the git repository."
    exit 1
fi

container_name="$(docker ps -all | grep cosmopolitan-test | awk '{print $1}')"
if [ -n "$container_name" ]; then
    docker rm "$container_name"
fi

if [ "$run_only" = 0 ]; then
    docker build --build-arg GIT_PAT_SM="$GIT_PAT_SM" \
        --build-arg GUNICORN="$GUNICORN" \
        --build-arg PORT=$PORT \
        --progress plain \
        -t cosmopolitan-test \
        .
fi

docker run --name cosmopolitan-test \
    -v "$(pwd)/cosmopolitan_app:/python_docker/cosmopolitan/cosmopolitan_app" \
    -e EMAIL_PASSWORD="$EMAIL_PASSWORD" \
    -e DB_PW="$DB_PW" \
    -e CLUSTER_TOKEN="$CLUSTER_TOKEN" \
    -e FLASK_DEBUG="$FLASK_DEBUG" \
    -p $PORT:$PORT \
    cosmopolitan-test

