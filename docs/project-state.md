# Project State

Last updated: 2026-08-06

## Current priorities

- **Slice 2**: `postgres_manager.py` onto the framework `Base` (`PostgresManager(DbManager)`),
  which collapses the two-engine state. Then `job.py`, `error_handling.py` (needs an
  `on_unhandled` hook in the framework, else maintainer mails stop silently).
- **Measure the real Celery runtimes** rather than inheriting them. The re-pin kept
  `task_soft_time_limit`/`task_time_limit` at 3600/3900 s because production has run under
  those bounds for a long time without regionalisation jobs being cut off — that is evidence,
  but it was never gathered deliberately. The actual runtimes are already in the database:
  `jobs.start_date` against the last log entry per `job_id`. One query, not a project.

## Recent changes

- 2026-08-06: **Slice 1b** — `background_job_manager` onto the framework base (265 → 105) and
  the Logs and Worker Management pages served from `cosmo_suite` via docstring-carrying shims
  (490 → 39, 866 → 53). `pages/job_management.py` and `files_route.py` deliberately stay local;
  each names its reason in its docstring. Fixed a pre-existing bug on the way: the Worker
  Management test task went to a queue no worker consumed and sat in PENDING forever.
  Slice 1b alone: −1471 lines of app code. See
  [cosmo-suite-boundary.md](knowledge/systems/cosmo-suite-boundary.md) and
  [framework_integration.md](conventions/framework_integration.md).

- 2026-08-06: **Re-pinned to `cosmo-suite@v0.4.0`**, which brings both apps onto the same tag.
  Three of its changes are silent for a consumer and were handled deliberately:
  `ModelWebsite` moved to `UploadJobConfig` (the base no longer carries
  `upload_file_name`); `task_soft_time_limit`/`task_time_limit` are now declared here at
  3600/3900 s instead of inherited, since the framework dropped them to `None`; and
  `get_files()` at `job.py:249` passes `overwrite=True` to keep the old semantics. The local
  `logger.py` shim is gone — the framework builders now take `excluded_packages`, so the
  domain list lives in `constants/general.py`.

- 2026-08-06: **Slice 1 of the `cosmo-suite` integration** — the app now imports the shared
  framework instead of duplicating it. `pyproject.toml` pinned `cosmo-suite@v0.3.0` (now v0.4.0);
  `logs_table.py`, `object_storage_manager.py` and `tasks/test_tasks.py` are deleted,
  `config.py`, `celery_config.py` and `ModelWebsite` sit on framework bases.
  Net −710 lines. See [Framework boundary](architecture.md#framework-boundary).

- 2026-06-17: Built out the `docs/` LLM-wiki layer — added `AGENTS.md`, `architecture.md`,
  this file, `decisions/`, two maintenance skills, and a [`knowledge/`](knowledge/index.md) base
  (job lifecycle, soil-moisture-prediction, TimeIO integration, dynamic forms).
- 2026-06-17: Updated the README "Code Quality" section to `ruff` (was black/isort/flake8).
- 2026-06-04: Added a deployment convention documenting the `values.yaml` nightly re-tag gotcha
  and the haproxy ingress requirement — [`conventions/deployment.md`](conventions/deployment.md).
- 2026-06-03: Fixed the ingress — switched `className` to `haproxy` and stopped the nightly
  pipeline from clobbering it (issue #48).

## Open questions

- The `docker-compose.local_smp.yml` (underscore) filename referenced by `docker_local_smp_up.sh`
  and the README doesn't exist — the real file is `docker-compose.local-smp.yml` (hyphen). Worth a
  cleanup. See [`knowledge/systems/soil-moisture-prediction.md`](knowledge/systems/soil-moisture-prediction.md).

## Decisions made

- **Ingress `className` must be `haproxy`; re-tag after any `values.yaml` infra change.** The UFZ
  cluster's working controller is haproxy, and the nightly pipeline reverts un-tagged `values.yaml`
  edits. Full rationale in [`conventions/deployment.md`](conventions/deployment.md) (#48).
- **No defensive programming.** No `dict.get()`, no bare `except Exception`, no inline imports,
  no inline CSS; HTML IDs only via `constants/html_ids.py`. See [`../CLAUDE.md`](../CLAUDE.md).
- **Lint/format is `ruff`.** Enforced by pre-commit and CI, superseding the black/isort/flake8
  referenced in the README.
