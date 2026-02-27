# Error Handling

Custom exceptions and a global error modal provide consistent user-facing error
messages across all callbacks.

## Rules

- Define custom exceptions in `cosmopolitan_app/error_handling.py`
- Give exceptions a `job_id` attribute when the error relates to a specific job
- Register every user-facing exception in `error_responds_dict` with a (title, message)
  tuple
- Let the global `handle_error` show the error modal — individual callbacks do not
  catch exceptions that are already in `error_responds_dict`
- Only catch specific exceptions in callbacks when you need to handle them differently
  (e.g., `PreventUpdate`, validation feedback)
- Never use bare `except Exception` — always catch specific types. When a catch-all
  is genuinely necessary (e.g., top-level task handlers, email-must-not-crash guards),
  add an inline comment explaining why:
  ```python
  except Exception as e:  # catch-all: computation can fail unpredictably; must log and mark FAILED
  ```
- `dict.get()` is acceptable for registry/dispatch lookups (like `error_responds_dict`)
  and external API responses where keys are genuinely optional — add a brief comment.
  Never use `dict.get()` defensively on internal data structures where keys are guaranteed

## Exception Pattern

```python
class MyCustomError(Exception):
    """Raised when <specific condition>."""

    def __init__(self, job_id):
        self.job_id = job_id
        super().__init__(f"Description for {job_id}.")
```

Register in `error_responds_dict`:

```python
error_responds_dict = {
    ...
    MyCustomError: (
        "Short Title",
        "User-friendly message about '{job_id}'.",
    ),
}
```

The `{job_id}` placeholder is formatted automatically by `handle_error`.

## Error Modal

The global error modal is defined in `error_handling.py` and included in the app
layout via `layouts.app_layout()`. It uses three component IDs from `constants.py`:

- `ERROR_MODAL_ID` — modal visibility
- `ERROR_TITLE_ID` — modal header
- `ERROR_MESSAGE_ID` — modal body

The `handle_error` function uses `set_props()` to open the modal. Callbacks that
need to control the error modal directly (e.g., clearing it) use standard
Output targeting these IDs.

## Examples

### Do

```python
# In a callback — let the global handler deal with it
def load_results(job_id):
    job = Job(job_id)
    if job.status != "COMPLETED":
        raise NotFinishedException(job_id)
```

### Don't

```python
# Don't catch and re-display manually
def load_results(job_id):
    try:
        job = Job(job_id)
    except Exception as e:
        return "error", str(e), True  # Don't do this
```

## Notes

- `handle_error` sends an email for unexpected errors (not in the known list)
- Use `USE_ERROR_MESSAGE` sentinel in `error_responds_dict` when the exception's
  own `str()` message should be shown to the user (e.g., `FileValidationError`)
