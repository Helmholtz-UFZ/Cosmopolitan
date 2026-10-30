"""Smoke test: the job management page is the framework's, linking to this app's job page.

No services are needed: it checks the page registry and the link seam only.
"""

import sys

import cosmo_ecosystem.pages
import dash

from cosmopolitan_app.app import app  # noqa: F401 - registers the pages first


def test_job_management_page_is_the_framework_page_at_job_management():
    page = dash.page_registry["pages.job_management"]

    assert page["path"] == "/job-management"
    # Served by the framework module, not a local copy registered under the same key.
    # Looked up in sys.modules instead of imported: a top-level import would sort above
    # the app import and raise, because the page needs job_link set by the app's shim.
    assert page["layout"] is sys.modules["cosmo_ecosystem.pages.job_management"].layout


def test_job_link_points_at_the_submission_page():
    row = {"status": "PENDING", "submitted": False, "start_date": None}

    assert cosmo_ecosystem.pages.job_link("abc123", row) == "/submission/abc123"
