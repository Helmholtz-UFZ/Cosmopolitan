# Logging

All logging goes to both stdout and PostgreSQL via a tag-based system. Tags
categorize log messages by functional area.

## Rules

- Create a module-level logger in every module that logs:
  ```python
  log = logging.getLogger(__name__)
  ```
- Every log call must include `extra={"tag": "<tag>"}` — no exceptions
- Every callback and dynamic layout function must have at least one `log.info()`
  call (except landing page skeleton layouts that just set up the loading spinner)
- Use f-strings for log messages — this is the established pattern
- Use the correct log level (see below)

## Log Levels

| Level     | Use for                                             |
| --------- | --------------------------------------------------- |
| `debug`   | Trace details, variable values, internal state      |
| `info`    | User actions, workflow steps, callback entry points |
| `warning` | Recoverable issues, unexpected but handled states   |
| `error`   | Failures, unhandled exceptions, broken invariants   |

## Tags

Tags are a fixed set validated at handler initialization. Use exactly these values:

| Category | Tags                                                                    |
| -------- | ----------------------------------------------------------------------- |
| Core     | `webserver`, `worker`, `scheduler`                                      |
| User     | `job_submission`, `frontend`                                            |
| System   | `time_io`, `database`, `object_storage`, `email_service`, `maintenance` |
| Fallback | `unknown`                                                               |

Pick the tag that best describes the functional area. Frontend callbacks use
`frontend`. Job creation/submission flows use `job_submission`.

## Examples

### Do

```python
import logging

log = logging.getLogger(__name__)

def load_content(job_id):
    log.info(f"Loading content for job {job_id}", extra={"tag": "frontend"})
    ...
    log.debug(f"Job status: {job.status}", extra={"tag": "frontend"})
```

### Don't

```python
# No module logger — uses root logger directly
logging.info("Loading content")  # Missing tag

# Wrong level — routine action logged as warning
logging.warning(f"Loading results for {job_id}", extra={"tag": "frontend"})
```

## Notes

- The `PostgreSQLHandler` in `cosmopolitan_app/logger.py` writes logs to a `logs`
  table with columns: timestamp, pid, level, module, message, tag
- Handler default tag is set at init time (e.g., `"webserver"` for the web process,
  `"worker"` for Celery workers) — per-call `extra={"tag": ...}` overrides it
- `ExcludeSubmodulesFilter` suppresses noisy third-party loggers (matplotlib, PIL,
  rasterio, etc.)
