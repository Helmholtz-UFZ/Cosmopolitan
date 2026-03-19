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

## Docker

How env vars reach containers (see `docker-compose.yml`):

- **App and worker containers**: `env_file: .env` passes all variables from the
  active `.env` file.
- **Postgres and MinIO**: `environment:` block with `${VAR}` interpolation maps
  project variables to the service's expected names (e.g.
  `MINIO_ROOT_USER: ${OBJECT_STORAGE_ACCESS_KEY}`).
- **Production Dockerfiles** (`docker/prod.Dockerfile`, `docker/worker.Dockerfile`):
  `COPY env_prod .env` bakes non-secret vars into the image; the CMD sources
  `.env` before starting the process.
- **`DOCKER_UID` / `DOCKER_GID`**: Used in `docker-compose.yml` via
  `user: "${DOCKER_UID}:${DOCKER_GID}"` for file permission mapping.

## Production Deployment (Kubernetes)

- `deployment/ufz/prod/values.yaml` injects env vars via `environmentVariables`
  on both frontend and worker pods.
- Secrets (`EMAIL_PASSWORD`, `OBJECT_STORAGE_SECRET_KEY`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`)
  are pulled from the K8s Secret `app.secrets` using `secretKeyRef`.
- The Secret is sealed with Bitnami SealedSecrets
  (`deployment/ufz/prod/app.sealedsecret.yaml`).
- Non-secret vars are baked into `env_prod` at image build time (see Docker
  section above).

## Adding a New Env Var — Checklist

1. Add the variable to **all tracked env files** (`env_dev_mock`, `env_dev_prod`,
   `env_prod`, `env_test`, `env_test_local`).
2. Add it to the `env_vars` list in `cosmopolitan_app/config.py`.
3. Add a `getenv()` call and module-level constant in `config.py`.
4. If it is a secret in production, add it to `values.yaml` and
   `app.sealedsecret.yaml`.
5. If `env_prod` will not have the value at build time, add a placeholder line
   to `additional_lines_map` in `test/test_env.py`.
6. Run `./run_pytest.sh` — `test_env.py` will catch any missing vars.

## Notes

- `load_dotenv()` is called once at the top of `config.py`
- `JOB_WORK_DIR_TEMPLATE` is derived from `WEB_WORK_DIR` — derived constants also
  belong in `config.py`
