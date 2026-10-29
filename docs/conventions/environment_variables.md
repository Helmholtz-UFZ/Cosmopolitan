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
- **Postgres and object storage**: `environment:` block with `${VAR}` interpolation
  maps project variables to the service's expected names (e.g.
  `RUSTFS_ACCESS_KEY: ${OBJECT_STORAGE_ACCESS_KEY}`).
- **Production Dockerfiles** (`docker/prod.Dockerfile`, `docker/worker.Dockerfile`):
  `COPY env_prod .env` bakes non-secret vars into the image; the CMD sources
  `.env` before starting the process.
- **`DOCKER_UID` / `DOCKER_GID`**: Used in `docker-compose.yml` via
  `user: "${DOCKER_UID}:${DOCKER_GID}"` for file permission mapping.

## Production Deployment (Kubernetes)

- `deployments/ufz/{prod,stage}/values.yaml` inject env vars via
  `environmentVariables` on both frontend and worker pods. The DB settings
  (`POSTGRES_DB`, `POSTGRES_USER`, ...) are set there, not only in `env_prod`.
- **Stage and prod both use `somweb_prod`** on `postgres.intranet.ufz.de` as
  `somweb_prod_rw`. `somweb_stage` on `postgres-dev` is used by no deployment and
  lags behind `init.sql` (missing tables and columns). A schema change that the
  deployed app needs must land on `somweb_prod` before the deploy; check with
  `./schema_diff.sh postgres.intranet.ufz.de somweb_prod somweb_prod_rw`.
- Secrets are pulled from the K8s Secret `custom-met-cosmopolitan.secrets` using
  `secretKeyRef`. Env var → key:

  | Env var | Secret key |
  |---|---|
  | `POSTGRES_PASSWORD` | `DB_PW` |
  | `EMAIL_PASSWORD` | `EMAIL_PASSWORD` |
  | `OBJECT_STORAGE_SECRET_KEY` | `OBJECT_STORAGE_SECRET_KEY` |
  | `CLUSTER_TOKEN` | `CLUSTER_TOKEN` |

- The Secret is **not** in the repo (no SealedSecret); it is managed in the
  cluster. ArgoCD masks Secret values; read a value via Rancher
  (Storage → Secrets) or `printenv` in a pod terminal.
- Non-secret vars are baked into `env_prod` at image build time (see Docker
  section above).

## Adding a New Env Var — Checklist

1. Add the variable to **all tracked env files** (`env_dev_mock`, `env_dev_prod`,
   `env_prod`, `env_test`, `env_test_local`).
2. Add it to the `env_vars` list in `cosmopolitan_app/config.py`.
3. Add a `getenv()` call and module-level constant in `config.py`.
4. If it is a secret in production, add a `secretKeyRef` to both `values.yaml`
   files and have the key added to the cluster Secret
   `custom-met-cosmopolitan.secrets`.
5. If `env_prod` will not have the value at build time, add a placeholder line
   to `additional_lines_map` in `test/test_env.py`.
6. Run `./run_pytest.sh` — `test_env.py` will catch any missing vars.

## Notes

- `load_dotenv()` is called once at the top of `config.py`
- `JOB_WORK_DIR_TEMPLATE` is derived from `WEB_WORK_DIR` — derived constants also
  belong in `config.py`
