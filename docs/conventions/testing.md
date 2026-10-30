# Testing

All tests live in `test/` and run against real services via Docker.

## Critical Rules for Running Tests

**ALWAYS run `./run_pytest.sh --help` before your first test execution in a session.**
The help output is the single source of truth for available flags and usage. Do not
guess flags or invent arguments — only use what `--help` shows.

**NEVER run `pytest` or `uv run pytest` directly.** Always use `./run_pytest.sh`.
The script manages `.env` backup/restore, Docker services, and cleanup. Running
pytest directly will use the wrong `.env`, skip service setup, and leave stale state.

**One test stack per worktree.** Every `run_pytest.sh` run brings up its own stack, so
any number of worktrees (of this repo and of COSMONAUT and cosmo-ecosystem) can run
their suites at the same time. See [below](#one-test-stack-per-worktree).

**`--no-services` SKIPS most tests.** It passes `--no-services` to pytest, which
causes `dash_app` and `celery_worker` fixtures to call `pytest.skip()`. All e2e
tests and most module tests will be skipped. Only use it for tests that truly need
no services (`test_env`, `test_smp_assumptions`, `test_documentation`).

**Check artifacts before rerunning.** On failure, `test/artifacts/<test-name>/`
contains screenshots, traces, HTML snapshots, server logs, and worker logs. Read
these first — they usually explain the failure without needing another run. Note
that `run_pytest.sh` clears previous artifacts by default (use `--keep-artifacts`
to preserve them across runs).

## One test stack per worktree

- **Compose project from the worktree.** The project is `cosmopolitan_test_<hash>`,
  where `<hash>` is the first 8 hex digits of the sha256 of the worktree's absolute
  path. Containers are `postgres_<project>`, `object_storage_<project>` and
  `redis_<project>`; volumes carry the project prefix. The same worktree always gets
  the same name, so the `down -v` at the start of a run clears what a crashed earlier
  run left there, and the `down -v` at the end removes only this run's stack.
- **Free ports picked at start.** The script asks the OS for five free TCP ports
  (Flask, Postgres, Redis, object storage API and console) and appends them to the
  run's `.env`, both the app-facing variables (`FLASK_PORT`, `POSTGRES_PORT`,
  `REDIS_PORT`, `OBJECT_STORAGE_HOST`) and the published `*_HOST_PORT`. The last
  assignment of a key wins for python-dotenv and compose, so `env_test_local` keeps
  its slot values. The e2e Dash server and the Celery worker read the same `.env`, so
  they use the run's ports too. A port taken between picking and binding fails loudly
  as "port is already allocated"; rerun.
- **Tests must not leave a different `.env` behind.** `test_env.py` rewrites `.env`
  from fixed env files; its `restored_env` fixture puts the run's `.env` and
  `os.environ` back, or later tests and the worker would talk to the slot ports.
- **Finding a running stack.** The run prints `Compose project: …` and the ports at
  start; `docker ps --filter label=com.docker.compose.project=<project>` shows its
  containers.
- **`--no-services`** picks no ports and tears nothing down: it runs against the
  `env_test_local` values, i.e. a stack you started yourself on the cosmopolitan slot.

The dev stack (`postgres_cosmopolitan` & co.) is a different project and is never
stopped by a test run, and since the test ports are picked free, a running dev stack
no longer gets in the way either. The port slots in
`../cosmo-ecosystem/docs/plan/local-port-allocation.md` apply to dev stacks (and
`--no-services`) only.

`check_parallel_runs.sh` (next to `run_pytest.sh`) is the acceptance check: it
creates a throwaway detached worktree of `HEAD`, runs `run_pytest.sh` on one e2e test
that runs a job through the worker in both worktrees at once, and passes when both
are green and no container or volume of either project is left. Run it after
changing `run_pytest.sh` (commit first: the probe worktree sees only `HEAD`). It is
not a CI job; CI has no parallel worktrees.

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
- Require all services: Postgres, Redis, object storage, Celery worker
- Test full user workflows through the browser
- Reusable helpers in `test/help_functions_tests.py` (3 layers: atomic form actions,
  page navigation, complete setups)

### Module tests (everything else)

Service requirements vary by test:

| Test file | Services needed |
|-----------|----------------|
| `test_postgres_manager.py` | Postgres |
| `test_cleanup.py` | Postgres, object storage |
| `test_update_measurements.py` | Postgres |
| `test_background_job_manager.py` | Redis, Celery worker |
| `test_env.py` | None (reads env files only) |
| `test_smp_assumptions.py` | None (checks data structures only) |
| `test_documentation.py` | None (reads files only) |
| `test_results_page.py` | None (temporary work dir only) |
| `test_job_management_page.py` | None (page registry and link seam only) |

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

**Which artifact to check first:**

| Failure type | Check first |
|---|---|
| Element not found / timeout | `test-failed-1.png` — is the element on screen? |
| Callback race / stuck overlay | `trace.zip` — step through the action timeline |
| JavaScript error | `console.log` — browser-side errors |
| Unexpected app behavior | `server.log` — Dash callback logs and exceptions |
| Background task failure | `worker.log` — Celery worker output and task traces |
| Layout / rendering issue | `page.html` — inspect the DOM structure |

## CI Pipeline

Tests run in GitLab CI. See `.gitlab-ci.yml` for configuration.

All tests must pass in CI before merging.

On failure, CI uploads `test/artifacts/` as a GitLab artifact (7-day retention).
Download from the pipeline job page under "Job artifacts".

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
- `conftest.py` inline imports from `cosmo_ecosystem.object_storage_manager` are inside `pytest_configure` (not at top level) to avoid triggering service connections during collection
