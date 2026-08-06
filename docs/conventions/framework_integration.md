# Framework Integration (`cosmo-suite`)

Binding rules for working across the boundary to the shared framework
[`cosmo-suite`](https://codebase.helmholtz.cloud/ufz/tb5-smm/met/wg7/cosmo-suite), which this
app shares with its sister app COSMONAUT.

For *how* the boundary currently runs — what is imported, what runs twice — see
[`../knowledge/systems/cosmo-suite-boundary.md`](../knowledge/systems/cosmo-suite-boundary.md).
This file says what you must do.

## Freeze rule

The framework is pinned to a **tag** in `pyproject.toml`. Never edit the installed package,
and never patch `../cosmo-suite` to unblock work here.

Need a framework change? It is a merge request in the framework repo, a new tag, and a
re-pin in **both** apps. A moving framework underneath two apps means debugging them against
each other.

## Adoption rule

Adopt a framework module only where it is **behaviourally equal or better**. Otherwise the
local module stays, the deviation is **named in that module's docstring**, and a framework MR
is raised.

Diff size does **not** predict which case you are in — read the code, do not count lines.
Both directions have been measured here:

- `logs_table.py` and `object_storage_manager.py` were byte-identical → deleted outright.
- `pages/job_management.py` is 212 lines against the framework's 207 — and the framework
  version links to a path this app does not serve, deletes through the wrong `Job`, and
  breaks a callback convention. It stays local.

## Env and startup

- The framework loads `.env` with `find_dotenv(usecwd=True)`, i.e. from the **CWD of the
  running process**, not from next to `config.py` (which now lives in site-packages). Every
  entrypoint must therefore start from the repo root. When adding a Dockerfile, compose
  service, script or k8s manifest, check its working directory.
- `pyproject.toml` needs `[tool.hatch.metadata] allow-direct-references = true`, otherwise
  hatchling rejects the git-URL pin. The build image also needs `git`.

## ID ownership

**Whoever renders the component owns its ID.**

This app's HTML ID constants overlap the framework's by *value*, so a framework callback can
drive a component this app renders. Two consequences:

1. **Never declare a callback for an Output the framework already declares.** Dash raises
   "Duplicate callback outputs" and the entire callback registry fails — not just that
   component. The symptom is unrelated pages breaking.
2. A constant that is rendered here but driven by a framework callback gets `# nocheck` with
   a comment saying so. That is the documented third case in
   `test/test_html_id_enforcement.py`; the marker only counts **on the assignment line**.

When a page moves to the framework, delete the ID constants it took with it, and point any
Playwright locators at `cosmo_suite.constants` rather than re-declaring the values.

## Framework pages

A framework page is mounted by a **shim** in `pages/`: a module whose only statement is
`import cosmo_suite.pages.<name>`. The shim exists for two reasons, both load-bearing:

1. `register_page` must run after `Dash(...)` is instantiated, which Dash's `pages_folder`
   discovery guarantees.
2. `doc_generator` reads page docstrings **from the file path** in `pages/`. Keeping the
   user documentation in the shim keeps it app-owned and keeps generated docs working.

Put developer notes under the `# Notes` marker so `clean_docstring` keeps them out of the
user documentation.

## Two Celery clients / two engines

Anything the framework provides that builds its own client — `DbManager`, the framework
`BackgroundJobManager` — must not be widened beyond its current use without first unifying
the mappings. The current, deliberate scope is recorded in the knowledge page above.

Also: the framework connects its own `worker_process_init` logging handler at import. This
app connects its own with a different exclusion list, so it **disconnects the framework's
explicitly** in `background_job_manager.py`. Without that, import order decides which
logging config a worker gets.
