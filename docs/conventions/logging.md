# Logging

All logging goes to both stdout and PostgreSQL.

## Rules

- Create a module-level logger in every module that logs, **after all imports**:
  ```python
  log = logging.getLogger(__name__)
  ```
- Every callback and dynamic layout function must have at least one `log.info()`
  call (except landing page skeleton layouts that just set up the loading spinner)
- Use f-strings for log messages — this is the established pattern
- Use the correct log level (see below)
- **DO NOT use:** `extra={"tag": "..."}` — this is a legacy pattern, do not copy

## Log Levels

| Level     | Use for                                             |
| --------- | --------------------------------------------------- |
| `debug`   | Trace details, variable values, internal state      |
| `info`    | User actions, workflow steps, callback entry points |
| `warning` | Recoverable issues, unexpected but handled states   |
| `error`   | Failures, unhandled exceptions, broken invariants   |

## Examples

### Do

```python
import logging

from cosmopolitan_app.config import SOME_SETTING

log = logging.getLogger(__name__)

def load_content(job_id):
    log.info(f"Loading content for job {job_id}")
    ...
    log.debug(f"Job status: {job.status}")
```

### Don't

```python
# No module logger — uses root logger directly
logging.info("Loading content")

# Wrong level — routine action logged as warning
logging.warning(f"Loading results for {job_id}")
```

## Logs in Test Artifacts

When a Playwright test fails, the `page` fixture in `test/conftest.py` captures all
Python log output (including Dash callbacks, werkzeug requests, and application logs)
into `test/artifacts/<test-dir>/server.log`. This uses a `logging.Handler` that
collects records during the test and writes them on failure.

This means every `log.info(...)`, `log.error(...)`, etc. from your application code
is available for post-mortem debugging without re-running the test.

See [Testing conventions — Artifacts](testing.md#artifacts) for the full artifact
reference.

## Celery and the Root Logger

The web process runs a Celery Beat thread (`app.py`). By default Celery hijacks the
root logger on startup, replacing all handlers with its own stdout-only handler. This
silently drops the PostgreSQL handler.

**Always keep this in `CeleryConfig`:**

```python
worker_hijack_root_logger = False
```

Without it, logs appear in the container stdout (in Celery format) but never reach
the database, and the `/logs` page shows nothing.

## Notes

- The `PostgreSQLHandler` in `cosmopolitan_app/logger.py` writes logs to a `logs`
  table with columns: timestamp, pid, level, module, message
- `ExcludeSubmodulesFilter` suppresses noisy third-party loggers (matplotlib, PIL,
  rasterio, etc.)
