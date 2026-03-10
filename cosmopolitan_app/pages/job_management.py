"""Manage all prediction jobs from a central dashboard.

This administrative page provides a comprehensive overview of all jobs in the system.
You can:
- View all jobs in a sortable, filterable table
- See job status, creation dates, and submission status at a glance
- Select and delete individual jobs or multiple jobs at once
- Trigger cleanup operations to remove old jobs automatically
- Access individual job pages directly from the table

The table uses color coding to quickly identify job statuses: blue for completed jobs,
green for running jobs, red for failed jobs, and grey for pending jobs. You can select
rows to perform bulk operations like deletion.

NOTE: This docstring is displayed on the documentation webpage.
"""

import logging
import re
from datetime import datetime

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dash_table, dcc, html

from cosmopolitan_app.constants import (
    CLEAN_BUTTON_JOB_MANAGEMENT_ID,
    DELETE_BUTTON_JOB_MANAGEMENT_ID,
    DUMMY_STORE_JOB_MANAGEMENT_ID,
    JOBS_TABLE_JOB_MANAGEMENT_ID,
    LOADING_OVERLAY_MODAL_SHARED_ID,
    REFRESH_BUTTON_JOB_MANAGEMENT_ID,
)
from cosmopolitan_app.job import Job
from cosmopolitan_app.layouts import create_header, page_container_column_layout
from cosmopolitan_app.postgres_manager import PostgresManager
from cosmopolitan_app.tasks.maintenance_tasks import clean_up_jobs

log = logging.getLogger(__name__)

dash.register_page(__name__)


table = dash_table.DataTable(
    id=JOBS_TABLE_JOB_MANAGEMENT_ID,
    columns=[
        {"id": "job_id", "name": "Job ID", "presentation": "markdown"},
        {"id": "status", "name": "Status"},
        {"id": "start_date", "name": "Start Date"},
        {"id": "submitted", "name": "Submitted"},
    ],
    data=[],
    row_selectable="multi",
    selected_rows=[],
    style_cell={"textAlign": "center"},
    cell_selectable=False,
    style_data_conditional=[
        {
            "if": {
                "column_id": "job_id",
            },
            "textAlign": "left",
            "fontFamily": "monospace",
        },
        {
            "if": {
                "filter_query": '{status} = "COMPLETED"',
                "column_id": "status",
            },
            "backgroundColor": "#3498db",
        },
        {
            "if": {
                "filter_query": '{status} = "RUNNING"',
                "column_id": "status",
            },
            "backgroundColor": "#2ecc71",
        },
        {
            "if": {
                "filter_query": '{status} = "FAILED"',
                "column_id": "status",
            },
            "backgroundColor": "#e74c3c",
        },
        {
            "if": {
                "filter_query": '{status} = "PENDING"',
                "column_id": "status",
            },
            "backgroundColor": "#f39c12",
        },
    ],
)

button_group = [
    dbc.Button(
        [html.I(className="bi bi-arrow-clockwise me-1"), "Refresh Jobs"],
        id=REFRESH_BUTTON_JOB_MANAGEMENT_ID,
        color="primary",
        className="ms-2 float-end",
    ),
    dbc.Button(
        [html.I(className="bi bi-trash me-1"), "Delete Selection"],
        id=DELETE_BUTTON_JOB_MANAGEMENT_ID,
        color="danger",
        className="ms-2 float-end",
    ),
    dbc.Button(
        [html.I(className="bi bi-recycle me-1"), "Clean"],
        id=CLEAN_BUTTON_JOB_MANAGEMENT_ID,
        color="warning",
        className="ms-2 float-end",
    ),
]

layout = page_container_column_layout(
    [
        create_header(
            "Job Management",
            "Overview and management of jobs in the Cosmopolitan App",
            bg_color="bg-info",
        ),
        # Needed to get a different set inputs for the loading overlay
        dcc.Store(id=DUMMY_STORE_JOB_MANAGEMENT_ID, data=None),
        dbc.Row(
            dbc.Col(
                button_group,
            ),
            className="m-2",
        ),
        dbc.Row(
            dbc.Col(
                table,
            ),
            className="m-2",
        ),
    ]
)


# Clientside callback: open loading overlay instantly in the browser.
# A server-side callback here would race with the processing callback
# (due to allow_duplicate), potentially leaving the overlay stuck open.
# Only listens to button clicks — not DUMMY_STORE (which should not show overlay).
dash.clientside_callback(
    """
    function() {
        for (var i = 0; i < arguments.length; i++) {
            if (arguments[i] != null) return true;
        }
        return false;
    }
    """,
    Output(LOADING_OVERLAY_MODAL_SHARED_ID, "is_open", allow_duplicate=True),
    Input(DELETE_BUTTON_JOB_MANAGEMENT_ID, "n_clicks"),
    Input(CLEAN_BUTTON_JOB_MANAGEMENT_ID, "n_clicks"),
    Input(REFRESH_BUTTON_JOB_MANAGEMENT_ID, "n_clicks"),
    prevent_initial_call=True,
)


@callback(
    Output(JOBS_TABLE_JOB_MANAGEMENT_ID, "data"),
    Output(JOBS_TABLE_JOB_MANAGEMENT_ID, "selected_rows"),
    Output(LOADING_OVERLAY_MODAL_SHARED_ID, "is_open", allow_duplicate=True),
    Input(DELETE_BUTTON_JOB_MANAGEMENT_ID, "n_clicks"),
    Input(CLEAN_BUTTON_JOB_MANAGEMENT_ID, "n_clicks"),
    Input(REFRESH_BUTTON_JOB_MANAGEMENT_ID, "n_clicks"),
    Input(DUMMY_STORE_JOB_MANAGEMENT_ID, "data"),
    State(JOBS_TABLE_JOB_MANAGEMENT_ID, "selected_rows"),
    State(JOBS_TABLE_JOB_MANAGEMENT_ID, "data"),
    prevent_initial_call=True,
)
def job_management_dashboard(
    delete_clicks, clean_clicks, refresh_clicks, _dummy, selected_rows, table_data
):
    """Manage job actions in the dashboard."""
    log.info("Job management dashboard callback triggered.", extra={"tag": "frontend"})
    button_id = dash.callback_context.triggered[0]["prop_id"].split(".")[0]

    if button_id == DELETE_BUTTON_JOB_MANAGEMENT_ID and selected_rows:
        log.info("Deleting selected jobs", extra={"tag": "job_submission"})
        for i in selected_rows:
            job_id = re.findall(r"\[(.*?)\]", table_data[i]["job_id"])[0]
            log.debug(
                f"Deleting job with ID: {job_id}", extra={"tag": "job_submission"}
            )
            job = Job(job_id)
            job.delete()
    elif button_id == CLEAN_BUTTON_JOB_MANAGEMENT_ID:
        log.info("Cleaning unsubmitted jobs", extra={"tag": "job_submission"})
        clean_up_jobs(days_delete_not_submitted=0)

    jobs_dict = PostgresManager.list_jobs()

    rows = []
    submission_base_path = dash.page_registry["pages.submission"]["path_template"]
    for job_id, job_data in jobs_dict.items():
        start_date = (
            job_data["start_date"].strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(job_data["start_date"], datetime)
            else job_data["start_date"]
        )

        job_id_link = submission_base_path.replace("<job_id>", job_id)
        job_id_markdown = f"[{job_id}]({job_id_link})"

        rows.append(
            {
                "job_id": job_id_markdown,
                "status": job_data["status"],
                "start_date": start_date,
                "submitted": "Yes" if job_data["submitted"] else "No",
            }
        )

    # Reset selected_rows after delete or clean, hide loading overlay
    if button_id in [DELETE_BUTTON_JOB_MANAGEMENT_ID, CLEAN_BUTTON_JOB_MANAGEMENT_ID]:
        return rows, [], False
    return rows, dash.no_update, False
