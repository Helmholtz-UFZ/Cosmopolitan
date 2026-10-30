#!/bin/bash

set -e

# Every worktree gets its own test stack, so several worktrees (and the sister repos)
# can run their suites at the same time. The compose project, and with it the
# container names and volumes, carries a short hash of this directory's absolute
# path: stable for one worktree, so a rerun finds and clears a crashed run's
# leftovers, and different for every other worktree, so a run only ever stops what
# it started. The dev stack (postgres_cosmopolitan & co.) is a different project and
# is never touched.
STACK_ID=$(pwd -P | sha256sum | cut -c1-8)
export COMPOSE_PROJECT_NAME="cosmopolitan_test_${STACK_ID}"
export POSTGRES_CONTAINER_NAME="postgres_${COMPOSE_PROJECT_NAME}"
export OBJECT_STORAGE_CONTAINER_NAME="object_storage_${COMPOSE_PROJECT_NAME}"
export REDIS_CONTAINER_NAME="redis_${COMPOSE_PROJECT_NAME}"

trap cleaning_up EXIT

# Cleanup function - restores environment and stops services
cleaning_up() {
    # Restore original .env
    if [ -f .env.bak ]; then
        mv .env.bak .env
    fi

    # COMPOSE_PROJECT_NAME scopes this to this run's project; the dev stack and other
    # worktrees' stacks are untouched. -v: the redis_data volume would otherwise stay.
    if [ "$START_SERVICES" -eq 1 ]; then
        docker compose down -v >/dev/null 2>&1 || true
    fi
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
    echo "Containers: test services run as compose project ${COMPOSE_PROJECT_NAME}"
    echo "  (one per worktree) on free host ports picked at start, so worktrees can run"
    echo "  their suites in parallel. Cleanup touches only this project; the dev stack"
    echo "  (postgres_cosmopolitan & co.) is never stopped. With --no-services the ports"
    echo "  from env_test_local apply."
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

if [ "$START_SERVICES" -eq 1 ]; then
    # Ask the OS for free host ports instead of env_test_local's fixed slot, which
    # another worktree's test stack may hold. All five sockets are open at once, so
    # the ports are distinct. Between closing them here and compose binding them
    # another process could take one; that race is accepted, compose then fails
    # loudly with "port is already allocated".
    read -r FLASK POSTGRES REDIS OBJECT_STORAGE OBJECT_STORAGE_CONSOLE < <(python3 -c '
import socket
socks = [socket.socket() for _ in range(5)]
for s in socks:
    s.bind(("localhost", 0))
print(*(s.getsockname()[1] for s in socks))
')
    # Appended, so these win over env_test_local's values in the same file
    # (python-dotenv and compose both take the last assignment of a key). The suite
    # runs on the host, so the app-facing port and the published host port are the
    # same number. FLASK_PORT is where the e2e Dash server binds.
    cat >>.env <<EOF_PORTS

### Per-run ports, written by run_pytest.sh ###
FLASK_PORT=${FLASK}
FLASK_HOST_PORT=${FLASK}
POSTGRES_PORT="${POSTGRES}"
POSTGRES_HOST_PORT=${POSTGRES}
REDIS_PORT="${REDIS}"
REDIS_HOST_PORT=${REDIS}
OBJECT_STORAGE_HOST="http://localhost:${OBJECT_STORAGE}"
OBJECT_STORAGE_HOST_PORT=${OBJECT_STORAGE}
OBJECT_STORAGE_CONSOLE_HOST_PORT=${OBJECT_STORAGE_CONSOLE}
EOF_PORTS
    echo "Compose project: ${COMPOSE_PROJECT_NAME}"
    echo "Ports: flask ${FLASK}, postgres ${POSTGRES}, redis ${REDIS}," \
        "object storage ${OBJECT_STORAGE} (console ${OBJECT_STORAGE_CONSOLE})"

    # Clear leftovers of a crashed earlier run in this worktree (this project only)
    docker compose down -v 2>/dev/null || true

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
