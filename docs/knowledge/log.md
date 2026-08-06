# Knowledge Log

Chronological history of important updates to [`knowledge/`](index.md). Record new pages, major
restructures, substantial revisions, and ingestion of raw material that changes the knowledge
model. Newest entries go at the top.

## Entry format

```md
## YYYY-MM-DD

- Added `path/to/file.md` — short note on what was added and why.
- Updated `path/to/file.md` — short note on what changed.
```

## 2026-08-06

- Added `knowledge/systems/cosmo-suite-boundary.md` — the split between this app and the
  shared framework after Slice 1/1b: what is imported, what deliberately stays local, the
  two-engines-one-Postgres transitional state and why it is safe, and the framework
  callbacks that register on import.
- Updated `knowledge/systems/job-lifecycle.md` — the unconsumed `test` queue is fixed
  (worker now listens on it); noted that `test_background_job_manager.py` bypasses
  `submit_test_task()`, which is why the suite never caught it.

## 2026-06-17

- Created `knowledge/index.md` and `knowledge/log.md` — established the knowledge layer.
- Added `knowledge/systems/job-lifecycle.md` — the end-to-end prediction-job flow and Celery/Beat setup.
- Added `knowledge/systems/soil-moisture-prediction.md` — the external SMP library and the input assumptions guarded by `test_smp_assumptions.py`.
- Added `knowledge/systems/timeio-integration.md` — CRNS data acquisition from the TimeIO / STA API.
- Added `knowledge/concepts/dynamic-forms.md` — Pydantic-model-driven form generation via `dash-form-factory`.
