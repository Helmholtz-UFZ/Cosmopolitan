# The cosmo-suite Boundary

How this app and the shared framework
[`cosmo-suite`](https://codebase.helmholtz.cloud/ufz/tb5-smm/met/wg7/cosmo-suite) divide the
work, what runs twice as a result, and why that was accepted.

The framework is a pinned dependency in `pyproject.toml`. It is **not** edited from this
repo — see [`../../conventions/framework_integration.md`](../../conventions/framework_integration.md).

## What comes from the framework

| Imported | Provides |
|---|---|
| `cosmo_suite.config` | The 18 infrastructure env vars, `getenv`, `JOB_WORK_DIR_TEMPLATE` |
| `cosmo_suite.logger` | `PostgreSQLHandler`, log format, the dictConfig builders |
| `cosmo_suite.object_storage_manager` | MinIO/S3 access via rclone, `ObjectStorageError` |
| `cosmo_suite.logs_table` | Log list rendering (`format_logs_list`, `level_badge`) |
| `cosmo_suite.celery_config` | `BaseCeleryConfig` |
| `cosmo_suite.background_job_manager` | `BackgroundJobManager` plumbing |
| `cosmo_suite.pydantic_models` | `BaseJobConfig`, `validate_job_id` |
| `cosmo_suite.pages.logs`, `…worker_management` | Two admin pages (via shims in `pages/`) |
| `cosmo_suite.layouts` | The navbar-collapse callback (see below) |
| `cosmo_suite.tasks.test_tasks` | The test task body |

## What stays here, and why

`postgres_manager.py`, `job.py`, `error_handling.py`, `layouts.py` (rendering),
`pages/job_management.py`, `files_route.py`. Each module's docstring names its own reason.
The short version:

- **`pages/job_management.py`** — the framework page hardcodes a submission path this app
  does not use, deletes through the framework `Job`, and uses a server-side loading-overlay
  callback that `../../conventions/callbacks.md` forbids.
- **`files_route.py`** — blocked on the `Job` seam, not on the routes; the route set is
  already identical.
- **`error_handling.py`** — the framework has no `on_unhandled` hook, so adopting it would
  silently drop the mails to `MAINTAINER_EMAIL`.

## Two engines against one Postgres

This is the deliberate transitional state, accepted knowingly.

Since the Logs page is served from the framework, the process holds **two** SQLAlchemy
setups against the same database:

- `cosmopolitan_app/postgres_manager.py` — its own `create_engine` / `sessionmaker` / `Base`,
  used by everything domain-related.
- `cosmo_suite/db_manager.py` — its own, used **only** for the Logs page's two queries
  (`query_distinct_modules`, `query_logs`).

**Why it is safe here:**

1. The framework's `LogTable` is byte-identical to this app's — same table, same six columns.
2. Nothing in either tree calls `Base.metadata.create_all()`. The schema comes from
   `docker/init.sql`, so two declarative registries never race to define the same table.
3. The framework's `DbManager` is used for reads on `logs` only. It never touches `jobs`,
   whose framework mapping would be too narrow anyway (this app's `JobTable` additionally
   has `prepared_input`).

**What it costs:** a second connection pool in the web process, and the fact that point 3 is
a convention rather than something enforced. Widening the framework `DbManager`'s use here
without first unifying the mappings would be a bug.

**How it is resolved:** the next slice puts this app's tables on the framework `Base`
(`class PostgresManager(DbManager)`), which collapses this to one engine.

## Callbacks the framework registers on import

Importing any framework page pulls in `cosmo_suite.layouts`, which registers three callbacks
at import time. This matters more here than in the sister app, because this app's HTML ID
constants match the framework's **by value**.

- **navbar collapse** — the framework's callback drives *this app's* navbar. This app must
  therefore **not** declare its own: two callbacks on one Output without `allow_duplicate` is
  a hard Dash error that takes the whole callback registry down, not just the navbar. The
  symptom is misleading — every page breaks, including ones far from the framework page that
  triggered the import. `layouts.py` imports `cosmo_suite.layouts` explicitly so this does
  not depend on which page happens to be imported.
- **two reset-modal callbacks** — inert. Their `RESET_*` components are not in this app's
  layout and nothing writes the store that triggers them. They cost two dead entries in the
  callback graph.

The framework-side fix is to register these behind an opt-in function instead of at import
time; it is on the MR list.

## Related

- [`../../conventions/framework_integration.md`](../../conventions/framework_integration.md) — the binding rules
- [`../../architecture.md`](../../architecture.md#framework-boundary) — the component map
- [`job-lifecycle.md`](job-lifecycle.md) — the Celery topology this touches
