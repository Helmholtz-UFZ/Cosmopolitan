# Job Lifecycle

How a soil-moisture prediction job travels from the web form to a finished result. This is the
core flow of the application; most pages and background machinery exist to serve it.

## End-to-end flow

```text
1. User fills the new-job form        → pages/ + form_template_factory (see concepts/dynamic-forms.md)
2. Input is validated                 → ModelWebsite (pydantic_models.py)
3. Job is persisted                    → Job (job.py) → PostgreSQL (postgres_manager.py)
4. Job is queued                       → submissions.submit_computation_job() → Redis
5. A worker runs the prediction        → tasks/computation_tasks.start_computation_task → smp_main()
6. Results are stored                  → object storage (cosmo_ecosystem.object_storage_manager, S3)
7. User views results / gets emailed    → pages/results, email_service.py
```

Each `Job` owns a working directory under `WEB_WORK_DIR` (`job.working_dir`); the SMP run reads
its inputs from and writes its outputs into that directory, which are then synced to object
storage. Job status moves through `COMPLETED` / `FAILED` (set in `start_computation_task`:
`smp_main` returning `None` → `FAILED`, otherwise `COMPLETED`).

## Celery topology

The process's one Celery app is the framework's: `cosmo_ecosystem.celery_app` assembles it from
this app's **domain module**, [`domain.py`](../../../cosmopolitan_app/domain.py), which
`COSMO_DOMAIN=cosmopolitan_app.domain` names in every process (web, worker, CLI). See
`docs/conventions/domain_module.md` and ADR 0003 in cosmo-ecosystem. Broker **and** result
backend are Redis.

- **Domain settings** live in `domain.CeleryConfig`: timezone Europe/Berlin and the 3600/3900
  time limits, each next to its reasoning. It sets no `task_routes` or `beat_schedule`; the
  framework rejects a config that does.
- **Task specs** (`domain.task_specs`) register, route and schedule the app's tasks:
  `start_computation` → `computation`, `update_db` → `maintenance` (beat 04:00). The framework
  adds its own `cleanup` (`maintenance`, beat 03:00) and test task (`test`).
- **Task names** are explicit constants in [`submissions.py`](../../../cosmopolitan_app/submissions.py),
  next to the domain submissions (`submit_computation_job`, `submit_update_db_task`), which are
  module functions over the framework's `background_job_manager`.
- **Worker** (`docker/worker.Dockerfile`):
  `celery -A cosmo_ecosystem.celery_app.celery worker --concurrency=4 --beat`. No `--queues`: the
  worker consumes every queue a task spec routes to.
- The framework's `background_job_manager` is a **lazy module-level singleton**, and the Celery
  app is assembled on its first access, never at import. Nothing `domain.py` imports may touch
  either at import time (assembly imports `domain.py`), which is why `submissions.py` looks the
  manager up at call time.

On submit, `submit_computation_job` also writes `task_name:<id>` into Redis with a 24 h TTL so a
task's name can still be recovered after it is revoked.

## Beat scheduler (periodic maintenance)

Two scheduled tasks, built by the framework from the task specs, in Europe/Berlin time:

- `cosmo_ecosystem.tasks.maintenance_tasks.cleanup` — 03:00, the framework's cleanup (deletes
  logs older than `domain.log_retention_days` = 60, then expired jobs).
- `cosmopolitan_app.tasks.maintenance_tasks.update_db` — 04:00 (refreshes CRNS measurements; see
  [`timeio-integration.md`](timeio-integration.md)).

**How Beat runs:** embedded in the Celery worker (`celery worker --beat`,
[`docker/worker.Dockerfile`](../../../docker/worker.Dockerfile)), as its own process. That relies
on exactly one worker pod — a second one would schedule everything twice. The schedule state file
is `/tmp/celerybeat-schedule`.

Until 2026-09 `app.py` started Beat in a daemon thread at import time, which was wrong both ways:
production ran Gunicorn *without* `--preload`, so each of the four workers started its own Beat and
every scheduled task ran four times; and with `--preload` (the dev image with `GUNICORN=1`) a
worker forked while that thread held one of Celery's locks blocks forever on its first task
submission. See `docs/conventions/celery_beat.md` in cosmo-ecosystem.

## Worker tuning

From the framework's `BaseCeleryConfig` and `domain.CeleryConfig`: `worker_prefetch_multiplier=1` and `task_acks_late=True` (fair dispatch,
re-queue on crash), `worker_max_tasks_per_child=50` and `worker_max_memory_per_child≈512 MB`
(recycle workers to bound memory), `task_soft_time_limit=3600` / `task_time_limit=3900`, 3 retries.
Celery's own logging is disabled (`worker_hijack_root_logger=False`) in favour of the PostgreSQL
log handler (see [`../../conventions/logging.md`](../../conventions/logging.md)).

## Gotchas

- **`test_background_job_manager.py` does not exercise `submit_test_task()`.** It calls
  `app.send_task(NAME_TEST_TASK, queue="maintenance")` directly, so it never touches the queue
  the real submit path uses. That is why the unconsumed `test` queue (fixed 2026-08-06 by adding
  `test` to the worker's queue list) stayed invisible to the suite. Since the worker derives its
  queues from the task specs, a queue nobody consumes can no longer arise this way.

## Related

- [`../concepts/dynamic-forms.md`](../concepts/dynamic-forms.md) — how step 1's form is built
- [`soil-moisture-prediction.md`](soil-moisture-prediction.md) — what `smp_main()` in step 5 does
- [`timeio-integration.md`](timeio-integration.md) — the data the 4 AM `update_db` task refreshes
- [`../../architecture.md`](../../architecture.md) — component map
- Code: [`domain.py`](../../../cosmopolitan_app/domain.py), [`submissions.py`](../../../cosmopolitan_app/submissions.py), [`tasks/computation_tasks.py`](../../../cosmopolitan_app/tasks/computation_tasks.py), [`tasks/maintenance_tasks.py`](../../../cosmopolitan_app/tasks/maintenance_tasks.py)
