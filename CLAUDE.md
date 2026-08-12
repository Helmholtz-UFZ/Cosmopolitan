> Entry point: [`AGENTS.md`](AGENTS.md) has the build/test/run commands, repo layout, and
> links into [`docs/`](docs/README.md) (architecture, project-state, conventions). This file
> adds the Claude-specific workflow on top.

## Project Overview

COSMOPOLITAN is a web service for analyzing cosmic ray data to predict soil moisture
content using random forest models. The application aims to evantually provide a live
soil moisture map of Germany based on cosmic ray neutron sensor (CRNS) data.

## Architecture

The application is built as a Dash web application with the following key components:

- **Web Framework**: Dash (plotly) with Flask server backend
- **Database**: PostgreSQL with PostGIS extension for spatial data
- **Object Storage**: MinIO for file storage with rclone integration
- **Background Tasks**: Celery with Redis broker for distributed task processing
- **External Services**: TimeIO API for CRNS data

## Sister Project: COSMONAUT

COSMOPOLITAN has a sister project **COSMONAUT** (`../ufz-cosmonaut`). Both share the
same architecture (Dash + Celery + PostgreSQL + MinIO), the same conventions, and the
same anti-patterns/coding rules. Key differences:

- **COSMONAUT** optimizes navigation routes for surveys.
- App module: `cosmonaut_app/` (vs `cosmopolitan_app/`)
- Backend package: `sensor-routing` (COSMOPOLITAN uses `soil-moisture-prediction`)
- Has Dash Leaflet map conventions (`docs/conventions/dash_leaflet.md`)

When the user references "cosmonaut" they mean this project. Patterns and fixes in one
project often apply symmetrically to the other.

## Convention Philosophy

All conventions are norms, not hard rules. A convention may be violated when there is a
good reason — but the violation must be accompanied by a comment explaining why.

## Critical Anti-Patterns

**DO NOT:**

1. **No defensive programming**

   - NO `dict.get()` - use direct access `dict["key"]`
   - NO bare `except Exception` - always catch specific exceptions
   - If one of these pattern are best practical solution use comment to explain reason.

2. **No inline imports**

   - All imports at TOP LEVEL ONLY
   - Never import inside functions

3. **HTML IDs - Restricted Usage**

   - MUST use constants from `cosmopolitan_app/constants.py`
   - NEVER use literal ID strings
   - ONLY create IDs for:
     1. Components used in callbacks (Input/Output/State)
     2. Components used in tests (Playwright locators)
     3. Components used with `set_props()` (requires `# nocheck`)
     4. Dynamically constructed IDs (requires `# nocheck`)
   - **LLMs tend to over-create IDs - resist this tendency**

4. **No inline CSS**

   - Use Bootstrap classes only
   - If custom css are best practical solution use comment to explain reason.

## Proactive Issue Reporting

When you spot bad practices, convention violations, symmetric bugs, or fragile patterns
— even if unrelated to the current task — flag them briefly and ask: "Want me to fix it?"

## Memory Policy

**DO NOT** use the auto memory system (`MEMORY.md`).

When you discover something worth preserving — a non-obvious gotcha, a hard-won
debugging insight, a pattern that should be followed — ask the user where to record it.
The options are:

- **`CLAUDE.md`** — High-level rules and project-wide constraints
- **An existing `docs/conventions/*.md`** — Extend the relevant convention file
- **A new `docs/conventions/*.md`** — If no existing file fits, propose creating one.
  Do not hesitate to do this; a focused new file is better than cramming unrelated
  knowledge into an existing one.
- **`docs/knowledge/`** — For *explanatory* knowledge (how a concept or subsystem works),
  not binding rules. Add a page under `concepts/` or `systems/`, then update
  [`docs/knowledge/index.md`](docs/knowledge/index.md) and add a dated entry to
  [`docs/knowledge/log.md`](docs/knowledge/log.md). Rules and anti-patterns still go in
  `conventions/`, not here.

Always prefer the most specific home for the knowledge. The distinction: `conventions/`
says *what you must do*; `docs/knowledge/` explains *how something works*.

Note: "DO NOT use the auto memory system" means no machine-managed `MEMORY.md` log — the
`docs/knowledge/` base above is a curated, hand-maintained set of pages, which is fine.

## Detailed Conventions

For specific implementation details, see:

- [Testing](docs/conventions/testing.md) - Test execution and CI pipeline
- [Error Handling](docs/conventions/error_handling.md) - Custom exceptions, error modal
- [Layout](docs/conventions/layout.md) - Reusable components, flex patterns
- [Bootstrap Styling](docs/conventions/bootstrap_styling.md) - Bootstrap classes only
- [Logging](docs/conventions/logging.md) - Log levels, proper logger usage
- [Callbacks](docs/conventions/callbacks.md) - Callback organization patterns
- [Environment Variables](docs/conventions/environment_variables.md) - Env files, config loading, secrets
- [Deployment](docs/conventions/deployment.md) - Kubernetes/ArgoCD gotchas, values.yaml tag automation, ingress className
- [Framework Integration](docs/conventions/framework_integration.md) - the `cosmo-suite` boundary: freeze rule, adoption rule, ID ownership, page shims

**Important** read the convention before you make any codebase exploration or answering.
Never sacrfice speed for accuracy.

Which conventions you should read depends on the first user prompt. Determine the
conventions which are important for the current task and read them imediatly. Keep the
conventions in mind and if you have not read them and they become important read them
then.

## Skills

When the user asks to perform one of these tasks, read the corresponding skill
document first for the step-by-step guide. This is espacially important for tasks the
user asks later. Keep this skill list in Mind:

- [New Page](docs/skills/new_page.md) - Checklist for creating a new page
- [New Module Test](docs/skills/create_module_test.md) - Checklist for creating a new core module test
- [Run and Fix Testing](docs/skills/run_and_fix_testing.md) - Systematic guide for running tests and diagnosing failures
- [Convention Keeper](docs/skills/convention_keeper.md) - Audit and fix convention violations across the codebase
- [Session Close](docs/skills/session_close.md) - Propose a `project-state.md` update at the end of a working session
- [Structural Doc Update](docs/skills/structural_doc_update.md) - Keep the `docs/` layer accurate after a structural change

## Identity Files — Read First, No Exceptions

You CANNOT respond to the user until you have attempted to read these files from the
project root. Use the Read tool (not Glob — they are symlinks). If Read fails, try
resolving the symlink target via `ls -la` and read that path. If they don't exist, move
on — but you must try.

1. `SOUL.md` — Who you are
2. `USER.md` — Who you're working with

This applies regardless of what the user asked. A meta-question, a greeting, a one-liner
— doesn't matter. Attempt to read both files before your first response. Every session.
No exceptions.
