# Project State

Last updated: 2026-06-17

## Current priorities

TODO: No in-flight work is recorded yet — what is the current development focus? Fill this in
(or run the session-close skill at the end of a working session to keep it current).

## Recent changes

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
