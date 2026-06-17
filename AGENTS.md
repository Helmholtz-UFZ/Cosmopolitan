# AGENTS.md — COSMOPOLITAN

A Dash web service that analyzes cosmic ray neutron sensor (CRNS) data to predict soil
moisture, aiming at a live soil moisture map of Germany via random-forest models.

This is the universal entry point for coding agents working on this repo. Read it first.
Deeper material lives under [`docs/`](docs/) — this file points there rather than repeating
it. (Claude-specific workflow lives in [`CLAUDE.md`](CLAUDE.md).)

## Commands

| Task | Command |
|------|---------|
| Install / set up | `uv sync` |
| Run locally (mock, no external services) | `./dev_up.sh mock` |
| Run locally (against prod services) | `cp env_dev_prod env_dev_prod_priv` then `./dev_up.sh prod` |
| Run via Docker | `docker compose up --build` |
| Test (spins up temporary services) | `./run_pytest.sh` |
| Test (services already running) | `pytest -s` |
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format .` |
| Pre-commit (all hooks) | `pre-commit run --all-files` |

Python ≥3.13, managed with `uv`. Add a dependency with `uv add <package>`.

## Layout

```text
cosmopolitan_app/   — the Dash app: pages/, tasks/ (Celery), constants/ (incl. html_ids), managers
test/               — pytest suite, including Playwright e2e (test/test_e2e.py)
docker/             — Dockerfiles and init.sql
deployments/ufz/    — Kubernetes/ArgoCD values.yaml for stage/ and prod/
env_*               — per-environment config files (see README)
docs/               — agent/docs layer (start at docs/README.md)
```

## Where to find more

- [`docs/README.md`](docs/README.md) — what the docs layer contains and how to add to it
- [`docs/architecture.md`](docs/architecture.md) — module map and how the pieces fit
- [`docs/project-state.md`](docs/project-state.md) — current priorities and recent changes
- [`docs/conventions/`](docs/conventions/) — binding coding rules (read the relevant one before editing)
- [`docs/skills/`](docs/skills/) — step-by-step procedures for common tasks
- [`docs/knowledge/`](docs/knowledge/index.md) — how key concepts and subsystems work

## Working agreement

- Follow the conventions in [`docs/conventions/`](docs/conventions/); match the style of surrounding code.
- Honor the anti-patterns in [`CLAUDE.md`](CLAUDE.md) (no `dict.get()`, no bare `except`, no inline imports/CSS, HTML IDs only via `constants/`).
- Don't commit or push unless asked; leave version control to the human.
- When a structural change lands, update the docs layer — see [`docs/skills/structural_doc_update.md`](docs/skills/structural_doc_update.md).
