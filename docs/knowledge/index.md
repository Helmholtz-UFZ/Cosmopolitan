# COSMOPOLITAN — Knowledge Index

Durable, cross-linked project knowledge for coding agents and human contributors. This is the
stuff that should survive individual sessions: how concepts and systems work and how the pieces
behave in practice.

It complements — but does not replace:

- [`../conventions/`](../conventions/) — binding coding rules and anti-patterns,
- [`../skills/`](../skills/) — reusable procedures,
- [`../architecture.md`](../architecture.md) — the high-level code map,
- [`../project-state.md`](../project-state.md) — the current state of active work.

## How to use this directory

- Start here when you need project knowledge beyond coding rules.
- Prefer updating an existing page over creating a near-duplicate.
- One concept / system per file. Cross-link related pages with relative Markdown links.
- Put transient working notes elsewhere (a plan dir or your tracker), not here.

## Pages

### Concepts — `concepts/`
Durable concepts used across the codebase.
- [dynamic-forms.md](concepts/dynamic-forms.md) — how job forms are generated from the `ModelWebsite` Pydantic model via `dash-form-factory`.

### Systems — `systems/`
Major subsystems and how they interact.
- [job-lifecycle.md](systems/job-lifecycle.md) — end-to-end flow of a prediction job (form → Postgres → Celery → SMP → MinIO → results) and the Celery/Beat setup.
- [soil-moisture-prediction.md](systems/soil-moisture-prediction.md) — the external `soil-moisture-prediction` library, its inputs, and the assumptions the app pins to it.
- [timeio-integration.md](systems/timeio-integration.md) — CRNS measurement acquisition from the TimeIO / STA (SensorThings) API.
- [cosmo-suite-boundary.md](systems/cosmo-suite-boundary.md) — what comes from the shared framework, what stays local, and the two-engine transitional state.

> Other page types (`datasets/`, `runbooks/`, `raw/`) are not used yet — add the folder and a
> section here when the first such page earns its place.

## Core files

- [log.md](log.md) — chronological history of knowledge updates.

## Page-creation rules

Create a new page only if **all** are true:

1. the knowledge will likely matter again in future sessions,
2. it is broader than a single temporary plan,
3. it describes a concept / system / dataset / procedure — not a one-off decision or a code
   review comment,
4. it is substantial enough to deserve its own file (aim for 100+ words, clear structure).

Do **not** create a page for: quick debugging notes, single-session decisions (use git messages
or an ADR in [`../decisions/`](../decisions/)), or code-only problems (those belong in the code
and its tests). Binding rules go in [`../conventions/`](../conventions/), not here.
