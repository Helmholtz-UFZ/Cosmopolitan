#!/bin/bash

set -e

# Test containers get their own names and compose project, so a test run never stops,
# removes or reuses a dev-stack container (postgres_cosmopolitan & co.).
export COMPOSE_PROJECT_NAME=cosmopolitan_test
export POSTGRES_CONTAINER_NAME=postgres_cosmopolitan_test
export OBJECT_STORAGE_CONTAINER_NAME=object_storage_cosmopolitan_test
export REDIS_CONTAINER_NAME=redis_cosmopolitan_test

trap cleaning_up EXIT

# Cleanup function - restores environment and stops services
cleaning_up() {
    # Restore original .env
    if [ -f .env.bak ]; then
        mv .env.bak .env
    fi

    # COMPOSE_PROJECT_NAME scopes this to the test project; the dev stack is untouched
    docker compose down >/dev/null 2>&1 || true
}

# Service health check with retry logic
check_service() {
    local check_command="$1"
    local service_name="$2"
    local max_retries=10
    local retry_count=0

    until eval "$check_command"; do
        if [ $retry_count -ge $max_retries ]; then
            echo "FAIL: ${service_name} did not start after ${max_retries} attempts"
            cleaning_up
            exit 1
        fi
        sleep 1
        retry_count=$((retry_count + 1))
    done
    echo "  ${service_name} ready"
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
    echo "  -v, --verbose     Show full pytest output (default: minimal, logs go to artifacts)"
    echo "  -h, --help        Show this help message"
    echo ""
    echo "Containers: test services run as postgres_cosmopolitan_test, redis_cosmopolitan_test"
    echo "  and object_storage_cosmopolitan_test (compose project cosmopolitan_test). Cleanup"
    echo "  touches only these; the dev stack (postgres_cosmopolitan & co.) is never stopped."
    echo "  Host ports are shared with the dev stack: stop it first or the start fails."
    echo ""
    echo "Environment:"
    echo "  COSMO_ECOSYSTEM_PATH  Path to a local cosmo-ecosystem checkout. When set, the"
    echo "                    script runs 'uv sync --frozen' (the pinned tag), then"
    echo "                    'uv pip install --editable \$COSMO_ECOSYSTEM_PATH' over it,"
    echo "                    and runs pytest with 'uv run --no-sync' (UV_NO_SYNC=1 for"
    echo "                    nested uv runs such as the test worker) so the overlay stays."
    echo "                    Unset: the pinned framework from uv.lock is used as is."
    echo "                    See cosmo-ecosystem docs/conventions/cross_repo_development.md."
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
    echo "  COSMO_ECOSYSTEM_PATH=../cosmo-ecosystem ./run_pytest.sh # Local framework"
    echo ""
    echo "Artifacts (on failure): screenshots, traces, HTML in test/artifacts/"
    echo "Full pytest output: test/artifacts/pytest_output.log"
    echo "View traces: npx playwright show-trace test/artifacts/<test-name>/trace.zip"
    exit 0
}

# Parse command line arguments
START_SERVICES=1
HEADED=false
LOCAL_SMP=false
ARTIFACTS=true
KEEP_ARTIFACTS=false
VERBOSE=false
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
    -v | --verbose)
        VERBOSE=true
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

# Overlay a local framework checkout (see --help). The variable lives only in the
# caller's shell, so nothing committed knows where the checkout is.
UV_RUN="uv run"
if [ -n "${COSMO_ECOSYSTEM_PATH:-}" ]; then
    if [ ! -d "$COSMO_ECOSYSTEM_PATH" ]; then
        echo "Error: COSMO_ECOSYSTEM_PATH=$COSMO_ECOSYSTEM_PATH is not a directory."
        exit 1
    fi
    echo "Overlaying cosmo-ecosystem from ${COSMO_ECOSYSTEM_PATH}"
    uv sync --frozen --quiet
    # --python: `uv pip` would otherwise install into an activated $VIRTUAL_ENV
    # instead of the project environment that `uv sync` and `uv run` use.
    uv pip install --quiet --python "${UV_PROJECT_ENVIRONMENT:-.venv}" \
        --editable "$COSMO_ECOSYSTEM_PATH"
    # A plain `uv run` re-syncs to uv.lock and silently puts the pinned tag back.
    UV_RUN="uv run --no-sync"
    # The same for every nested `uv run`, such as the Celery worker conftest starts.
    export UV_NO_SYNC=1
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

    # Start services (quiet output)
    echo "Starting services: postgres, object-storage, redis"
    docker compose up postgres object-storage redis -d --quiet-pull

    # Wait for services with retry logic
    check_service "docker exec $POSTGRES_CONTAINER_NAME pg_isready -q 2>/dev/null" "PostgreSQL"
    # The compose healthcheck owns the server-specific probe; this only reads its verdict.
    check_service "docker inspect -f '{{.State.Health.Status}}' $OBJECT_STORAGE_CONTAINER_NAME 2>/dev/null | grep -qx healthy" "Object storage"
    check_service "docker exec $REDIS_CONTAINER_NAME redis-cli ping 2>/dev/null | grep -q PONG" "Redis"
else
    echo "Skipping service management (assuming services already running)"
fi

# Clear previous artifacts unless --keep-artifacts is set
if [ "$KEEP_ARTIFACTS" = false ] && [ -d test/artifacts ]; then
    rm -rf test/artifacts/*
fi
mkdir -p test/artifacts

# Build pytest command dynamically based on flags
PYTEST_CMD="$UV_RUN pytest"

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

# Run pytest — output goes to temp file, moved into artifacts after Playwright is done.
# Playwright cleans --output dir when all tests pass, so writing there during the run
# would lose the log.
TMP_LOG=$(mktemp)
LOG_FILE="test/artifacts/pytest_output.log"

set +e
if [ "$VERBOSE" = true ]; then
    echo "Running: $PYTEST_CMD"
    bash -c "$PYTEST_CMD" 2>&1 | tee "$TMP_LOG"
    PYTEST_EXIT=${PIPESTATUS[0]}
else
    echo "Running tests (logs: $LOG_FILE) ..."
    bash -c "$PYTEST_CMD" > "$TMP_LOG" 2>&1
    PYTEST_EXIT=$?
fi

mkdir -p test/artifacts
mv "$TMP_LOG" "$LOG_FILE"

if [ "$VERBOSE" = false ]; then
    echo ""
    grep -E "^(FAILED|ERROR|=)" "$LOG_FILE" | tail -20 || true
    echo "Full output: $LOG_FILE"
fi
exit $PYTEST_EXIT
