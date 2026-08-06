# Job Lifecycle

How a soil-moisture prediction job travels from the web form to a finished result. This is the
core flow of the application; most pages and background machinery exist to serve it.

## End-to-end flow

```text
1. User fills the new-job form        → pages/ + form_template_factory (see concepts/dynamic-forms.md)
2. Input is validated                 → ModelWebsite (pydantic_models.py)
3. Job is persisted                    → Job (job.py) → PostgreSQL (postgres_manager.py)
4. Job is queued                       → background_job_manager.submit_computation_job() → Redis
5. A worker runs the prediction        → tasks/computation_tasks.start_computation_task → smp_main()
6. Results are stored                  → object storage (cosmo_suite.object_storage_manager, MinIO/S3)
7. User views results / gets emailed    → pages/results, email_service.py
```

Each `Job` owns a working directory under `WEB_WORK_DIR` (`job.working_dir`); the SMP run reads
its inputs from and writes its outputs into that directory, which are then synced to object
storage. Job status moves through `COMPLETED` / `FAILED` (set in `start_computation_task`:
`smp_main` returning `None` → `FAILED`, otherwise `COMPLETED`).

## Celery topology

Celery config lives in [`celery_config.py`](../../../cosmopolitan_app/celery_config.py)
(`CeleryConfig`). Broker **and** result backend are Redis.

- **Task names** are explicit constants in
  [`background_job_manager.py`](../../../cosmopolitan_app/background_job_manager.py):
  `start_computation` (computation), `cleanup` / `update_db` (maintenance),
  `long_running_test` (test).
- **Registration** happens in [`celery_app.py`](../../../cosmopolitan_app/celery_app.py), the
  worker entry point — kept separate from `background_job_manager` to break a circular import
  (`tasks/*.py → job → background_job_manager → tasks/*.py`).
- **Routing** (`task_routes`): `computation_tasks.*` → `computation` queue,
  `maintenance_tasks.*` → `maintenance` queue. Default queue is `default`.
- **Worker** (`docker/worker.Dockerfile`):
  `celery -A cosmopolitan_app.celery_app.celery worker --concurrency=4 --queues=default,computation,maintenance`.
- `BackgroundJobManager` is a **lazy module-level singleton** (created on first access to
  `background_job_manager` via `module.__getattr__`), so importing the module doesn't connect to
  Redis.

On submit, `submit_computation_job` also writes `task_name:<id>` into Redis with a 24 h TTL so a
task's name can still be recovered after it is revoked.

## Beat scheduler (periodic maintenance)

Two scheduled tasks, defined in `CeleryConfig.beat_schedule`:

- `cleanup-at-3am` — `crontab(minute=0, hour=3)` → `cleanup` (clears old jobs and logs).
- `update-db-at-4am` — `crontab(minute=0, hour=4)` → `update_db` (refreshes CRNS measurements;
  see [`timeio-integration.md`](timeio-integration.md)).

**How Beat actually runs (non-obvious):** [`app.py`](../../../cosmopolitan_app/app.py) starts Beat
in a **daemon `Thread`** at import time (`start_beat_scheduler` → `...app.Beat(...).run()`), not as
a separate process. In production the web app is launched by Gunicorn with `--preload`, so `app.py`
is imported **once** in the master before workers fork — which is what guarantees a single Beat
thread. Without `--preload`, each Gunicorn worker would import `app.py` and start its own Beat
thread, producing duplicate scheduled runs. The schedule state file is `/tmp/celerybeat-schedule`.

> Note: the README/CLAUDE wording ("runs in the Gunicorn master process") describes the effect;
> the mechanism is the daemon thread above.

## Worker tuning

From `CeleryConfig`: `worker_prefetch_multiplier=1` and `task_acks_late=True` (fair dispatch,
re-queue on crash), `worker_max_tasks_per_child=50` and `worker_max_memory_per_child≈512 MB`
(recycle workers to bound memory), `task_soft_time_limit=3600` / `task_time_limit=3900`, 3 retries.
Celery's own logging is disabled (`worker_hijack_root_logger=False`) in favour of the PostgreSQL
log handler (see [`../../conventions/logging.md`](../../conventions/logging.md)).

## Gotchas

- **`test` queue is not consumed.** `submit_test_task` sends to `queue="test"`, but the worker
  only listens on `default,computation,maintenance`. The test task won't run unless a worker is
  started with `-Q test`.
- **Manual cleanup vs scheduled cleanup use different queues.** `submit_cleanup_task` sends to
  `default`, while the Beat-scheduled `cleanup` uses `maintenance`. Both are consumed by the
  worker, so both run — but the inconsistency is easy to trip over when reasoning about routing.

## Related

- [`../concepts/dynamic-forms.md`](../concepts/dynamic-forms.md) — how step 1's form is built
- [`soil-moisture-prediction.md`](soil-moisture-prediction.md) — what `smp_main()` in step 5 does
- [`timeio-integration.md`](timeio-integration.md) — the data the 4 AM `update_db` task refreshes
- [`../../architecture.md`](../../architecture.md) — component map
- Code: [`background_job_manager.py`](../../../cosmopolitan_app/background_job_manager.py), [`tasks/computation_tasks.py`](../../../cosmopolitan_app/tasks/computation_tasks.py), [`tasks/maintenance_tasks.py`](../../../cosmopolitan_app/tasks/maintenance_tasks.py)
