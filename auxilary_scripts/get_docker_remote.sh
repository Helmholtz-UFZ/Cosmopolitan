#!/bin/bash

set -e

usage() {
    echo "Usage: $0 [-v|--version <version>]"
    echo "Will pull the docker container with the specified version and start the image."
    echo "Options:"
    echo "  -v, --version <version>   Specify the version number (e.g., 0.1.1, 1.2.3, latest)"
    echo "                            default latest"
    exit 1
}

# Default values
version="latest"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -v|--version)
            version="$2"
            shift 2
            ;;
        *)
            usage
            ;;
    esac
done

# Validate version using regex
version_regex="^(latest|[0-9]+\.[0-9]+\.[0-9]+)$"
if ! [[ "$version" =~ "$version_regex" ]]; then
    echo "Error: Invalid version format. Please provide a valid version number or 'latest'."
    usage
fi

. .env

# Test if variables are set
variable_list=("PORT" "CLUSTER_TOKEN" "EMAIL_PASSWORD" "DB_PW" "FLASK_DEBUG")
for var_name in "${variable_list[@]}"; do
    if [ -z "${!var_name}" ]; then
        echo "Error: $var_name is not set in the environment."
        exit 1
    fi
done

docker login git.ufz.de:4567

docker pull "git.ufz.de:4567/andersj/som-web:$version"

docker run  \
    -e EMAIL_PASSWORD="$EMAIL_PASSWORD" \
    -e DB_PW="$DB_PW" \
    -e CLUSTER_TOKEN="$CLUSTER_TOKEN" \
    -e FLASK_DEBUG="$FLASK_DEBUG" \
    -p $PORT:$PORT \
    91947412eb1d
