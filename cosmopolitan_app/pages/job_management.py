"""Manage all prediction jobs from a central dashboard.

This administrative page provides a comprehensive overview of all jobs in the system.
You can:
- View all jobs in a sortable, filterable table
- See job status, creation dates, and submission status at a glance
- Select and delete individual jobs or multiple jobs at once
- Trigger cleanup operations to remove old jobs automatically
- Access individual job pages directly from the table

The table uses color coding to quickly identify job statuses: blue for completed jobs,
green for running jobs, red for failed jobs, and orange for pending jobs. You can select
rows to perform bulk operations like deletion.

NOTE: This docstring is displayed on the documentation webpage.

# Notes (This section is for developer notes and will not appear in the user documentation.)

The page implementation is `cosmo_ecosystem.pages.job_management`, which registers
itself under the page key `pages.job_management` (path `/job-management`) on import.
This module exists so Dash's `pages_folder` discovery imports it after `Dash(...)` is
instantiated (`register_page` must run after app instantiation; Dash also skips any
file in `pages/` whose text does not contain that word), and so the user
documentation above stays app-owned: `doc_generator` parses the docstring of *this*
file.

The two blockers that kept a local copy here are gone in the framework page: the row
link is the seam `cosmo_ecosystem.pages.job_link`, and the loading-overlay opener is
clientside, as `docs/conventions/callbacks.md` requires. The seam must be set before
the framework page is imported (it raises `JobLinkNotConfigured` otherwise), and on
the package attribute: a `from ... import job_link` would bind a copy.

`job_link` resolves the submission page from `dash.page_registry` at call time, not
here: `pages/submission.py` is discovered after this module, so its entry does not
exist yet when this module runs.

Delete and Clean go through `cosmo_ecosystem.job_persistence.delete_jobs` and
`cosmo_ecosystem.job_retention.clean_up_jobs`, which find this app's rows because
`DbManager.job_table` is configured in `postgres_manager`. The page's HTML ids come
from `cosmo_ecosystem.constants`.
"""

import dash

import cosmo_ecosystem.pages


def job_link(job_id, row):
    """Link a job management row to this app's submission page, whatever its status."""
    return dash.page_registry["pages.submission"]["path_template"].replace(
        "<job_id>", job_id
    )


cosmo_ecosystem.pages.job_link = job_link

import cosmo_ecosystem.pages.job_management  # noqa: E402, F401 - job_link is set first
