# Run and Fix Testing

Systematic guide for running the test suite and diagnosing failures.

## Prerequisites

- Docker is running
- You are in the project root (`/home/andersj/git/cosmopolitan`)
- Read `docs/conventions/testing.md` first

## Steps

1. **Run the full test suite** — `./run_pytest.sh`
   If services are already running: `./run_pytest.sh --no-services`
   To run a single file: `./run_pytest.sh test/test_e2e.py`
   With visible browser: `./run_pytest.sh --headed test/test_e2e.py`
   With local smp: `./run_pytest.sh --local-smp test/test_smp_assumptions.py`

2. **Read the failure output** — identify which test failed and the error type:
   - `AssertionError` — test expectation not met
   - `playwright._impl._errors.TimeoutError` — Playwright timed out waiting for element/condition
   - `ConnectionRefusedError` / `OperationalError` — service not running
   - `pytest.exit(...)` in conftest — prerequisite check failed

3. **For port-already-allocated / service startup failures**:
   1. Run `docker compose down` in the current project directory first — leftover
      containers from a previous test run or `dev_up.sh` are the most common cause.
   2. If the error persists after step 1, tell the user which port is blocked. A
      sibling project (cosmonaut, etc.) may be running in parallel and only the
      user knows which is safe to stop.

4. **For service connection failures** — check Docker:
   - `docker ps` to verify containers are running
   - `docker logs postgres_cosmopolitan` (or redis, minio) for service logs
   - Verify `.env` is `env_test_local` (not a production env file)

4. **For Playwright/E2E failures** — check `test/artifacts/` directory:
   - Screenshots show the browser state at failure time
   - HTML snapshots show the rendered DOM
   - Console logs show browser console messages
   - Server logs show Python server-side errors
   - Worker logs show Celery worker output
   - Traces can be viewed with `npx playwright show-trace test/artifacts/<test>/trace.zip`

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
- `test/artifacts/` directory has no new failure artifacts from this run
