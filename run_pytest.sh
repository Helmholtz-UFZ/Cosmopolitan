#!/bin/bash

set -e

trap cleaning_up EXIT

# Cleanup function - restores environment and stops services
cleaning_up() {
    echo "Cleaning up..."

    # Restore original .env
    if [ -f .env.bak ]; then
        mv .env.bak .env
    fi

    # Stop and remove containers
    docker stop postgres_cosmopolitan minio_cosmopolitan redis_cosmopolitan 2>/dev/null || true
    docker rm postgres_cosmopolitan minio_cosmopolitan redis_cosmopolitan 2>/dev/null || true
    docker compose down 2>/dev/null || true

    echo "Cleanup complete"
}

# Service health check with retry logic
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
        echo "Waiting for ${service_name}... (${retry_count}/${max_retries})"
        sleep 1
        retry_count=$((retry_count + 1))
    done
    echo "${service_name} is ready"
}

# Help message
show_help() {
    echo "Usage: ./run_pytest.sh [OPTIONS] [TEST_PATH]"
    echo ""
    echo "The ONLY way to run tests. Do NOT run pytest directly."
    echo ""
    echo "This script manages the test environment: backs up .env, starts Docker"
    echo "services, runs pytest, then restores .env and stops services on exit."
    echo ""
    echo "Options:"
    echo "  --headed          Run browser tests with visible browser (for debugging)"
    echo "  --local-smp       Use local ../soil-moisture-prediction instead of PyPI version"
    echo "  --no-services     Skip Docker service start/stop (services must already be running)."
    echo "                    WARNING: also passes --no-services to pytest, which causes"
    echo "                    dash_app and celery_worker fixtures to SKIP. This means ALL"
    echo "                    e2e tests and most module tests will be SKIPPED. Only useful"
    echo "                    for tests that need no services (test_env, test_smp_assumptions,"
    echo "                    test_documentation_version)."
    echo "  --no-artifacts    Disable Playwright artifact capture (screenshots, traces)"
    echo "  --keep-artifacts  Keep artifacts from previous runs (default: clear on each run)"
    echo "  -h, --help        Show this help message"
    echo ""
    echo "Test Selection:"
    echo "  [TEST_PATH]       Specific test file, directory, or pytest node ID (optional)."
    echo "                    Passed directly to pytest as the last argument."
    echo "                    Examples: test/test_e2e.py"
    echo "                              test/test_e2e.py::test_full_procedure"
    echo ""
    echo "Note: This script does NOT support arbitrary pytest flags like -k, -x, etc."
    echo "Only the options listed above are supported."
    echo ""
    echo "Examples:"
    echo "  ./run_pytest.sh                                        # Run all tests"
    echo "  ./run_pytest.sh --headed                               # Visible browser"
    echo "  ./run_pytest.sh test/test_e2e.py                       # Specific file"
    echo "  ./run_pytest.sh test/test_e2e.py::test_full_procedure  # Specific test"
    echo "  ./run_pytest.sh --keep-artifacts test/test_e2e.py      # Keep old artifacts"
    echo "  ./run_pytest.sh --local-smp test/test_e2e.py           # Local smp repo"
    echo "  ./run_pytest.sh --no-services test/test_env.py         # No-service tests only"
    echo ""
    echo "Artifacts (on failure): screenshots, traces, HTML, logs in test/artifacts/"
    echo "View traces: npx playwright show-trace test/artifacts/<test-name>/trace.zip"
    exit 0
}

# Parse command line arguments
START_SERVICES=1
HEADED=false
LOCAL_SMP=false
ARTIFACTS=true
KEEP_ARTIFACTS=false
TEST_PATH=""

while [[ $# -gt 0 ]]; do
    case $1 in
    --headed)
        HEADED=true
        shift
        ;;
    --local-smp)
        LOCAL_SMP=true
        shift
        ;;
    --no-services)
        START_SERVICES=0
        shift
        ;;
    --no-artifacts)
        ARTIFACTS=false
        shift
        ;;
    --keep-artifacts)
        KEEP_ARTIFACTS=true
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

# Validate --local-smp
if [ "$LOCAL_SMP" = true ]; then
    if [ ! -d "../soil-moisture-prediction" ]; then
        echo "Error: ../soil-moisture-prediction directory not found."
        echo "Clone soil-moisture-prediction as a sibling directory first."
        exit 1
    fi
    SMP_PATH="$(cd ../soil-moisture-prediction && pwd)"
    export PYTHONPATH="${SMP_PATH}:${PYTHONPATH:-}"
    echo "Using local soil-moisture-prediction from ${SMP_PATH}"
fi

# Backup existing .env
if [ -f .env ]; then
    mv .env .env.bak
fi

# Use test environment configuration
cp env_test_local .env

# Source for environment variables
source .env

if [ "$START_SERVICES" -eq 1 ]; then
    # Clean up existing containers
    docker compose down 2>/dev/null || true

    # Start services
    echo "Starting services: postgres, minio, redis"
    docker compose up postgres minio redis -d

    # Wait for services with retry logic
    check_service "docker exec postgres_cosmopolitan pg_isready -q 2>/dev/null" "PostgreSQL"
    check_service "docker exec minio_cosmopolitan curl -sf http://localhost:9000/minio/health/ready >/dev/null 2>&1" "MinIO"
    check_service "docker exec redis_cosmopolitan redis-cli ping 2>/dev/null | grep -q PONG" "Redis"
else
    echo "Skipping service management (assuming services already running)"
fi

# Clear previous artifacts unless --keep-artifacts is set
if [ "$KEEP_ARTIFACTS" = false ] && [ -d test/artifacts ]; then
    echo "Clearing previous artifacts..."
    rm -rf test/artifacts/*
fi

# Build pytest command dynamically based on flags
PYTEST_CMD="uv run pytest"

# Add artifact flags (enabled by default)
if [ "$ARTIFACTS" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --screenshot only-on-failure --tracing retain-on-failure --output test/artifacts"
fi

# Add --no-services flag if needed
if [ "$START_SERVICES" -eq 0 ]; then
    PYTEST_CMD="$PYTEST_CMD --no-services"
fi

# Add --headed flag if needed
if [ "$HEADED" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --headed"
fi

# Add test path if specified
if [ -n "$TEST_PATH" ]; then
    PYTEST_CMD="$PYTEST_CMD $TEST_PATH"
fi

# Run pytest with all accumulated flags
echo "Running: $PYTEST_CMD"
$PYTEST_CMD
