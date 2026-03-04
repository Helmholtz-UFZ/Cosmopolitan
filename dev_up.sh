#!/bin/bash

# Parse command line arguments
DEBUG_MODE=false
LOCAL_SMP=false
MODE=""

while [[ $# -gt 0 ]]; do
    case $1 in
    -d | --debug)
        DEBUG_MODE=true
        shift
        ;;
    --local-smp)
        LOCAL_SMP=true
        shift
        ;;
    mock | prod | stage)
        MODE="$1"
        shift
        ;;
    *)
        echo "Unknown option: $1"
        echo "Usage: $0 [-d|--debug] [--local-smp] <mock|prod|stage>"
        echo "  -d, --debug:  Enable debug mode (FLASK_DEBUG=1)"
        echo "  --local-smp:  Use local ../soil-moisture-prediction instead of PyPI version"
        echo "  mock:  Use mock environment (env_dev_mock)"
        echo "  prod:  Use production environment (env_dev_prod_priv)"
        echo "  stage: Use staging environment (env_dev_stage_priv)"
        exit 1
        ;;
    esac
done

if [ -z "$MODE" ]; then
    echo "Usage: $0 [-d|--debug] [--local-smp] <mock|prod|stage>"
    echo "  -d, --debug:  Enable debug mode (FLASK_DEBUG=1)"
    echo "  --local-smp:  Use local ../soil-moisture-prediction instead of PyPI version"
    echo "  mock:  Use mock environment (env_dev_mock)"
    echo "  prod:  Use production environment (env_dev_prod_priv)"
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

# Build compose command (optionally layer local soil-moisture-prediction override)
COMPOSE="docker compose -f docker-compose.yml"
if [ "$LOCAL_SMP" = true ]; then
    if [ ! -d "../soil-moisture-prediction" ]; then
        echo "Error: ../soil-moisture-prediction directory not found."
        echo "Clone soil-moisture-prediction as a sibling directory first."
        exit 1
    fi
    COMPOSE="$COMPOSE -f docker-compose.local-smp.yml"
    echo "Using local soil-moisture-prediction from ../soil-moisture-prediction"
fi

# Rebuild images when uv.lock or Dockerfiles change
CURRENT_HASH="$(sha256sum uv.lock docker/dev.Dockerfile docker/worker.Dockerfile)"
if [ ! -e ".docker_build_hash" ] || [ "$CURRENT_HASH" != "$(cat .docker_build_hash)" ]; then
    $COMPOSE build webserver
    $COMPOSE build worker

    echo "$CURRENT_HASH" >.docker_build_hash
fi

cleaning_up() {
    echo "Cleaning up..."
    $COMPOSE down 2>/dev/null || true
}

trap cleaning_up EXIT

$COMPOSE down
docker rm -f postgres_cosmopolitan 2>/dev/null || true

if [ "$MODE" == "prod" ] || [ "$MODE" == "stage" ]; then
    $COMPOSE up --no-log-prefix --no-deps webserver
else
    $COMPOSE up --no-log-prefix --attach webserver
fi
