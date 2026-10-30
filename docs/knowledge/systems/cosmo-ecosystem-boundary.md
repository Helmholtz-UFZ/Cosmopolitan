# The cosmo-ecosystem Boundary

How this app and the shared framework
[`cosmo-ecosystem`](https://codebase.helmholtz.cloud/ufz/tb5-smm/met/wg7/cosmo-ecosystem) divide the
work, what still runs twice as a result, and why that was accepted.

The framework is a pinned dependency in `pyproject.toml`. It is **not** edited from this
repo — see [`../../conventions/framework_integration.md`](../../conventions/framework_integration.md).

## What comes from the framework

| Imported | Provides |
|---|---|
| `cosmo_ecosystem.config` | The 18 infrastructure env vars, `getenv`, `JOB_WORK_DIR_TEMPLATE` |
| `cosmo_ecosystem.logger` | `PostgreSQLHandler`, log format, the dictConfig builders |
| `cosmo_ecosystem.db_manager` | `Base`, `DbManager`, `JobColumns`, `LogTable` — the one engine and declarative registry (see below) |
| `cosmo_ecosystem.object_storage_manager` | S3 access via rclone, presigned URLs via boto3, `ObjectStorageError` |
| `cosmo_ecosystem.logs_table` | Log list rendering (`format_logs_list`, `level_badge`) |
| `cosmo_ecosystem.celery_config` | `BaseCeleryConfig` |
| `cosmo_ecosystem.background_job_manager` | `BackgroundJobManager` plumbing |
| `cosmo_ecosystem.pydantic_models` | `UploadJobConfig`, `validate_job_id` |
| `cosmo_ecosystem.base_job` | `BaseJob`, the five-member contract `Job` implements |
| `cosmo_ecosystem.job_persistence`, `…job_log`, `…job_run` | Job row and work-dir persistence, the job log, the worker-side run lifecycle |
| `cosmo_ecosystem.job_retention` | Job expiry (`days_to_live`) and the nightly `clean_up_jobs` |
| `cosmo_ecosystem.files_route` | The download routes (`serve_files`, given `job_class=Job`) and `create_download_button` |
| `cosmo_ecosystem.error_handling` | `handle_error`, `USE_ERROR_MESSAGE` and the infrastructure exceptions (`JobNotFound`, `InvalidJobID`, `JobExists`, `RedisConnectionError`) |
| `cosmo_ecosystem.pages.logs`, `…worker_management`, `…job_management` | Three admin pages (via shims in `pages/`); the job management shim sets the row link `cosmo_ecosystem.pages.job_link` first |
| `cosmo_ecosystem.layouts` | `create_header`, `page_container_column_layout`, `register_navbar_callbacks` (see below) |
| `cosmo_ecosystem.tasks.test_tasks` | The test task body |

## What stays here, and why

`postgres_manager.py`, `job.py`, `error_handling.py`, `layouts.py`. None of them is a copy
any more: each builds on the framework module of the same concern and adds the domain on
top. Each module's docstring names the details. The short version:

- **`postgres_manager.py`** — `PostgresManager(DbManager)`: the domain tables (on the
  framework `Base`) and their queries.
- **`job.py`** — `Job(BaseJob)`: construction, the working directory and the whole CRNS
  domain; persistence goes through `job_persistence`.
- **`error_handling.py`** — the domain exceptions, the error modal, and a `handle_error`
  that delegates to the framework's, laying this app's response table and expected-error
  set over the defaults. The maintainer mail is wired in `app.py` as the framework's
  `on_unhandled` hook.
- **`layouts.py`** — the navbar and page shells; the shared pieces are imported.

## One engine, two Celery clients

`PostgresManager` subclasses the framework's `DbManager`, and this app's tables sit on the
framework `Base` with `LogTable` imported rather than copied. The process therefore holds
**one** SQLAlchemy engine, session factory and declarative registry, shared by the domain
code and the framework pages. `postgres_manager.py` assigns `DbManager.job_table = JobTable`
— on the base class, because framework code such as `job_retention` calls `DbManager`
directly — so framework code reaches this app's wider `jobs` row (it has `prepared_input`).
The schema still comes from `docker/init.sql`; nothing calls `Base.metadata.create_all()`.

Celery is **not** unified. The worker-management page uses the framework's module-level
`background_job_manager`, a Celery client configured from `BaseCeleryConfig`; the domain
code uses this app's subclass, configured from its own `CeleryConfig`. Both talk to the same
broker. This app also disconnects the framework's `worker_process_init` logging handler, see
[`../../conventions/framework_integration.md`](../../conventions/framework_integration.md).

## Callbacks the framework registers

This app's HTML ID constants match the framework's **by value**, so a framework callback
can drive a component this app renders.

- **navbar collapse** — since v0.7.0 no longer registered by importing
  `cosmo_ecosystem.layouts`, but by the idempotent `register_navbar_callbacks()`.
  `layouts.create_navbar` calls it, and the framework callback then drives *this app's*
  navbar. This app must therefore **not** declare its own: two callbacks on one Output
  without `allow_duplicate` is a hard Dash error that takes the whole callback registry
  down, not just the navbar. The symptom is misleading — every page breaks.
- **framework pages** — each page module registers its own callbacks on import, as any
  Dash page does. That is why they are mounted through shims in `pages/`.

## Related

- [`../../conventions/framework_integration.md`](../../conventions/framework_integration.md) — the binding rules
- [`../../architecture.md`](../../architecture.md#framework-boundary) — the component map
- [`job-lifecycle.md`](job-lifecycle.md) — the Celery topology this touches
