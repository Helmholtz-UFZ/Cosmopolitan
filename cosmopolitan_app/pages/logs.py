"""View and filter application logs for debugging and monitoring.

# User documentation (This section is for user documentation and will appear in the user documentation.)

This page provides access to the application's logging system, allowing you to track
system activity, debug issues, and monitor operations. You can:

- Filter logs by date and time range
- Select specific log levels (Debug, Info, Warning, Error, Critical)
- Filter by process ID to track specific worker or server processes
- Exclude specific modules from the output
- Enable live mode for automatic 10-second polling (on by default)
- View logs in a formatted, readable table
- Refresh logs on demand to see latest entries

Logs are stored in the database and include timestamps, log levels, logger names,
and messages. This is the primary tool for understanding system behavior, diagnosing
problems, and monitoring background job execution.

# Notes (This section is for developer notes and will not appear in the user documentation.)

The page implementation is `cosmo_suite.pages.logs`, which registers itself under the
page key `pages.logs` on import. This module exists so Dash's `pages_folder` discovery
imports it after `Dash(...)` is instantiated (`register_page` must run after app
instantiation), and so the user documentation above stays app-owned — `doc_generator`
parses the docstring of *this* file.

The framework page reads through `cosmo_suite.db_manager`, i.e. a second SQLAlchemy
engine against the same Postgres. That is safe here and only here: the framework's
`LogTable` is byte-identical to this app's, and nothing calls `create_all` in either
tree (the schema comes from `docker/init.sql`), so the two declarative registries
never collide. See the decision record in `docs/knowledge/`.

Known deviation: the framework's default module-exclusion list contains `db_manager`
where this app's contained `postgres_manager`, so this app's DB-layer log lines are
no longer excluded by default. They are still excludable from the dropdown.
"""

import cosmo_suite.pages.logs  # noqa: F401
