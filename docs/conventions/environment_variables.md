# Environment Variables

All environment variables are loaded once in `cosmopolitan_app/config.py` and
imported as Python constants by the rest of the codebase.

## Rules

- All env vars are loaded in `config.py` — nowhere else
- Use the project's `getenv()` function — never `os.getenv()` or `os.environ`
  directly. `getenv()` raises `ValueError` on missing variables, catching
  misconfiguration at startup
- Every env var is required — there are no optional variables
- Add new env vars to the `env_vars` list in `config.py` (used by `test_env.py`)
- Import config values as Python constants:
  ```python
  from cosmopolitan_app.config import POSTGRES_HOST_NAME
  ```
- Never read env vars at runtime in other modules

## Env File Hierarchy

| File | Purpose | Tracked |
|------|---------|---------|
| `env_dev_mock` | Local Docker dev with mock services | Yes |
| `env_test` | CI pipeline testing | Yes |
| `env_test_local` | Local test runs | Yes |
| `env_dev_prod` | Template for real service access (empty secrets) | Yes |
| `env_dev_prod_priv` | Real credentials (copy of `env_dev_prod`) | **No** |
| `env_dev_stage_priv` | Staging credentials | **No** |
| `env_prod` | Production config (secrets injected at deploy) | Yes |

Tracked env files must never contain real credentials. Files ending in `_priv` are
gitignored and contain actual secrets.

## Examples

### Do

```python
# In config.py — adding a new env var
NEW_SERVICE_URL = getenv("NEW_SERVICE_URL")

# In any other module
from cosmopolitan_app.config import NEW_SERVICE_URL
```

### Don't

```python
# Direct os.getenv in a module other than config.py
url = os.getenv("NEW_SERVICE_URL", "http://default")

# Optional env var with fallback — all vars are required
password = os.getenv("REDIS_PASSWORD", "")
```

## Notes

- `load_dotenv()` is called once at the top of `config.py`
- `JOB_WORK_DIR_TEMPLATE` is derived from `WEB_WORK_DIR` — derived constants also
  belong in `config.py`
- When adding a new env var, update all tracked env files (`env_dev_mock`, `env_test`,
  `env_test_local`, `env_dev_prod`, `env_prod`)
