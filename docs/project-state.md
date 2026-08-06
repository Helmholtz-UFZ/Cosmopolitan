# Project State

Last updated: 2026-08-06

## Current priorities

- **Slice 2 of the `cosmo-suite` integration.** Slice 1 landed (see below). What is left needs
  the framework's `db_manager`, `job` and `layouts` adopted together, because the remaining
  candidates all import them: `files_route.py`, `pages/logs.py`, `pages/job_management.py`,
  `pages/worker_management.py` (1652 lines). Taking any of them alone would put a second
  SQLAlchemy engine, a second Celery client and a second `Job` class into the same process.
- Two things Slice 2 needs from the framework itself, neither of which exists at `v0.3.0`:
  an `on_unhandled` hook for `handle_error` (without it the mails to `MAINTAINER_EMAIL` stop
  silently), and an `excluded_packages` parameter for `ExcludeSubmodulesFilter` (would remove
  the shim in `logger.py`).

## Recent changes

- 2026-08-06: **Slice 1 of the `cosmo-suite` integration** — the app now imports the shared
  framework instead of duplicating it. `pyproject.toml` pins `cosmo-suite@v0.3.0`;
  `logs_table.py`, `object_storage_manager.py` and `tasks/test_tasks.py` are deleted,
  `config.py`, `logger.py`, `celery_config.py` and `ModelWebsite` sit on framework bases.
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
