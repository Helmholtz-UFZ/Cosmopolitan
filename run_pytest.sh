#!/bin/bash

set -e

# Parse command line arguments
START_SERVICES=1
TEST_PATH=""

show_help() {
    echo "Usage: ./run_pytest.sh [OPTIONS] [TEST_PATH]"
    echo ""
    echo "Pytest runner with service management and test selection"
    echo ""
    echo "Options:"
    echo "  --no-services     Don't start/stop services (assume already running)"
    echo "  -h, --help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./run_pytest.sh                    # Run all tests with all services"
    echo "  ./run_pytest.sh test/test_app.py   # Run specific test file"
    echo "  ./run_pytest.sh --no-services      # Run tests, assume services already running"
    echo "  ./run_pytest.sh --no-services test/test_app.py"
    exit 0
}

cleaning_up() {
    # Restore original .env
    if [ -f .env.bak ]; then
        mv .env.bak .env
    fi

    docker rm -f postgres 2>/dev/null || true
    docker compose down 2>/dev/null || true
    echo "Cleanup complete"
}

check_service() {
    local check_command="$1"
    local service_name="$2"
    local max_retries=10
    local retry_count=0

    echo "Checking ${service_name}..."
    until eval "$check_command"; do
        if [ $retry_count -ge $max_retries ]; then
            echo "${service_name} failed to start after ${max_retries} attempts"
            echo "Cleaning up..."
            cleaning_up
            exit 1
        fi
        echo "Waiting for ${service_name} to be available... (${retry_count}/${max_retries})"
        sleep 1
        retry_count=$((retry_count + 1))
    done
    echo "${service_name} is ready"
}

while [[ $# -gt 0 ]]; do
    case $1 in
    --no-services)
        START_SERVICES=0
        shift
        ;;
    -h | --help)
        show_help
        ;;
    *)
        TEST_PATH="$1"
        shift
        ;;
    esac
done

# Backup existing .env if present
if [ -f .env ]; then
    mv .env .env.bak
fi

# Use test environment configuration
cp env_test_local .env

docker compose down 2>/dev/null || true

# Source the .env file to load environment variables
source .env

if [ "$START_SERVICES" -eq 1 ]; then
    # Clean up any existing postgres container
    docker rm -f postgres 2>/dev/null || true

    # Start Docker services
    echo "Starting services: postgres, mailhog, minio, redis"
    cp env_dev_mock .env # Ensure env file is set for services
    docker compose up postgres mailhog minio redis -d
    cp env_test_local .env # Restore test env

    # Wait for services to be ready
    check_service "docker exec postgres_cosmopolitan pg_isready -q" "PostgreSQL"
    check_service "curl --silent --output /dev/null http://localhost:8025" "MailHog"
    check_service "curl --silent --output /dev/null ${OBJECT_STORAGE_HOST}/minio/health/live" "MinIO"
    check_service "docker exec redis_cosmopolitan redis-cli ping | grep -q PONG" "Redis"
else
    echo "Skipping service management (assuming services already running)"
fi

# Run pytest with optional test path
echo "Running pytest..."
pytest "$TEST_PATH"

# Cleanup
cleaning_up
