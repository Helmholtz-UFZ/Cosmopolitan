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

## Notes

- The `PostgreSQLHandler` in `cosmopolitan_app/logger.py` writes logs to a `logs`
  table with columns: timestamp, pid, level, module, message
- `ExcludeSubmodulesFilter` suppresses noisy third-party loggers (matplotlib, PIL,
  rasterio, etc.)
