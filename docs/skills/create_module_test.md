# New Module Test

Create a new test file for a module in `cosmopolitan_app/`.

## Prerequisites

- The module under test exists in `cosmopolitan_app/`
- Read `docs/conventions/testing.md` first

## Steps

1. **Create the test file** — `test/test_<module_name>.py`

2. **Add imports** — all at top level:
   ```python
   """Test the <module_name> module."""

   import pytest

   from cosmopolitan_app.<module_name> import <classes_and_functions>
   ```

3. **Determine service dependencies** — does the module need:
   - Postgres? (uses `PostgresManager` or SQLAlchemy)
   - Redis? (uses Celery or `BackgroundJobManager`)
   - MinIO? (uses `ObjectStorageManager`)
   - MailHog? (uses `send_mail`)
   - If none, the test can run without services

4. **Add fixtures for cleanup** — if the test writes to a database or filesystem,
   add an `autouse` fixture to reset state:
   ```python
   @pytest.fixture(autouse=True)
   def reset_state():
       # setup
       yield
       # teardown / cleanup
   ```

5. **Write test functions** — one function per behavior:
   ```python
   def test_<behavior_description>():
       """Test that <expected behavior>."""
       # Arrange
       ...
       # Act
       result = module_function(args)
       # Assert
       assert result == expected
   ```

6. **Use existing fixtures from conftest.py** where applicable:
   - `logger` — for tests that need logging
   - `celery_worker` — for tests that submit Celery tasks
   - `crns_file_path` / `pred_file_paths` — for tests needing test data files

7. **Update the service requirements table** — add your new test file to the table
   in `docs/conventions/testing.md`

## Verification

- Test passes: `./run_pytest.sh --no-services test/test_<module_name>.py`
- Full suite still passes: `./run_pytest.sh --no-services`
- Test file is listed in `docs/conventions/testing.md` service requirements table
