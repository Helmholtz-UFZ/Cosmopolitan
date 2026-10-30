# COSMOPOLITAN — Architecture Overview

Quick-reference map of the codebase for new sessions and new contributors. All application
code lives under [`cosmopolitan_app/`](../cosmopolitan_app/).

## Stack

Dash (Plotly) on a Flask server, Celery + Redis for background work, PostgreSQL/PostGIS for
spatial data, S3 object storage via rclone (UFZ S3 in prod, RustFS locally and in CI). Predictions come from the external
`soil-moisture-prediction` library; CRNS data comes from the TimeIO / STI API.

Infrastructure that is not CRNS-specific comes from
[`cosmo-ecosystem`](https://codebase.helmholtz.cloud/ufz/tb5-smm/met/wg7/cosmo-ecosystem), the
framework shared with the sister app COSMONAUT, pinned to a tag in `pyproject.toml`.
See [Framework boundary](#framework-boundary) below.

## Component map

| Component | Purpose |
|-----------|---------|
| `app.py` | Dash/Flask app initialization and entry point (starts no threads — Celery Beat runs in the worker) |
| `layouts.py` | Shared page shell (navbar + content) |
| `pages/` | The multi-page UI — one module per page (home, new_job, job_management, results, sensor/CRNS admin, measurement_view, documentation, …). `logs.py`, `worker_management.py` and `job_management.py` are shims over the framework pages |
| `pydantic_models.py` | Pydantic models for job-input validation |
| `form_template_factory.py` | Builds form views from selected inputs (predictors + CRNS); pairs with the `dash-form-factory` dependency |
| `job.py` | The Cosmopolitan Job model and its workflow |
| `background_job_manager.py` | The domain job submissions on top of the framework's `BackgroundJobManager` |
| `celery_app.py`, `celery_config.py` | Celery app and broker (Redis) configuration |
| `tasks/` | Celery task definitions — computation jobs and periodic maintenance |
| `postgres_manager.py` | SQLAlchemy ORM models and DB operations (PostGIS) |
| `timeio_manager.py`, `timeio_info.py` | Data acquisition from the TimeIO / STI API (CRNS measurements) |
| `map_utils.py` | Map layers (TiTiler tile layers for GeoTIFF; dash-leaflet) |
| `error_handling.py` | Custom exceptions and the error modal |
| `email_service.py` | Notification emails (e.g. job finished) |
| `files_route.py` | Flask route for downloading job files |
| `doc_generator.py`, `screenshot_generator.py` | Generate in-app documentation and screenshots |
| `config.py` | The framework's infrastructure variables plus the domain's own |
| `constants/` | `html_ids.py` (HTML ID constants — see convention) and `general.py` |

## Framework boundary

These modules are **not** in this repository — they are imported from `cosmo_ecosystem`:

| Framework module | Used for |
|---|---|
| `cosmo_ecosystem.config` | The 18 infrastructure env vars, `getenv`, `JOB_WORK_DIR_TEMPLATE` |
| `cosmo_ecosystem.logger` | `PostgreSQLHandler`, log format, the dictConfig builders (domain exclusions passed in from `constants/general.py`) |
| `cosmo_ecosystem.db_manager` | `Base`, `DbManager`, `JobColumns`, `LogTable` — `PostgresManager` subclasses `DbManager`, one engine per process |
| `cosmo_ecosystem.object_storage_manager` | S3 access via rclone, presigned URLs via boto3, `ObjectStorageError` |
| `cosmo_ecosystem.logs_table` | Logs table UI and formatting |
| `cosmo_ecosystem.celery_config` | `BaseCeleryConfig` — broker, timeouts, worker limits |
| `cosmo_ecosystem.background_job_manager` | `BackgroundJobManager` submission/inspection plumbing |
| `cosmo_ecosystem.pydantic_models` | `UploadJobConfig`, `validate_job_id` |
| `cosmo_ecosystem.base_job`, `…job_persistence`, `…job_log`, `…job_run`, `…job_retention` | The `Job` contract, job persistence, job log, run lifecycle, expiry and cleanup |
| `cosmo_ecosystem.files_route` | Download routes and download button |
| `cosmo_ecosystem.error_handling` | `handle_error` and the infrastructure exceptions |
| `cosmo_ecosystem.pages.logs`, `…worker_management`, `…job_management` | Three admin pages, mounted by shims in `pages/` |
| `cosmo_ecosystem.layouts` | Header, column container, the navbar-collapse callback |
| `cosmo_ecosystem.tasks.test_tasks` | The long-running test task body |

Still local, each building on the framework module of the same concern:
`postgres_manager.py`, `job.py`, `error_handling.py` and `layouts.py` (rendering). Each of
those modules names its details in its docstring.

Two consequences of this split are easy to trip over — the two Celery clients against one
broker, and the navbar callback the framework registers for this app's navbar. Both are
explained in [`knowledge/systems/cosmo-ecosystem-boundary.md`](knowledge/systems/cosmo-ecosystem-boundary.md);
the rules for working across the boundary are in
[`conventions/framework_integration.md`](conventions/framework_integration.md).

## How it fits together

```text
1. User submits a prediction job through a Dash web form (pages/ + form_template_factory)
2. Job is validated (pydantic_models) and stored in PostgreSQL (postgres_manager)
3. Job is queued to Celery workers via Redis (background_job_manager / tasks)
4. The soil-moisture-prediction library processes the data on a worker
5. Results land in object storage (cosmo_ecosystem.object_storage_manager) and are displayed in the UI (pages/results)
```

Background work runs on dedicated Celery worker containers. A single Beat scheduler, embedded
in the worker (`--beat`), runs periodic maintenance — cleanup at 3 AM, CRNS data updates at 4 AM.

## Key patterns (and where the rules live)

- **HTML IDs only via `constants/html_ids.py`** — never literal ID strings. See [`conventions/html_ids.md`](conventions/html_ids.md).
- **Callback organization** — see [`conventions/callbacks.md`](conventions/callbacks.md).
- **Error handling** — custom exceptions + error modal. See [`conventions/error_handling.md`](conventions/error_handling.md).
- **Layout & flex** — reusable components. See [`conventions/layout.md`](conventions/layout.md).
- **Bootstrap-only styling** — no inline CSS. See [`conventions/bootstrap_styling.md`](conventions/bootstrap_styling.md).
- **Logging** — levels and logger usage. See [`conventions/logging.md`](conventions/logging.md).
- **Working across the framework boundary** — freeze rule, adoption rule, ID ownership. See [`conventions/framework_integration.md`](conventions/framework_integration.md).

## Entry points

- **Web app:** `cosmopolitan_app/app.py` (Dash + Flask) — Gunicorn in prod, `./dev_up.sh` / `docker compose up` locally.
- **Workers:** Celery workers from `docker/worker.Dockerfile`, executing `tasks/`.
- **Scheduler:** Celery Beat, embedded in the Celery worker (`docker/worker.Dockerfile`, `--beat`).

## Related

- [`README.md`](README.md) — what this directory is and how to add to it
- [`../README.md`](../README.md) — human-facing project README (dev/test/deploy details)
- [`conventions/deployment.md`](conventions/deployment.md) — Kubernetes/ArgoCD gotchas
