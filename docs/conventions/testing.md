# Testing

All tests live in `test/` and run against real services via Docker. Tests are
executed with `run_pytest.sh` or directly with `pytest`.

## Rules

- All tests go in `test/` (flat directory, no subdirectories)
- Use constants from `cosmopolitan_app/constants.py` for element IDs in Selenium
  selectors — never literal ID strings
- All imports at top level — except `test_postgres_manager.py` which deliberately
  imports inside the test function (documented exception)
- When adding a required env var, update `test_env.py`'s `additional_lines_map` for
  `env_prod`

## Test Types

### E2E tests (`test_app.py`)

- Use `dash_duo` fixture (Selenium + Dash test server)
- Require all services: Postgres, Redis, MinIO, MailHog, Celery worker
- Test full user workflows through the browser
- Screenshots and HTML snapshots are captured on failure (saved to `test_failures/`)

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

# Specific test file
./run_pytest.sh test/test_app.py

# Services already running (faster iteration)
./run_pytest.sh --no-services test/test_app.py
```

`run_pytest.sh`:
1. Backs up `.env`, copies `env_test_local` to `.env`
2. Starts Docker services (Postgres, MailHog, MinIO, Redis)
3. Waits for all services to be ready
4. Runs `pytest`
5. Restores original `.env` and stops services

## Fixtures (`conftest.py`)

- Module-level setup verifies all services are reachable before any tests run
- Safety check: exits if credentials aren't test values (prevents running against
  production)
- `celery_worker` — starts a real Celery worker subprocess, terminates on teardown
- `crns_file_path` / `pred_file_paths` — copies test data files locally, cleans up
  after
- `logger` — configured logger with suppressed third-party noise

## Examples

### Do

```python
from cosmopolitan_app.constants import SUBMIT_JOB_ID

def test_something(dash_duo):
    dash_duo.wait_for_element(f"#{SUBMIT_JOB_ID}", timeout=10).click()
```

### Don't

```python
def test_something(dash_duo):
    dash_duo.wait_for_element("#submit_job_button", timeout=10).click()
```

## Notes

- `check_all_errors(dash_duo)` is the standard post-action verification in E2E tests
  — checks console errors, JS errors, and broken images
- `scroll_to_element_and_click()` handles scrolling and retries for intercepted clicks
- `conftest.py` inline imports from `kombu` are at top level, not inside functions
