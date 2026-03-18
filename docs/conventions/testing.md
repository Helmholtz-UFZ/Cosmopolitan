# Testing

All tests live in `test/` and run against real services via Docker.

## Critical Rules for Running Tests

**ALWAYS run `./run_pytest.sh --help` before your first test execution in a session.**
The help output is the single source of truth for available flags and usage. Do not
guess flags or invent arguments — only use what `--help` shows.

**NEVER run `pytest` or `uv run pytest` directly.** Always use `./run_pytest.sh`.
The script manages `.env` backup/restore, Docker services, and cleanup. Running
pytest directly will use the wrong `.env`, skip service setup, and leave stale state.

**`--no-services` SKIPS most tests.** It passes `--no-services` to pytest, which
causes `dash_app` and `celery_worker` fixtures to call `pytest.skip()`. All e2e
tests and most module tests will be skipped. Only use it for tests that truly need
no services (`test_env`, `test_smp_assumptions`, `test_documentation_version`).

**Check artifacts before rerunning.** On failure, `test/artifacts/<test-name>/`
contains screenshots, traces, HTML snapshots, server logs, and worker logs. Read
these first — they usually explain the failure without needing another run. Note
that `run_pytest.sh` clears previous artifacts by default (use `--keep-artifacts`
to preserve them across runs).

## Code Rules

- All tests go in `test/` (flat directory, no subdirectories)
- Use constants from `cosmopolitan_app/constants.py` for element IDs in Playwright
  locators — never literal ID strings
- All imports at top level (lazy-loading managers make this safe even for DB/service modules)
- When adding a required env var, update `test_env.py`'s `additional_lines_map` for
  `env_prod`

## Test Types

### E2E tests (`test_e2e.py`)

- Use Playwright via `pytest-playwright` (`page` fixture)
- App served by `dash_app` fixture (werkzeug make_server in background thread)
- Require all services: Postgres, Redis, MinIO, Celery worker
- Test full user workflows through the browser
- Reusable helpers in `test/help_functions_tests.py` (3 layers: atomic form actions,
  page navigation, complete setups)

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
- **Server logs**: Python server-side logs (callbacks, validation errors, file operations)
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
