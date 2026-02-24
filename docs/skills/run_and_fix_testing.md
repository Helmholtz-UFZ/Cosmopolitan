# Run and Fix Testing

Systematic guide for running the test suite and diagnosing failures.

## Prerequisites

- Docker is running
- You are in the project root (`/home/andersj/git/cosmopolitan`)
- Read `docs/conventions/testing.md` first

## Steps

1. **Run the full test suite** — `./run_pytest.sh`
   If services are already running: `./run_pytest.sh --no-services`
   To run a single file: `./run_pytest.sh test/test_app.py`

2. **Read the failure output** — identify which test failed and the error type:
   - `AssertionError` — test expectation not met
   - `TimeoutException` / `NoSuchElementException` — Selenium can't find element
   - `ConnectionRefusedError` / `OperationalError` — service not running
   - `pytest.exit(...)` in conftest — prerequisite check failed

3. **For service connection failures** — check Docker:
   - `docker ps` to verify containers are running
   - `docker logs postgres_cosmopolitan` (or redis, minio, mailhog) for service logs
   - Verify `.env` is `env_test_local` (not a production env file)

4. **For Selenium/E2E failures** — check `test_failures/` directory:
   - Screenshots show the browser state at failure time
   - HTML snapshots show the rendered DOM
   - Check for error modals visible in the screenshot
   - Check console errors in the failure output

5. **For assertion failures in module tests** — read the test and the module under
   test. Common causes:
   - Database state from a previous test (check for missing `autouse` fixture cleanup)
   - Changed API in `soil_moisture_prediction` library
   - Env var missing or wrong value

6. **Fix the issue** — apply the fix in the source code or test code

7. **Re-run only the failing test** — `./run_pytest.sh --no-services test/test_file.py`

8. **Run the full suite once more** — `./run_pytest.sh --no-services` to verify no
   regressions

## Verification

- All tests pass with exit code 0
- No new warnings introduced
- `test_failures/` directory has no new screenshots from this run
