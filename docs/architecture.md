# COSMOPOLITAN — Architecture Overview

Quick-reference map of the codebase for new sessions and new contributors. All application
code lives under [`cosmopolitan_app/`](../cosmopolitan_app/).

## Stack

Dash (Plotly) on a Flask server, Celery + Redis for background work, PostgreSQL/PostGIS for
spatial data, MinIO (S3, via rclone) for object storage. Predictions come from the external
`soil-moisture-prediction` library; CRNS data comes from the TimeIO / STI API.

## Component map

| Component | Purpose |
|-----------|---------|
| `app.py` | Dash/Flask app initialization and entry point; starts the Celery Beat scheduler in the Gunicorn master (`--preload`) |
| `layouts.py` | Shared page shell (navbar + content) |
| `pages/` | The multi-page UI — one module per page (home, new_job, job_management, results, logs, sensor/CRNS admin, measurement_view, documentation, …) |
| `pydantic_models.py` | Pydantic models for job-input validation |
| `form_template_factory.py` | Builds form views from selected inputs (predictors + CRNS); pairs with the `dash-form-factory` dependency |
| `job.py` | The Cosmopolitan Job model and its workflow |
| `background_job_manager.py` | Celery task orchestration / job queueing |
| `celery_app.py`, `celery_config.py` | Celery app and broker (Redis) configuration |
| `tasks/` | Celery task definitions — computation jobs and periodic maintenance |
| `postgres_manager.py` | SQLAlchemy ORM models and DB operations (PostGIS) |
| `object_storage_manager.py` | MinIO/S3 access via rclone |
| `timeio_manager.py`, `timeio_info.py` | Data acquisition from the TimeIO / STI API (CRNS measurements) |
| `map_utils.py` | Map layers (TiTiler tile layers for GeoTIFF; dash-leaflet) |
| `error_handling.py` | Custom exceptions and the error modal |
| `logger.py` | Logging setup, including a handler that writes log records to PostgreSQL |
| `logs_table.py` | Logs table UI and formatting |
| `email_service.py` | Notification emails (e.g. job finished) |
| `files_route.py` | Flask route for downloading job files |
| `doc_generator.py`, `screenshot_generator.py` | Generate in-app documentation and screenshots |
| `config.py` | Configuration / environment loading |
| `constants/` | `html_ids.py` (HTML ID constants — see convention) and `general.py` |

## How it fits together

```text
1. User submits a prediction job through a Dash web form (pages/ + form_template_factory)
2. Job is validated (pydantic_models) and stored in PostgreSQL (postgres_manager)
3. Job is queued to Celery workers via Redis (background_job_manager / tasks)
4. The soil-moisture-prediction library processes the data on a worker
5. Results land in MinIO (object_storage_manager) and are displayed in the UI (pages/results)
```

Background work runs on dedicated Celery worker containers. A single Beat scheduler (pinned to
the Gunicorn master via `--preload`) runs periodic maintenance — cleanup at 3 AM, CRNS data
updates at 4 AM.

## Key patterns (and where the rules live)

- **HTML IDs only via `constants/html_ids.py`** — never literal ID strings. See [`conventions/html_ids.md`](conventions/html_ids.md).
- **Callback organization** — see [`conventions/callbacks.md`](conventions/callbacks.md).
- **Error handling** — custom exceptions + error modal. See [`conventions/error_handling.md`](conventions/error_handling.md).
- **Layout & flex** — reusable components. See [`conventions/layout.md`](conventions/layout.md).
- **Bootstrap-only styling** — no inline CSS. See [`conventions/bootstrap_styling.md`](conventions/bootstrap_styling.md).
- **Logging** — levels and logger usage. See [`conventions/logging.md`](conventions/logging.md).

## Entry points

- **Web app:** `cosmopolitan_app/app.py` (Dash + Flask) — Gunicorn in prod, `./dev_up.sh` / `docker compose up` locally.
- **Workers:** Celery workers from `docker/worker.Dockerfile`, executing `tasks/`.
- **Scheduler:** Celery Beat, embedded in the Gunicorn master process.

## Related

- [`README.md`](README.md) — what this directory is and how to add to it
- [`../README.md`](../README.md) — human-facing project README (dev/test/deploy details)
- [`conventions/deployment.md`](conventions/deployment.md) — Kubernetes/ArgoCD gotchas
