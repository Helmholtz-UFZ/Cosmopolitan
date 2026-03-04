# Testing

All tests live in `test/` and run against real services via Docker. Tests are
executed with `run_pytest.sh` or directly with `pytest`.

## Rules

- All tests go in `test/` (flat directory, no subdirectories)
- Use constants from `cosmopolitan_app/constants.py` for element IDs in Playwright
  locators — never literal ID strings
- All imports at top level — except `test_postgres_manager.py` which deliberately
  imports inside the test function (documented exception)
- When adding a required env var, update `test_env.py`'s `additional_lines_map` for
  `env_prod`

## Test Types

### E2E tests (`test_e2e.py`)

- Use Playwright via `pytest-playwright` (`page` fixture)
- App served by `dash_app` fixture (werkzeug make_server in background thread)
- Require all services: Postgres, Redis, MinIO, Celery worker
- Test full user workflows through the browser
- Artifacts captured on failure: screenshots, traces, HTML snapshots, console/server/worker logs (saved to `test/artifacts/`)

### Module tests (everything else)

Service requirements vary by test:

| Test file | Services needed |
|-----------|----------------|
| `test_postgres_manager.py` | Postgres |
| `test_update_measurments.py` | Postgres |
| `test_background_job_manager.py` | Redis, Celery worker |
| `test_env.py` | None (reads env files only) |
| `test_smp_assumptions.py` | None (checks data structures only) |
| `test_documentation_version.py` | None (reads files only) |

## Running Tests

```bash
# All tests with full service management
./run_pytest.sh

# Run with visible browser (debugging)
./run_pytest.sh --headed

# Specific test file
./run_pytest.sh test/test_e2e.py

# Services already running (faster iteration)
./run_pytest.sh --no-services test/test_e2e.py

# Disable artifact capture
./run_pytest.sh --no-artifacts

# Use local soil-moisture-prediction repo (sibling directory)
./run_pytest.sh --local-smp test/test_smp_assumptions.py
```

`run_pytest.sh`:
1. Backs up `.env`, copies `env_test_local` to `.env`
2. Starts Docker services (Postgres, MinIO, Redis)
3. Waits for all services to be healthy (10 retry limit)
4. Runs `uv run pytest` with Playwright artifact flags
5. Restores `.env`, stops services

## Fixtures (`conftest.py`)

- `pytest_configure()` verifies all services are reachable before any tests run (gated by `--no-services`)
- Safety check: exits if credentials aren't test values (prevents running against production)
- `dash_app` (session) — starts the Dash app via werkzeug make_server in a background thread, polls until responsive, shuts down cleanly
- `page` (function) — wraps pytest-playwright's page fixture; captures HTML, console logs, server logs, and worker logs on failure
- `celery_worker` (session) — starts a real Celery worker subprocess with log capture, terminates on teardown
- `crns_file_path` / `pred_file_paths` (session) — copies test data files to temp dir
- `logger` — configured logger with suppressed third-party noise

## Artifacts

Playwright artifacts are stored in `test/artifacts/` and include:
- **Screenshots** (`--screenshot only-on-failure`): browser screenshots on test failure
- **Traces** (`--tracing retain-on-failure`): Playwright traces viewable with `npx playwright show-trace`
- **HTML snapshots**: rendered DOM at failure time
- **Console logs**: browser console messages
- **Server logs**: Python server-side logs
- **Worker logs**: Celery worker output

## Examples

### Do

```python
from playwright.sync_api import expect

from cosmopolitan_app.constants import SUBMIT_JOB_BUTTON_SUBMISSION_ID

def test_something(page, dash_app):
    page.goto(f"http://localhost:{PORT}/")
    page.locator(f"#{SUBMIT_JOB_BUTTON_SUBMISSION_ID}").click()
    expect(page.locator(f"#{SUBMIT_JOB_BUTTON_SUBMISSION_ID}")).to_be_visible()
```

### Don't

```python
def test_something(page, dash_app):
    page.locator("#submit_job_button").click()
```

## Notes

- `check_all_errors(page)` in `test/help_functions_tests.py` is the standard post-action verification — checks console errors, JS errors, and broken images
- Use `locator.scroll_into_view_if_needed()` before clicking elements that may be off-screen
- `conftest.py` inline imports from `object_storage_manager` are inside `pytest_configure` (not at top level) to avoid triggering service connections during collection
